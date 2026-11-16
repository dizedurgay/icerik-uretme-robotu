"""Aşama 1-2 testleri. llm.generate_structured mock'lanır; gerçek API çağrısı yok."""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from contentflow import config, llm, models, prompts, storage
from contentflow.generators import strategy
from tests import sample_data as sd

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = {
    models.BrandIdentity: sd.IDENTITY, models.CompetitorAnalysis: sd.COMPETITORS,
    models.PersonaSet: sd.PERSONAS, models.BrandVoice: sd.VOICE, models.ContentStrategy: sd.STRATEGY,
}


@pytest.fixture(autouse=True)
def tmp_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    yield tmp_path


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw)
        return llm.CallResult(OUTPUTS[kw["schema"]], f"log{len(calls)}", cached=False)

    monkeypatch.setattr(llm, "generate_structured", fake)
    return calls


def test_all_templates_render_without_missing_vars():
    storage.save_version("brand_identity", sd.IDENTITY.model_dump())
    storage.save_version("personas", sd.PERSONAS.model_dump())
    ctx = strategy._ctx()
    for name in ("brand_identity", "competitor_analysis", "personas", "brand_voice", "content_pillars"):
        text = prompts.render(name, **ctx)
        assert "$" not in text, name
        assert prompts.formula(name) != "serbest", name


def test_costar_and_rtf_headers_present():
    for name in ("brand_identity", "brand_voice", "content_pillars"):
        raw = prompts.load_raw(name)
        for h in ("# Context", "# Objective", "# Style", "# Tone", "# Audience", "# Response"):
            assert h in raw, (name, h)
    for name in ("competitor_analysis", "personas"):
        raw = prompts.load_raw(name)
        for h in ("# Role", "# Task", "# Format"):
            assert h in raw, (name, h)


def test_full_stage_1_2_flow(fake_llm):
    strategy.generate_identity()
    strategy.generate_competitors()
    strategy.generate_personas()
    strategy.generate_voice()
    strategy.generate_strategy()
    assert all(storage.get_current(k) for k in
               ("brand_identity", "competitors", "personas", "brand_voice", "content_strategy"))
    # Model 'verified: true' döndürse bile false'a zorlanır
    assert not any(c["verified"] for c in storage.get_current("competitors")["competitors"])
    # Marka sesi yalnızca strateji çağrısında enjekte edilir
    assert [c["with_brand_voice"] for c in fake_llm] == [False, False, False, False, True]
    assert storage.stage_progress()[1]["done"]


def test_persona_count_from_seed(fake_llm):
    storage.save_version("brand_identity", sd.IDENTITY.model_dump())
    _, issues = strategy.generate_personas()
    assert issues == []  # tohumda persona_count: 1
    assert "tam olarak 1 adet" in fake_llm[-1]["user_prompt"]


def test_checks_flag_bad_counts():
    bad = sd.IDENTITY.model_copy(update={"palette": sd.IDENTITY.palette[:2] + [
        models.ColorSwatch(name="x", hex="123456", usage="u")]})
    issues = models.check_identity(bad)
    assert any("Renk paleti" in i for i in issues) and any("HEX" in i for i in issues)


def test_brand_voice_rendered_in_system_prompt():
    storage.save_version("brand_voice", sd.VOICE.model_dump())
    system, injected = llm.build_system_prompt("x")
    assert injected and "| Biz şuyuz | Şu değiliz |" in system and "samimi" in system


@pytest.mark.parametrize("page", ["pages/1_Marka_Kimligi.py", "pages/2_Ses_ve_Strateji.py", "app.py"])
def test_pages_render_with_data(page):
    for key, obj in (("brand_identity", sd.IDENTITY), ("competitors", sd.COMPETITORS),
                     ("personas", sd.PERSONAS), ("brand_voice", sd.VOICE), ("content_strategy", sd.STRATEGY)):
        storage.save_version(key, obj.model_dump(mode="json"))
    storage.save_version("brand_voice", sd.VOICE.model_dump(mode="json"), source="human")  # versiyon seçici
    at = AppTest.from_file(str(ROOT / page), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
