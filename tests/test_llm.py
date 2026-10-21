import pytest

from finfluencer_digest.llm import Gemini, RecordedGemini


class Err(Exception):
    def __init__(self, code):
        super().__init__(f"code {code}")
        self.code = code


class Meta:
    prompt_token_count, candidates_token_count, thoughts_token_count = 100, 20, 5


class Resp:
    text, parsed, usage_metadata = "ok", None, Meta()


def make(script):
    """script: {model: [异常或 Resp, ...]}，按调用顺序弹出。"""
    calls = []
    llm = Gemini("k", sleep=lambda s: calls.append(("sleep", s)))

    def fake(model, **kwargs):
        calls.append(model)
        item = script[model].pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    llm._call = fake  # Gemini 内部统一经 self._call(model, **kwargs) 调 SDK，测试替换它
    return llm, calls


def test_retries_on_503_then_succeeds():
    llm, calls = make({"m1": [Err(503), Resp()]})
    resp, model = llm.generate(["m1", "m2"], contents="x")
    assert model == "m1" and calls == ["m1", ("sleep", 30), "m1"]


def test_quota_error_skips_to_next_model_without_sleep():
    llm, calls = make({"m1": [Err(429)], "m2": [Resp()]})
    _, model = llm.generate(["m1", "m2"], contents="x")
    assert model == "m2" and ("sleep", 30) not in calls


def test_all_models_fail_raises_last_error():
    llm, _ = make({"m1": [Err(429)], "m2": [Err(400)]})
    with pytest.raises(Err) as e:
        llm.generate(["m1", "m2"], contents="x")
    assert e.value.code == 400


def test_ask_records_usage_and_text():
    llm, _ = make({"m1": [Resp(), Resp()]})
    llm.ask(["m1"], contents="x")
    llm.ask(["m1"], contents="y")
    assert llm.usage["m1"] == [2, 200, 50]
    assert llm.usage_text() == "今日 Gemini 用量：m1 调用 2 次（输入约 0.0 万、输出约 0.0 万 tokens）"


def test_recorded_gemini_replays_by_label():
    summary = {"is_market_related": True, "one_line": "一句话", "main_points": [], "stocks": [], "key_facts": [],
               "risks": []}
    llm = RecordedGemini({"video:v1": summary, "synth": "汇总文字"})
    resp, model = llm.generate(["m1", "m2"], label="video:v1", contents="x")
    assert model == "m1" and resp.parsed.one_line == "一句话"
    llm.add_usage(model, resp.usage_metadata)
    assert llm.ask(["p"], label="synth").text == "汇总文字" and llm.ask(["p"], label="synth").parsed is None
    assert llm.usage == {"m1": [1, 1000, 200], "p": [2, 2000, 400]}
    with pytest.raises(KeyError):
        llm.generate(["m1"], label="video:没录过")


def test_short_error_names_gemini_only_for_genai_errors():
    from urllib.error import HTTPError

    from google.genai import errors

    from finfluencer_digest.llm import short_error
    x_error = HTTPError("https://api.fxtwitter.com/x", 404, "Not Found", {}, None)
    assert short_error(x_error) == "接口返回 404（Not Found）"
    assert "Gemini" not in short_error(Err(404)) and "Gemini" not in short_error(Err(503))
    gemini_error = errors.ClientError(404, {"error": {"code": 404, "message": "model not found"}})
    assert short_error(gemini_error) == "Gemini 拒绝处理（404）：model not found"
    assert short_error(errors.ServerError(503, {"error": {"code": 503}})) == "Gemini 服务暂时繁忙（503）"
    assert short_error(ValueError("bad")) == "ValueError: bad"
