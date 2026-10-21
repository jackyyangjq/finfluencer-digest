from finfluencer_digest.render import build_digest, fix_md_lists


def test_build_digest_sections(make_result):
    results = [make_result("A", "NVDA", "看多", vid="v1"), make_result("B", "NVDA", "看空", vid="v2")]
    md = build_digest("2026-09-23", results, "汇总文字", [], [], watch={"NVDA", "TSLA"},
                      usage_line="今日 Gemini 用量：x")
    assert md.startswith("# 财经博主日报 · 2026-09-23")
    assert "## 今日共识与分歧" in md and "今天整理了 2 个新视频，来自 2 位博主：A、B。" in md
    assert "## 你关注的股票" in md and "**NVDA**" in md
    assert "| ⭐ NVDA |" in md and "| 1（A） | 1（B） |" in md
    assert md.count("### ") == 2 and md.rstrip().endswith("今日 Gemini 用量：x")


def test_build_digest_held_excluded_from_watch_hits_and_title_switch(make_result):
    md = build_digest("d", [make_result("A", "NVDA", "看多")], "s", [], [], watch={"NVDA"},
                      portfolio_md="## 我的持仓\n\n（示例）", held=frozenset({"NVDA"}))
    assert md.startswith("# 投资日报 · d") and "## 你关注的股票" not in md and "## 我的持仓" in md


def test_build_digest_empty_and_failures():
    md = build_digest("d", [], "", ["频道甲失败"], [], set())
    assert "今天没有需要整理的新视频" in md and "- 频道甲失败" in md


def test_fix_md_lists_adds_blank_lines_and_indents_sublists():
    src = "段落\n- 一\n  - 子\n- 二\n结尾"
    assert fix_md_lists(src) == "段落\n\n- 一\n    - 子\n- 二\n\n结尾"


def test_build_digest_star_and_row_for_same_company(make_result):
    results = [make_result("A", "GOOGL", "看多", vid="v1"), make_result("B", "GOOG", "中性", vid="v2")]
    md = build_digest("d", results, "s", [], [], watch=set(), portfolio_md="## 我的持仓", held=frozenset({"GOOG"}))
    table = md.split("## 个股提及统计", 1)[1].split("## 各博主要点", 1)[0]
    assert table.count("\n|") == 3 and "| ⭐ GOOG | GOOGL | 1（A） |  | 1（B） |" in table  # 表头、分隔线、合并的一行


def test_build_digest_table_lists_only_multi_mentions_or_mine(make_result):
    results = [make_result("A", "NVDA", "看多", vid="v1"), make_result("B", "NVDA", "看空", vid="v2"),
               make_result("A", "AMD", "看多", vid="v3"), make_result("B", "TSLA", "看空", vid="v4")]
    md = build_digest("d", results, "s", [], [], watch={"TSLA"})
    table = md.split("## 个股提及统计", 1)[1].split("## 各博主要点", 1)[0]
    assert "NVDA" in table and "⭐ TSLA" in table and "AMD" not in table


def test_build_digest_blogger_points_are_compact(make_result):
    v, s = make_result("A", "NVDA", "看多")
    s = s.model_copy(update={"main_points": ["一", "二", "三", "四"], "key_facts": ["数据"], "risks": ["风险"]})
    md = build_digest("d", [(v, s)], "s", [], [], watch=set())
    assert "- 三" in md and "- 四" not in md and "提到的数据" not in md and "博主提到的风险" not in md
