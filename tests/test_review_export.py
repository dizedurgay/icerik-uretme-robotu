"""Milestone 5-7: medya üreticileri, kontrol katmanı, dışa aktarım (Gemini mock'lu)."""
from __future__ import annotations

import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from PIL import Image
from streamlit.testing.v1 import AppTest

from contentflow import config, llm, models, review, storage, video
from contentflow.exporters import docs
from contentflow.generators import calendar as cal_gen
from contentflow.generators import content, media
from tests import sample_data as sd

ROOT = Path(__file__).resolve().parent.parent
OUT = {models.BlogPost: sd.BLOG, models.SocialPost: sd.SOCIAL, models.ImagePrompt: sd.IMAGE_PROMPT,
       models.CalendarDraft: sd.CALENDAR, models.VoiceoverScript: sd.VOICEOVER, models.VideoScript: sd.VIDEO_SCRIPT,
       models.ReviewReport: sd.REVIEW_RISKY}


def png() -> bytes:
    b = BytesIO()
    Image.new("RGB", (8, 8), "#8FA58B").save(b, format="PNG")
    return b.getvalue()


@pytest.fixture(autouse=True)
def full_state(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    calls = []

    def fake(**kw):
        calls.append(kw)
        llm._log(stage=kw["stage"], task=kw["task"], formula=kw["formula"], model=kw.get("model") or config.TEXT_MODEL,
                 user_prompt=kw["user_prompt"], output="{}", kind="structured", brand_voice_injected=True)
        return llm.CallResult(OUT[kw["schema"]], f"log{len(calls)}", cached=False)

    monkeypatch.setattr(llm, "generate_structured", fake)
    for key, obj in (("brand_identity", sd.IDENTITY), ("competitors", sd.COMPETITORS), ("personas", sd.PERSONAS),
                     ("brand_voice", sd.VOICE), ("content_strategy", sd.STRATEGY)):
        storage.save_version(key, obj.model_dump(mode="json"))
    cal_gen.generate_calendar(date(2026, 11, 23))
    content.generate_blog(content.items_with("blog")[0]["id"])
    for item in content.items_with("image"):
        if "social_post" in item["deliverables"]:
            content.generate_social(item["id"])
        content.generate_image_prompt(item["id"])
        content.save_uploaded_image(item["id"], png(), "g.png", "ChatGPT")
    media.generate_voiceover_script()
    media.generate_video_script()
    # gerçek ses/video yerine sahte dosyalar (montaj ayrıca canlı test edildi)
    (tmp_path / "audio").mkdir(exist_ok=True)
    (tmp_path / "audio" / "s.mp3").write_bytes(b"ID3")
    (tmp_path / "video").mkdir(exist_ok=True)
    (tmp_path / "video" / "v.mp4").write_bytes(b"\x00")
    storage.save_version("voiceover", {"path": "audio/s.mp3", "voice": "tr-TR-EmelNeural", "rate": "-5%",
                                       "pitch": "+0Hz", "text": sd.VOICEOVER.text, "duration_s": 17.2})
    storage.save_version("video", {"path": "video/v.mp4", "duration": 17.8, "audio_duration": 17.2, "music": None,
                                   "scenes": []})
    calls.clear()
    return calls


def test_voice_settings_from_brand_voice():
    assert media.voice_settings() == ("-5%", "+0Hz")


def test_scale_durations():
    assert sum(video.scale_durations([4, 4, 4, 3], 17.5)) == pytest.approx(17.5)


def test_review_fix_decision_flow(full_state):
    items = review.review_items()
    kinds = {i.key.split(":")[0] for i in items}
    assert kinds == {"blog", "social_post", "image_prompt", "voiceover_script", "video_script"}
    blog = next(i for i in items if i.key == "blog")
    review.run_review(blog)
    kw = full_state[-1]
    assert kw["model"] == config.REVIEW_MODEL and kw["with_brand_voice"] is True
    assert "# Role" in kw["user_prompt"] and "$" not in kw["user_prompt"]
    rep = storage.get_current("review:blog")
    assert rep["reviewed_version"] == 1 and rep["kaynak_dogrulama"]["durum"] == "riskli"

    v = review.apply_fix(blog)
    assert v == 2 and storage.get_current_version("blog")["source"] == "fix"
    assert len(storage.get_section("blog")["versions"]) == 2  # eski sürüm korunur
    review.save_decision(blog, "düzeltildi", "kaynak eklendi")
    assert storage.get_current("decision:blog")["decided_version"] == 2


def test_export_all_produces_deliverables(full_state):
    for item in review.review_items():
        review.run_review(item)
        review.save_decision(item, "onaylandı", "ok", {"fake_text": False} if item.is_image else None)
    llm.log_human_edit(task="blog", stage="aşama3", output="x")
    res = docs.export_all()
    exp = storage.subdir("exports")
    for f in ("marka_stratejisi.md", "marka_stratejisi.docx", "marka_sesi_rehberi.md", "icerik_takvimi.xlsx",
              "kontrol_listesi.md", "prompt_kutuphanesi.md", "ai_kullanim_raporu.md", "icerik_seti/blog.md",
              "icerik_seti/sosyal_gonderiler.md", "icerik_seti/seslendirme.mp3", "icerik_seti/video.mp4"):
        assert f in res["files"], f
    assert len([f for f in res["files"] if f.startswith("icerik_seti/gorseller/")]) == 3
    with zipfile.ZipFile(res["zip"]) as z:
        assert "kontrol_listesi.md" in z.namelist()
    Document(str(exp / "marka_stratejisi.docx"))  # açılabiliyor

    checklist = (exp / "kontrol_listesi.md").read_text(encoding="utf-8")
    assert "onaylandı" in checklist and "🟠 riskli" in checklist and "manuel doğrulanmamış" in checklist
    report = (exp / "ai_kullanim_raporu.md").read_text(encoding="utf-8")
    assert "ChatGPT: 3" in report and "Karşılaşılan sorunlar" in report and "0 TL" in report
    library = (exp / "prompt_kutuphanesi.md").read_text(encoding="utf-8")
    assert "RTF" in library and "CO-STAR" in library and "harici görsel aracı" in library
    assert storage.stage_progress()[5]["done"]


@pytest.mark.parametrize("page", ["pages/4_Icerik_Uretimi.py", "pages/5_Kontrol.py", "pages/6_Disa_Aktar.py"])
def test_pages_render(full_state, page):
    for item in review.review_items()[:2]:
        review.run_review(item)
    at = AppTest.from_file(str(ROOT / page), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]


def test_presentation_view_renders(full_state):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    at.toggle[0].set_value(True).run()
    assert not at.exception, [e.value for e in at.exception]
