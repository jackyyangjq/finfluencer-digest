import json

from finfluencer_digest.summarize import VIDEO_PROMPT, synthesize


class FakeLLM:
    def __init__(self):
        self.prompts = []

    def ask(self, models, *, label="", contents="", **kwargs):
        self.prompts.append(contents)
        return type("R", (), {"text": "**共识**\n\n- x"})()


def test_synthesize_puts_program_stance_roster_in_prompt(make_result):
    llm = FakeLLM()
    results = [make_result("A", "GOOGL", "看多", vid="v1"), make_result("B", "GOOG", "看空", vid="v2")]
    assert synthesize(llm, {"synth_models": ["m"]}, results).startswith("**共识**")
    prompt = llm.prompts[0]
    roster = json.loads(prompt.split("博主名单：\n", 1)[1].split("\n", 1)[0])
    assert roster == {"GOOG": {"看多": ["A"], "看空": ["B"]}}
    assert "不得增减" in prompt and "不超过 6 条" in prompt and "最多 2 条" in prompt


def test_video_prompt_has_unit_and_homophone_rules():
    text = VIDEO_PROMPT.format(channel="c", title="t")
    assert "千亿" in text and "billion" in text and "同音错字" in text
