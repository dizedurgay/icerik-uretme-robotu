"""llm.py birim testleri. Gerçek API çağrısı YAPILMAZ: Gemini istemcisi ve edge-tts mock'lanır."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from google.genai import errors
from pydantic import BaseModel

from contentflow import config, llm, storage


class Dummy(BaseModel):
    title: str


sleeps: list[float] = []


@pytest.fixture(autouse=True)
def tmp_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(llm, "_client_instance", None)
    monkeypatch.setattr(llm, "_sleep", lambda s: sleeps.append(s))
    sleeps.clear()
    yield tmp_path


def fake_client(parsed=None, text="merhaba", in_tok=1000, out_tok=500, fail_with=None):
    usage = SimpleNamespace(prompt_token_count=in_tok, candidates_token_count=out_tok, thoughts_token_count=0)
    calls = {"n": 0, "kwargs": []}

    def generate_content(**kw):
        calls["n"] += 1
        calls["kwargs"].append(kw)
        if fail_with and calls["n"] <= len(fail_with):
            raise fail_with[calls["n"] - 1]
        return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json() if parsed else text,
                               usage_metadata=usage, prompt_feedback=None)

    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)), calls


def use(monkeypatch, client):
    monkeypatch.setattr(llm, "_client", lambda: client)


def structured(**kw):
    return llm.generate_structured(task="t", stage="aşama1", formula="serbest", user_prompt="u",
                                   schema=Dummy, **kw)


def api_error(code, details=None, message="err"):
    body = {"error": {"code": code, "message": message, "status": "X", "details": details or []}}
    return errors.ClientError(code, body) if code < 500 else errors.ServerError(code, body)


MINUTE_429 = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
               "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]},
              {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "33s"}]
DAILY_429 = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
              "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]},
             {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "20s"}]


# ----------------------------------------------------------------- metin


def test_structured_uses_schema_and_logs(monkeypatch):
    client, calls = fake_client(parsed=Dummy(title="x"))
    use(monkeypatch, client)
    res = structured()
    assert res.output.title == "x" and not res.cached
    cfg = calls["kwargs"][0]["config"]
    assert cfg.response_mime_type == "application/json" and cfg.response_schema is Dummy
    assert "Türkçe" in cfg.system_instruction
    log = storage.read_jsonl(storage.prompt_log_path())
    assert len(log) == 1 and log[0]["model"] == config.TEXT_MODEL
    assert (log[0]["input_tokens"], log[0]["output_tokens"]) == (1000, 500)
    assert "cost_usd" not in log[0] and log[0]["edited_by_human"] is False


def test_falls_back_to_json_text_when_parsed_missing(monkeypatch):
    client, _ = fake_client(parsed=None, text='{"title": "metinden"}')
    use(monkeypatch, client)
    assert structured().output.title == "metinden"


def test_invalid_json_gives_turkish_error(monkeypatch):
    client, _ = fake_client(parsed=None, text="bozuk")
    use(monkeypatch, client)
    with pytest.raises(llm.LLMError, match="şemaya uygun"):
        structured()


def test_cache_hit_and_regenerate(monkeypatch):
    client, calls = fake_client(parsed=Dummy(title="x"))
    use(monkeypatch, client)
    structured()
    assert structured().cached and calls["n"] == 1
    structured(use_cache=False)  # "Yeniden üret"
    assert calls["n"] == 2


def test_brand_voice_injected_when_present(monkeypatch):
    client, calls = fake_client()
    use(monkeypatch, client)
    llm.generate_text(task="t", stage="s", formula="f", user_prompt="a")
    assert "MARKA SESİ" not in calls["kwargs"][-1]["config"].system_instruction

    storage.save_version("brand_voice", {"kisilik": ["samimi", "sakin"]})
    llm.generate_text(task="t", stage="s", formula="f", user_prompt="b")
    system = calls["kwargs"][-1]["config"].system_instruction
    assert "MARKA SESİ REHBERİ" in system and "samimi" in system
    assert storage.read_jsonl(storage.prompt_log_path())[-1]["brand_voice_injected"] is True

    llm.generate_text(task="t", stage="s", formula="f", user_prompt="c", with_brand_voice=False)
    assert "MARKA SESİ" not in calls["kwargs"][-1]["config"].system_instruction


# ----------------------------------------------------------------- 429 / hatalar


def test_minute_429_waits_retry_delay_then_succeeds(monkeypatch):
    client, calls = fake_client(parsed=Dummy(title="x"), fail_with=[api_error(429, MINUTE_429)])
    use(monkeypatch, client)
    assert structured().output.title == "x"
    assert calls["n"] == 2 and sleeps == [33.0]


def test_daily_429_fails_fast_without_waiting(monkeypatch):
    monkeypatch.setattr(config, "FALLBACK_MODELS", [])
    client, calls = fake_client(parsed=Dummy(title="x"), fail_with=[api_error(429, DAILY_429)])
    use(monkeypatch, client)
    with pytest.raises(llm.QuotaExhausted, match="günlük ücretsiz kotası"):
        structured()
    assert calls["n"] == 1 and sleeps == []


def test_429_wait_is_capped_and_retries_exhaust(monkeypatch):
    long = [{"@type": "x.RetryInfo", "retryDelay": "500s"}]
    client, calls = fake_client(fail_with=[api_error(429, long)] * 10)
    use(monkeypatch, client)
    with pytest.raises(llm.LLMError, match="dakikalık"):
        llm.generate_text(task="t", stage="s", formula="f", user_prompt="a")
    assert calls["n"] == config.MAX_RETRIES
    assert all(s <= config.MAX_RATE_LIMIT_WAIT_S for s in sleeps)


def test_503_retries_once_then_falls_back_to_next_model(monkeypatch):
    monkeypatch.setattr(config, "FALLBACK_MODELS", ["yedek-1", "yedek-2"])
    client, calls = fake_client(fail_with=[api_error(503), api_error(503)])
    use(monkeypatch, client)
    assert llm.generate_text(task="t", stage="s", formula="f", user_prompt="a").output == "merhaba"
    assert [k["model"] for k in calls["kwargs"]] == [config.TEXT_MODEL, config.TEXT_MODEL, "yedek-1"]
    assert sleeps == [2.0]
    row = storage.read_jsonl(storage.prompt_log_path())[0]
    assert row["model"] == "yedek-1" and row["fallback_from"] == config.TEXT_MODEL


def test_daily_quota_falls_back_and_all_busy_gives_clear_error(monkeypatch):
    monkeypatch.setattr(config, "FALLBACK_MODELS", ["yedek-1"])
    client, calls = fake_client(fail_with=[api_error(429, DAILY_429)])
    use(monkeypatch, client)
    assert llm.generate_text(task="t", stage="s", formula="f", user_prompt="a").output == "merhaba"
    assert calls["kwargs"][-1]["model"] == "yedek-1" and sleeps == []

    client, calls = fake_client(fail_with=[api_error(503)] * 10)
    use(monkeypatch, client)
    with pytest.raises(llm.ServerBusy, match="aşırı yoğun"):
        llm.generate_text(task="t", stage="s", formula="f", user_prompt="b")
    assert calls["n"] == 2 * config.SERVER_ERROR_RETRIES


@pytest.mark.parametrize("code,msg,expected", [
    (400, "API key not valid. Please pass a valid API key.", "anahtarı geçersiz"),
    (403, "forbidden", "anahtarı geçersiz"),
    (404, "models/x is not found", "Model bulunamadı"),
    (400, "bad schema", "İstek reddedildi"),
])
def test_client_errors_not_retried(monkeypatch, code, msg, expected):
    client, calls = fake_client(fail_with=[api_error(code, message=msg)])
    use(monkeypatch, client)
    with pytest.raises(llm.LLMError, match=expected):
        llm.generate_text(task="t", stage="s", formula="f", user_prompt="a")
    assert calls["n"] == 1


def test_missing_key_message(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="GEMINI_API_KEY"):
        llm._client()


# ----------------------------------------------------------------- sayaç


def test_requests_today_counts_only_todays_gemini_calls(monkeypatch):
    client, _ = fake_client(parsed=Dummy(title="x"))
    use(monkeypatch, client)
    structured()
    structured()                       # önbellek: sayılmaz
    structured(use_cache=False)
    llm.log_human_edit(task="t", stage="s", output="x")  # Gemini değil: sayılmaz
    yesterday = (datetime.now().astimezone() - timedelta(days=1)).isoformat()
    storage.append_jsonl(storage.prompt_log_path(), {"kind": "structured", "timestamp": yesterday})
    assert llm.requests_today() == 2


# ----------------------------------------------------------------- ses / görsel / insan


def test_speech_with_edge_tts(monkeypatch):
    saved = []

    class FakeCommunicate:
        def __init__(self, text, voice, rate, pitch):
            saved.append((text, voice, rate, pitch))

        async def save(self, path):
            open(path, "wb").write(b"ID3fake")

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=FakeCommunicate))
    res = llm.generate_speech(task="voiceover", stage="aşama3", text="Merhaba", voice="tr-TR-AhmetNeural",
                              rate="-5%")
    assert res.output.exists() and saved == [("Merhaba", "tr-TR-AhmetNeural", "-5%", "+0Hz")]
    row = storage.read_jsonl(storage.prompt_log_path())[0]
    assert row["kind"] == "speech" and row["model"] == "edge-tts:tr-TR-AhmetNeural"
    assert llm.generate_speech(task="voiceover", stage="aşama3", text="Merhaba", voice="tr-TR-AhmetNeural",
                               rate="-5%").cached
    assert llm.requests_today() == 0  # TTS Gemini kotasına girmez


def test_speech_network_failure(monkeypatch):
    class Broken:
        def __init__(self, *a, **k):
            pass

        async def save(self, path):
            raise ConnectionError("offline")

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=Broken))
    with pytest.raises(llm.LLMError, match="edge-tts"):
        llm.generate_speech(task="v", stage="s", text="x")


def test_image_upload_logged():
    llm.log_image_upload(task="image", stage="aşama3", prompt="cup", tool="Canva", path="images/a.png",
                         calendar_item_id="cal-02")
    row = storage.read_jsonl(storage.prompt_log_path())[0]
    assert (row["kind"], row["model"], row["tool"], row["output"]) == ("image_upload", "Canva", "Canva", "images/a.png")


def test_human_edit_logged():
    llm.log_human_edit(task="blog", stage="aşama3", output="yeni metin")
    row = storage.read_jsonl(storage.prompt_log_path())[0]
    assert row["edited_by_human"] is True and row["kind"] == "human_edit"


def test_versions_never_deleted():
    storage.save_version("blog", "v1 metni")
    storage.save_version("blog", "v2 metni", source="human")
    assert storage.get_current("blog") == "v2 metni"
    storage.set_current("blog", 1)
    assert storage.get_current("blog") == "v1 metni"
    assert len(storage.get_section("blog")["versions"]) == 2


def test_api_key_never_logged(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSECRET123")
    client, _ = fake_client()
    use(monkeypatch, client)
    llm.generate_text(task="t", stage="s", formula="f", user_prompt="a")
    assert "AIzaSECRET123" not in storage.prompt_log_path().read_text(encoding="utf-8")
