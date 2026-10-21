"""汇总各博主的结构化摘要：按股票统计多空，整理成逐条落盘的观点记录。都是纯函数。"""
from __future__ import annotations

from collections import defaultdict

STANCES = ("看多", "看空", "中性")

# 同一家公司的不同股票代码，统一成右边的代码（统计表、持仓匹配、打 ⭐ 都用它）
SAME_COMPANY = {
    "GOOGL": "GOOG",
    "BRK.A": "BRK.B", "BRK-A": "BRK.B", "BRK/A": "BRK.B", "BRKA": "BRK.B",
    "BRK-B": "BRK.B", "BRK/B": "BRK.B", "BRKB": "BRK.B",
}


def norm_symbol(symbol: str) -> str:
    return symbol.strip().upper().lstrip("$")


def symbol_aliases(cfg: dict | None) -> dict[str, str]:
    """内置的同公司代码表，加上 config.yaml 里可选的 symbol_aliases（如 {GOOGL: GOOG}）。
    配置优先：配置把某个代码映射到别处时，内置表里以它为目标的条目让位，避免来回映射。"""
    extra = {norm_symbol(str(k)): norm_symbol(str(v)) for k, v in ((cfg or {}).get("symbol_aliases") or {}).items()}
    base = {k: v for k, v in SAME_COMPANY.items() if v not in extra}
    return {**base, **extra}


def canonical_symbol(symbol: str, aliases: dict[str, str] | None = None) -> str:
    """规范化代码：去掉 $ 和空格、转大写，再把同一家公司的不同代码统一成一个（GOOGL → GOOG）。"""
    aliases = SAME_COMPANY if aliases is None else aliases
    s, seen = norm_symbol(symbol), set()
    while s in aliases and s not in seen:
        seen.add(s)
        s = aliases[s]
    return s


def stock_mentions(results: list, aliases: dict[str, str] | None = None) -> dict:
    agg = defaultdict(lambda: {"name": "", **{s: [] for s in STANCES}, "reasons": []})
    for v, s in results:
        for st in s.stocks:
            sym = canonical_symbol(st.symbol, aliases)
            if not sym:
                continue
            stance = st.stance if st.stance in STANCES else "中性"
            a = agg[sym]
            a["name"] = a["name"] or st.name
            if v["channel"] not in a[stance]:
                a[stance].append(v["channel"])
            a["reasons"].append(f"{v['channel']}（{stance}）：{st.reason}")
    return agg


def stance_roster(mentions: dict) -> dict:
    """每只股票看多、看空、中性的博主名单（程序统计的结果），交给 Gemini 写共识时对照。"""
    return {sym: {s: a[s] for s in STANCES if a[s]} for sym, a in mentions.items()}


def call_rows(date: str, results: list) -> list[dict]:
    """每位博主每天对每只股票的看法，一行一条，日后用来算博主的真实胜率。"""
    return [{"date": date, "channel": v["channel"], "video_id": v["id"], "symbol": norm_symbol(st.symbol),
             "name": st.name, "stance": st.stance, "reason": st.reason}
            for v, s in results for st in s.stocks if norm_symbol(st.symbol)]
