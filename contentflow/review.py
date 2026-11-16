"""Aşama 4: AI çıktı kontrol katmanı (ikinci LLM geçişi), öneriye göre düzeltme, karar kaydı.

State anahtarları:
  review:<içerik anahtarı>    → ReviewReport + {"reviewed_version": n}
  decision:<içerik anahtarı>  → {"karar", "not", "manual_checks", "decided_version"}
Düzeltme, içeriğin kendi bölümüne source="fix" ile YENİ versiyon olarak yazılır; eskisi silinmez.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel

from contentflow import config, llm, models, prompts, render, storage
from contentflow.generators import content as cgen


@dataclass
class ReviewItem:
    key: str              # içerik bölümünün state anahtarı
    label: str
    content_type: str
    schema: type[BaseModel]
    calendar_item_id: str | None
    is_image: bool = False


IMAGE_MANUAL_CHECKS = {
    "fake_text": "Görselde okunamayan/sahte yazı, harf veya logo benzeri işaret var mı?",
    "real_person": "Görseldeki bir yüz/kişi gerçek veya ünlü birine benziyor mu?",
    "other_brand": "Başka bir markanın ürünü/ambalajı tanınabiliyor mu?",
}


def review_items() -> list[ReviewItem]:
    """Kontrol edilecek tüm üretilmiş içerikler."""
    items: list[ReviewItem] = []

    def cal(key: str) -> str | None:
        v = storage.get_current_version(key)
        return v.get("calendar_item_id") if v else None

    if storage.get_current("blog"):
        items.append(ReviewItem("blog", "Blog yazısı", "SEO blog yazısı", models.BlogPost, cal("blog")))
    for k in storage.keys_with_prefix("social_post:"):
        cid = k.split(":", 1)[1]
        items.append(ReviewItem(k, f"Sosyal gönderi · {cid}", "sosyal medya gönderisi", models.SocialPost, cid))
    for k in storage.keys_with_prefix("image_prompt:"):
        cid = k.split(":", 1)[1]
        items.append(ReviewItem(k, f"Görsel · {cid}", "görsel üretim promptu (görsel harici araçla üretildi)",
                                models.ImagePrompt, cid, is_image=True))
    if storage.get_current("voiceover_script"):
        items.append(ReviewItem("voiceover_script", "Seslendirme metni", "TTS seslendirme metni",
                                models.VoiceoverScript, cal("voiceover_script")))
    if storage.get_current("video_script"):
        items.append(ReviewItem("video_script", "Video senaryosu", "kısa video senaryosu", models.VideoScript,
                                cal("video_script")))
    return items


def _context(item: ReviewItem) -> tuple[str, str]:
    try:
        row = cgen.get_item(item.calendar_item_id) if item.calendar_item_id else None
    except KeyError:
        row = None
    ctx = (f"{row['channel']} · {row['format']} · sütun: {row['pillar']} · persona: {row['persona']} · "
           f"amaç: {row['goal']}") if row else "-"
    hint = row["topic"] if row else "-"
    if item.key == "blog":
        b = storage.get_current("blog")
        hint = f"odak: {b['focus_keyword']}; ikincil: {', '.join(b['secondary_keywords'])}"
    return ctx, hint


def _brand_facts() -> str:
    seed = storage.load_brand_seed()
    return f"{render.seed_block(seed)}\n{render.identity_block(storage.get_current('brand_identity'))}"


def run_review(item: ReviewItem, use_cache: bool = True) -> tuple[llm.CallResult, list[str]]:
    ver = storage.get_current_version(item.key)
    ctx, hint = _context(item)
    result = llm.generate_structured(
        task=f"review:{item.key.split(':')[0]}", stage="aşama4", formula=prompts.formula("review"),
        schema=models.ReviewReport, model=config.REVIEW_MODEL, with_brand_voice=True,
        calendar_item_id=item.calendar_item_id, use_cache=use_cache,
        user_prompt=prompts.render(
            "review", content_type=item.content_type, context=ctx, keyword_hint=hint,
            content=render.generic_markdown(ver["content"]), brand_facts=_brand_facts(),
            address_form=storage.load_brand_seed().get("address_form", "sen")),
    )
    data = {**result.output.model_dump(mode="json"), "reviewed_version": ver["v"]}
    storage.save_version(f"review:{item.key}", data, source="ai", log_id=result.log_id,
                         calendar_item_id=item.calendar_item_id)
    return result, []


def apply_fix(item: ReviewItem) -> int:
    """Kontrol önerilerine göre düzeltilmiş YENİ versiyon üretir. Yeni versiyon numarasını döner."""
    report = storage.get_current(f"review:{item.key}")
    if not report:
        raise llm.LLMError("Önce kontrolü çalıştır.")
    ver = storage.get_current_version(item.key)
    result = llm.generate_structured(
        task=f"fix:{item.key.split(':')[0]}", stage="aşama4", formula=prompts.formula("fix"), schema=item.schema,
        with_brand_voice=True, calendar_item_id=item.calendar_item_id, use_cache=False,
        user_prompt=prompts.render(
            "fix", content_type=item.content_type,
            content=json.dumps(ver["content"], ensure_ascii=False, indent=2),
            report=json.dumps({k: v for k, v in report.items() if k != "reviewed_version"},
                              ensure_ascii=False, indent=2)),
    )
    return storage.save_version(item.key, result.output.model_dump(mode="json"), source="fix",
                                log_id=result.log_id, calendar_item_id=item.calendar_item_id,
                                note=f"v{ver['v']} kontrol önerilerine göre düzeltildi")


def save_decision(item: ReviewItem, karar: str, note: str, manual_checks: dict[str, bool] | None = None) -> None:
    if karar not in models.DECISIONS:
        raise ValueError(karar)
    ver = storage.get_current_version(item.key)
    storage.save_version(f"decision:{item.key}", {
        "karar": karar, "not": note.strip(), "manual_checks": manual_checks or {}, "decided_version": ver["v"],
    }, source="human", calendar_item_id=item.calendar_item_id)


def summary() -> dict[str, int]:
    items = review_items()
    reviewed = sum(storage.get_current(f"review:{i.key}") is not None for i in items)
    decided = sum(storage.get_current(f"decision:{i.key}") is not None for i in items)
    return {"total": len(items), "reviewed": reviewed, "decided": decided}
