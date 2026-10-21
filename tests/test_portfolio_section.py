import datetime as dt
import json

import pytest

pytest.importorskip("pandas")  # 持仓部分的附加依赖；没装时跳过，不影响其他测试

from finfluencer_digest.portfolio.section import (
    HoldingAnalysis,
    base_symbol,
    blogger_views,
    card,
    risk_flags,
    stale_flags,
    valuation_payload,
    yahoo_symbol,
)
from finfluencer_digest.portfolio.technicals import brief

PCFG = {"single_stock_warn": 0.35, "loss_from_cost_warn": 0.2, "earnings_within_days": 7, "theme_warn": 0.5,
        "manual_file": "holdings_manual.yaml"}
TODAY = dt.date(2026, 10, 21)


def tech(**kw):
    t = {"last": 100.0, "r1d": 0.01, "r5d": 0.0, "r1m": 0.06, "ytd": 0.1, "ma": {20: 98.0, 50: 102.0, 200: 90.0},
         "rsi": 55.0, "macd_above": True, "macd_cross_days": None, "vol_ratio": 1.0,
         "range20": (95.0, 105.0), "range60": (90.0, 110.0), "range52w": (70.0, 120.0)}
    return {**t, **kw}


def row(sym="VRT", **kw):
    r = {"symbol": f"{sym}.US", "yahoo": sym, "name": sym, "weight": 0.1, "pnl_pct": 0.05, "pnl": 10.0,
         "d": {"t": tech(), "earnings": None, "prev": 99.0, "price_date": dt.date(2026, 10, 19)},
         "news": [], "intraday": False, "benchmark": "XLK"}
    return {**r, **kw}


def test_symbols_for_share_classes():
    assert yahoo_symbol("BRK.B.US") == "BRK-B" and yahoo_symbol("NVDA.US") == "NVDA"
    assert yahoo_symbol("700.HK") == "0700.HK" and yahoo_symbol("0700.HK") == "0700.HK"
    assert base_symbol("BRK.B.US") == base_symbol("BRK-B") == "BRK.B" and base_symbol("00700.HK") == "700"


def test_blogger_views_match_googl_to_goog(tmp_path):
    calls = tmp_path / "calls.jsonl"
    old = {"date": (dt.date.today() - dt.timedelta(days=2)).isoformat(), "channel": "甲", "video_id": "v0",
           "symbol": "GOOG", "stance": "中性", "reason": "旧"}
    calls.write_text(json.dumps(old, ensure_ascii=False) + "\n", encoding="utf-8")
    today = [{"date": dt.date.today().isoformat(), "channel": "Steve Eisman", "video_id": "v1", "symbol": "GOOGL",
              "stance": "看多", "reason": "回撤时值得布局"}]
    views = blogger_views({"GOOG": "GOOG"}, today, 7, calls)
    assert [v["channel"] for v in views["GOOG"]] == ["甲", "Steve Eisman"]


def test_stale_flags():
    sources = [("长桥", "2026-10-01T09:00:00"), ("富途", "2026-10-15"), ("手动", ""), ("手动2", dt.date(2026, 9, 1))]
    flags = stale_flags(sources, TODAY, 14)
    assert flags == ["**持仓数据过期**：长桥 持仓数据已 20 天未更新，交易过的话请更新",
                     "**持仓数据过期**：手动2 持仓数据已 50 天未更新，交易过的话请更新"]


def test_risk_flags_merge_per_stock_and_include_stale(monkeypatch):
    monkeypatch.delenv("LONGBRIDGE_ACCESS_TOKEN", raising=False)
    r = row(pnl_pct=-0.43, d={"t": tech(last=77.0, ma={20: 80.0, 50: 90.0, 200: 100.0}), "earnings": None})
    flags = risk_flags([r], {}, PCFG, [("长桥", "2026-10-01")], today=TODAY)
    assert flags[0] == "**VRT**：比成本低 43%；低于 200 日均线 23%"
    assert any("长桥 持仓数据已 20 天未更新" in f for f in flags)
    assert risk_flags([r], {}, {**PCFG, "snapshot_stale_days": 30}, [("长桥", "2026-10-01")], today=TODAY) == flags[:1]


def test_valuation_payload_notes_low_trailing_pe():
    note = valuation_payload({"forwardPE": 22.2, "trailingPE": 17.1})["说明"]
    assert note.startswith("过去 12 个月利润可能含一次性收益")
    assert "说明" not in valuation_payload({"forwardPE": 20.0, "trailingPE": 25.0})


def test_brief_only_mentions_extreme_signals():
    assert brief(tech()) == ["均线交织，长期偏强"]
    assert brief(tech(rsi=75.0, macd_cross_days=2, vol_ratio=2.3)) == [
        "均线交织，长期偏强", "RSI 75，超买", "MACD 2 个交易日前金叉", "成交量为 20 日均量的 2.3 倍"]
    assert brief(tech(rsi=29.0, macd_cross_days=5, vol_ratio=1.9)) == ["均线交织，长期偏强", "RSI 29，超卖"]


def test_card_is_compact():
    a = HoldingAnalysis(symbol="META", theme="广告",
                        good_news=["新品发布（10-20 Reuters）", "多余一条（10-20 Reuters）"],
                        bad_news=["监管罚款（10-19 编造来源）"], bull_points=["甲", "乙", "丙"], bear_points=["丁。"],
                        watch=["守住 650", "财报指引", "多余"], lean="偏多", lean_reason="证据偏多")
    r = row("META", name="Meta Platforms", pnl_pct=-0.079, news=[{"source": "Reuters", "date": "2026-10-20",
                                                                     "title": "t"}])
    r["d"] = {**r["d"], "analyst": {"buy": 55, "hold": 6, "sell": 2, "mean": 115.9, "low": 80.0, "high": 150.0},
              "valuation": {"forwardPE": 20.4, "trailingPE": 25.0}, "earnings": dt.date(2026, 10, 21)}
    views = [{"date": "2026-10-18", "channel": "甲", "stance": "看多", "reason": "x"},
             {"date": "2026-10-20", "channel": "Steve Eisman", "stance": "看多", "reason": "优质标的"},
             {"date": "2026-10-19", "channel": "乙", "stance": "中性", "reason": "y"}]
    views.sort(key=lambda v: v["date"])
    lines = card(r, {"r1m": -0.003}, views, a, 7)
    assert lines[0] == "### META Meta Platforms｜$100.00（10-19 收盘，+1.0%）｜偏多"
    body = lines[2:-1]
    assert body == [
        "- **数据**：1 个月 +6.0%，跑赢 XLK 6.3 个百分点；距成本 -7.9%；均线交织，长期偏强；"
        "分析师 55/63 买入，均价目标 +15.9%；预期市盈率 20.4 倍；财报 10-21",
        "- **看多**：甲；乙",
        "- **看空**：丁",
        "- **新闻**：利好 新品发布（10-20 Reuters）",
        "- **博主**：近 7 天 2 看多、1 中性；最新 10-20 Steve Eisman（看多）：优质标的",
        "- **要盯**：守住 650；财报指引",
        "- **结论**：证据偏多",
    ]
    assert card(r, None, [], None)[2:-1] == [body[0].replace("，跑赢 XLK 6.3 个百分点", ""),
                                             "- **新闻**：10-20 Reuters：t"]
