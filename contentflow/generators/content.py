"""Aşama 3b: blog (CO-STAR), sosyal gönderiler (RTF), görsel promptları ve görsel yüklemeleri.

Görseller API ile üretilmez (sistem ücretsiz kalsın diye): uygulama marka diline uygun promptu
üretir, kullanıcı onu ChatGPT / Gemini / Canva'da ücretsiz üretip yükler; kullanılan araç kaydedilir.

Her içerik bir takvim satırına bağlıdır (calendar_item_id). State anahtarları:
  blog                      → BlogPost (tek blog)
  social_post:<cal-id>      → SocialPost
  image_prompt:<cal-id>     → ImagePrompt
  image:<cal-id>            → {"path", "prompt", "size", "tool", "original_name"}
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from contentflow import config, llm, models, prompts, render, storage

# Kopyalanan her görsel promptuna kodla eklenir: model unutsa bile kural uygulanır.
IMAGE_SAFETY_SUFFIX = "No text, no letters, no logos, no brand packaging, no recognizable faces."
PORTRAIT_HINTS = ("reels", "tiktok", "story", "hikaye", "hikâye", "dikey", "video", "shorts")


# --------------------------------------------------------------------- yardımcılar


def calendar_items() -> list[dict]:
    return (storage.get_current("calendar") or {"items": []})["items"]


def get_item(item_id: str) -> dict:
    for item in calendar_items():
        if item["id"] == item_id:
            return item
    raise KeyError(f"Takvimde {item_id} yok")


def items_with(deliverable: str) -> list[dict]:
    return [i for i in calendar_items() if deliverable in (i.get("deliverables") or [])]


def pillar(name: str) -> dict:
    for p in (storage.get_current("content_strategy") or {"pillars": []})["pillars"]:
        if p["name"] == name:
            return p
    return {"name": name, "purpose": "", "description": "", "persona_match": "", "example_topics": [],
            "best_channels": []}


def persona_text(name: str) -> str:
    personas = storage.get_current("personas") or {"personas": []}
    chosen = [p for p in personas["personas"] if p["name"] == name] or personas["personas"]
    return render.persona_block({"personas": chosen})


def _save(key: str, result: llm.CallResult, content, item_id: str | None) -> None:
    current = storage.get_current_version(key)
    if not (result.cached and current and current["log_id"] == result.log_id):
        storage.save_version(key, content, source="ai", log_id=result.log_id, calendar_item_id=item_id)


def _structured(key: str, template: str, task: str, schema: type[BaseModel], item_id: str,
                variables: dict, use_cache: bool) -> llm.CallResult:
    result = llm.generate_structured(
        task=task, stage="aşama3", formula=prompts.formula(template),
        user_prompt=prompts.render(template, **variables), schema=schema, with_brand_voice=True,
        calendar_item_id=item_id, use_cache=use_cache,
    )
    _save(key, result, result.output.model_dump(mode="json"), item_id)
    return result


# --------------------------------------------------------------------- blog


def generate_blog(item_id: str, use_cache: bool = True) -> tuple[llm.CallResult, list[str]]:
    item, seed = get_item(item_id), storage.load_brand_seed()
    p = pillar(item["pillar"])
    result = _structured(
        "blog", "blog_costar", "blog", models.BlogPost, item_id, use_cache=use_cache,
        variables={
            "seed": render.seed_block(seed),
            "identity": render.identity_block(storage.get_current("brand_identity")),
            "topic": item["topic"], "pillar": item["pillar"], "goal": item["goal"],
            "rationale": item["rationale"],
            "pillar_detail": f"{p['description']} Amaç: {p['purpose']}. Persona eşleşmesi: {p['persona_match']}",
            "persona": persona_text(item["persona"]),
            "address_form": seed.get("address_form", "sen"),
            "source_tag": models.SOURCE_TAG,
        },
    )
    return result, models.check_blog(result.output)


# --------------------------------------------------------------------- sosyal


def generate_social(item_id: str, use_cache: bool = True) -> tuple[llm.CallResult, list[str]]:
    item, seed = get_item(item_id), storage.load_brand_seed()
    p = pillar(item["pillar"])
    result = _structured(
        f"social_post:{item_id}", "social_rtf", "social_post", models.SocialPost, item_id, use_cache=use_cache,
        variables={
            "channel": item["channel"], "format": item["format"], "topic": item["topic"],
            "pillar": item["pillar"], "pillar_purpose": p["purpose"], "goal": item["goal"],
            "rationale": item["rationale"], "persona": persona_text(item["persona"]),
            "brand_name": seed["name"], "one_liner": seed["one_liner"],
            "values": ", ".join(seed.get("values_hint", [])),
            "address_form": seed.get("address_form", "sen"),
        },
    )
    return result, models.check_social(result.output)


# --------------------------------------------------------------------- görsel


def default_size(item: dict) -> str:
    text = f"{item.get('channel', '')} {item.get('format', '')}".casefold()
    return "1024x1536" if any(h in text for h in PORTRAIT_HINTS) else "1024x1024"


def scene_for(item: dict) -> tuple[str, str]:
    """(sahne tarifi, kullanım yeri). Aynı satırın sosyal gönderisi varsa onun görsel tarifini kullanır."""
    post = storage.get_current(f"social_post:{item['id']}")
    if post:
        return post["image_description"], f"{item['channel']} gönderisinin görseli"
    if "blog" in (item.get("deliverables") or []):
        return f"Blog kapak görseli; konu: {item['topic']}", "blog kapak görseli"
    return f"{item['topic']} ({item['format']})", f"{item['channel']} içeriği"


def generate_image_prompt(item_id: str, use_cache: bool = True) -> tuple[llm.CallResult, list[str]]:
    item = get_item(item_id)
    identity = storage.get_current("brand_identity")
    scene, usage = scene_for(item)
    size = default_size(item)
    result = _structured(
        f"image_prompt:{item_id}", "image_prompt", "image_prompt", models.ImagePrompt, item_id,
        use_cache=use_cache,
        variables={
            "scene": scene, "usage": usage,
            "orientation": "dikey 2:3 (story/video)" if size == "1024x1536" else "kare 1:1 (feed)",
            "visual_style": render.visual_style_block(identity),
        },
    )
    return result, models.check_image_prompt(result.output)


ASPECT_TEXT = {"1024x1024": "Square 1:1 aspect ratio.", "1024x1536": "Vertical 2:3 aspect ratio (portrait)."}
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]


def final_image_prompt(prompt_en: str, size: str = "1024x1024") -> str:
    """Kullanıcının kopyalayacağı son prompt: güvenlik cümlesi + en-boy oranı (harici araçlarda
    boyut parametresi olmadığı için oran prompt metninde belirtilir)."""
    text = prompt_en.rstrip()
    if IMAGE_SAFETY_SUFFIX.casefold() not in text.casefold():
        text = f"{text} {IMAGE_SAFETY_SUFFIX}"
    return f"{text} {ASPECT_TEXT.get(size, '')}".strip()


def save_uploaded_image(item_id: str, data: bytes, original_name: str, tool: str,
                        size: str | None = None) -> int:
    """Harici araçta üretilip yüklenen görseli kaydeder, prompt loguna işler. Versiyon no döner."""
    if tool not in config.IMAGE_TOOLS:
        raise llm.LLMError(f"Geçersiz araç: {tool}")
    ext = Path(original_name).suffix.lower().lstrip(".")
    if ext not in ALLOWED_IMAGE_TYPES:
        raise llm.LLMError(f"Desteklenmeyen dosya türü: .{ext} (izin verilen: {', '.join(ALLOWED_IMAGE_TYPES)})")
    _verify_image(data)
    item = get_item(item_id)
    pv = storage.get_current_version(f"image_prompt:{item_id}")
    if not pv:
        raise llm.LLMError("Önce bu satır için görsel promptunu üret; görsel o prompta bağlanır.")
    size = size or default_size(item)
    prompt = final_image_prompt(pv["content"]["prompt_en"], size)

    v = len((storage.get_section(f"image:{item_id}") or {"versions": []})["versions"]) + 1
    path = storage.subdir("images") / f"{item_id}_v{v}.{'jpg' if ext == 'jpeg' else ext}"
    path.write_bytes(data)
    rel = path.relative_to(storage.workspace()).as_posix()
    log_id = llm.log_image_upload(task="image", stage="aşama3", prompt=prompt, tool=tool, path=rel,
                                  calendar_item_id=item_id, prompt_log_id=pv["log_id"])
    content = {"path": rel, "prompt": prompt, "size": size, "tool": tool, "original_name": original_name}
    return storage.save_version(f"image:{item_id}", content, source="human", log_id=log_id,
                                calendar_item_id=item_id, note=f"{tool} ile üretilip yüklendi")


def _verify_image(data: bytes) -> None:
    from io import BytesIO

    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(BytesIO(data)) as im:
            im.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise llm.LLMError("Yüklenen dosya geçerli bir görsel değil.") from exc


def image_path(content: dict) -> Path:
    return storage.workspace() / content["path"]
