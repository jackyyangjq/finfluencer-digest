from finfluencer_digest.aggregate import call_rows, norm_symbol, stock_mentions
from finfluencer_digest.summarize import StockView, VideoSummary


def vs(*stocks):
    return VideoSummary(is_market_related=True, one_line="x", main_points=[], key_facts=[], risks=[],
                        stocks=[StockView(symbol=s, name=n, stance=st, reason="r") for s, n, st in stocks])


def test_norm_symbol_strips_dollar_and_case():
    assert norm_symbol(" $nvda ") == "NVDA"
    assert norm_symbol("") == ""


def test_stock_mentions_counts_channels_per_stance_and_dedups():
    results = [
        ({"channel": "A"}, vs(("NVDA", "英伟达", "看多"), ("nvda", "英伟达", "看多"))),
        ({"channel": "B"}, vs(("NVDA", "", "看空"), ("TSLA", "特斯拉", "乱写"))),
    ]
    m = stock_mentions(results)
    assert m["NVDA"]["看多"] == ["A"] and m["NVDA"]["看空"] == ["B"] and m["NVDA"]["name"] == "英伟达"
    assert m["TSLA"]["中性"] == ["B"]  # 未知态度按中性
    assert len(m["NVDA"]["reasons"]) == 3


def test_call_rows_drops_empty_symbols():
    rows = call_rows("2026-09-23", [({"channel": "A", "id": "v1"}, vs(("", "x", "看多"), ("QQQ", "纳指", "中性")))])
    assert [r["symbol"] for r in rows] == ["QQQ"]
    assert rows[0] == {"date": "2026-09-23", "channel": "A", "video_id": "v1", "symbol": "QQQ", "name": "纳指",
                       "stance": "中性", "reason": "r"}


def test_canonical_symbol_merges_share_classes():
    from finfluencer_digest.aggregate import canonical_symbol
    assert canonical_symbol("googl") == "GOOG" and canonical_symbol("$GOOG") == "GOOG"
    assert {canonical_symbol(s) for s in ("BRK.A", "BRK-B", "brk/b", "BRK.B")} == {"BRK.B"}
    assert canonical_symbol("NVDA") == "NVDA"


def test_symbol_aliases_from_config_add_and_override():
    from finfluencer_digest.aggregate import canonical_symbol, symbol_aliases
    aliases = symbol_aliases({"symbol_aliases": {"goog": "GOOGL", "FB": "META"}})
    assert canonical_symbol("GOOG", aliases) == "GOOGL" and canonical_symbol("GOOGL", aliases) == "GOOGL"
    assert canonical_symbol("FB", aliases) == "META" and canonical_symbol("BRK-B", aliases) == "BRK.B"
    assert symbol_aliases({}) == symbol_aliases(None)


def test_stock_mentions_merges_same_company_into_one_row():
    results = [({"channel": "A"}, vs(("GOOGL", "谷歌", "看多"))), ({"channel": "B"}, vs(("GOOG", "谷歌", "看空")))]
    m = stock_mentions(results)
    assert list(m) == ["GOOG"] and m["GOOG"]["看多"] == ["A"] and m["GOOG"]["看空"] == ["B"]
