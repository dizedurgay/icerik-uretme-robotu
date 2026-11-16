"""Aşama 3b testleri: blog, sosyal, görsel promptu + yükleme (llm mock'lanır; gerçek API çağrısı yok)."""
from __future__ import annotations

from io import BytesIO

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from contentflow import config, llm, models, prompts, storage
from contentflow.generators import calendar as cal_gen
from contentflow.generators import content
from tests import sample_data as sd


def png_bytes(color="#3B2A20") -> bytes:
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()

ROOT = Path(__file__).resolve().parent.parent
OUT = {models.BlogPost: sd.BLOG, models.SocialPost: sd.SOCIAL, models.ImagePrompt: sd.IMAGE_PROMPT,
       models.CalendarDraft: sd.CALENDAR}


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    calls = []

    def fake_structured(**kw):
        calls.append(kw)
        return llm.CallResult(OUT[kw["schema"]], f"log{len(calls)}", cached=False)

    monkeypatch.setattr(llm, "generate_structured", fake_structured)
    for key, obj in (("brand_identity", sd.IDENTITY), ("personas", sd.PERSONAS),
                     ("brand_voice", sd.VOICE), ("content_strategy", sd.STRATEGY)):
        storage.save_version(key, obj.model_dump(mode="json"))
    cal_gen.generate_calendar(date(2026, 11, 23))
    calls.clear()
    return calls


def test_blog_prompt_is_costar_and_linked(setup):
    item = content.items_with("blog")[0]
    _, issues = content.generate_blog(item["id"])
    kw = setup[0]
    for h in ("# Context", "# Objective", "# Style", "# Tone", "# Audience", "# Response"):
        assert h in kw["user_prompt"]
    assert "$" not in kw["user_prompt"] and models.SOURCE_TAG in kw["user_prompt"]
    assert kw["with_brand_voice"] is True and kw["calendar_item_id"] == item["id"]
    assert storage.get_current_version("blog")["calendar_item_id"] == item["id"]
    assert issues == []


def test_three_social_posts_rtf(setup):
    for item in content.items_with("social_post")[:3]:
        content.generate_social(item["id"])
    assert storage.count_filled("social_post:") == 3
    for kw in setup:
        assert all(h in kw["user_prompt"] for h in ("# Role", "# Task", "# Format"))
        assert "$" not in kw["user_prompt"] and kw["formula"] == "RTF"


def test_image_prompt_uses_post_description_and_palette(setup):
    item = content.items_with("image")[0]
    content.generate_social(item["id"])
    content.generate_image_prompt(item["id"])
    assert "Ahşap masada fincan." in setup[-1]["user_prompt"]
    assert "#3B2A20" in setup[-1]["user_prompt"]  # palet HEX'leri görsel stil bloğunda


def test_final_prompt_has_safety_suffix_and_aspect():
    p = content.final_image_prompt("A cup on a desk.", "1024x1536")
    assert content.IMAGE_SAFETY_SUFFIX in p and p.endswith("Vertical 2:3 aspect ratio (portrait).")
    assert content.final_image_prompt(p, "1024x1536").count(content.IMAGE_SAFETY_SUFFIX) == 1


def test_upload_saves_versioned_file_and_logs_tool(setup):
    item = content.items_with("image")[0]
    content.generate_image_prompt(item["id"])
    v1 = content.save_uploaded_image(item["id"], png_bytes(), "gorsel.png", "ChatGPT")
    v2 = content.save_uploaded_image(item["id"], png_bytes("#F4EBDD"), "yeni.jpeg", "Canva")
    assert (v1, v2) == (1, 2)
    sec = storage.get_section(f"image:{item['id']}")
    assert [v["content"]["tool"] for v in sec["versions"]] == ["ChatGPT", "Canva"]
    cur = storage.get_current(f"image:{item['id']}")
    assert cur["path"].endswith("_v2.jpg") and not Path(cur["path"]).is_absolute()
    assert content.image_path(cur).exists()
    assert content.IMAGE_SAFETY_SUFFIX in cur["prompt"]
    logs = [r for r in storage.read_jsonl(storage.prompt_log_path()) if r.get("kind") == "image_upload"]
    assert [r["tool"] for r in logs] == ["ChatGPT", "Canva"] and logs[0]["calendar_item_id"] == item["id"]
    assert storage.get_current_version(f"image:{item['id']}")["source"] == "human"


def test_upload_rejects_bad_input(setup):
    item = content.items_with("image")[0]
    with pytest.raises(llm.LLMError, match="görsel promptunu"):
        content.save_uploaded_image(item["id"], png_bytes(), "a.png", "Gemini")
    content.generate_image_prompt(item["id"])
    with pytest.raises(llm.LLMError, match="geçerli bir görsel değil"):
        content.save_uploaded_image(item["id"], b"not an image", "a.png", "Gemini")
    with pytest.raises(llm.LLMError, match="Desteklenmeyen"):
        content.save_uploaded_image(item["id"], png_bytes(), "a.gif", "Gemini")
    with pytest.raises(llm.LLMError, match="Geçersiz araç"):
        content.save_uploaded_image(item["id"], png_bytes(), "a.png", "Midjourney")


def test_portrait_size_for_reels():
    assert content.default_size({"channel": "TikTok/Reels", "format": "Dikey video"}) == "1024x1536"
    assert content.default_size({"channel": "Instagram", "format": "Carousel"}) == "1024x1024"


def test_check_blog_flags():
    bad = sd.BLOG.model_copy(update={
        "meta_description": "x" * 160, "body_markdown": "# H1\n\nKahvelerin %73'ü sabah içiliyor.",
        "secondary_keywords": ["a"]})
    found = " | ".join(models.check_blog(bad))
    for s in ("Kelime sayısı", "155", "H1", "İkincil", "kaynak işaretsiz", "H2"):
        assert s in found, s
    ok = sd.BLOG.model_copy(update={"body_markdown": sd.BLOG.body_markdown + f" Oran %73. {models.SOURCE_TAG}"})
    assert not any("kaynak işaretsiz" in i for i in models.check_blog(ok))


def test_check_image_prompt_forbidden_but_negations_ok():
    bad = sd.IMAGE_PROMPT.model_copy(update={"prompt_en": sd.IMAGE_PROMPT.prompt_en + " in the style of Someone, Starbucks cup."})
    found = " | ".join(models.check_image_prompt(bad))
    assert "in the style of" in found and "starbucks" in found
    ok = sd.IMAGE_PROMPT.model_copy(update={"prompt_en": sd.IMAGE_PROMPT.prompt_en + " " + content.IMAGE_SAFETY_SUFFIX})
    assert models.check_image_prompt(ok) == []


def test_progress_stage4_partial(setup):
    content.generate_blog(content.items_with("blog")[0]["id"])
    s4 = storage.stage_progress()[3]
    assert s4["partial"] and not s4["done"]


def test_page_renders_with_content(setup):
    content.generate_blog(content.items_with("blog")[0]["id"])
    for item in content.items_with("image"):
        content.generate_social(item["id"]) if "social_post" in item["deliverables"] else None
        content.generate_image_prompt(item["id"])
        content.save_uploaded_image(item["id"], png_bytes(), "g.png", "Gemini")
    at = AppTest.from_file(str(ROOT / "pages/4_Icerik_Uretimi.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
