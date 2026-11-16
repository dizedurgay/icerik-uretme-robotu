"""Aşama 1 (Marka Kimliği) ve Aşama 2 (Ses ve Strateji) üreticileri.

Her fonksiyon: promptu şablondan doldurur → llm ile yapılandırılmış çıktı alır →
state'e yeni versiyon olarak kaydeder → (CallResult, uyarılar) döndürür.
use_cache=False "Yeniden üret" anlamına gelir.
"""
from __future__ import annotations

from pydantic import BaseModel

from contentflow import llm, models, prompts, render, storage


def _run(
    *, key: str, template: str, task: str, stage: str, schema: type[BaseModel],
    variables: dict, use_cache: bool, with_brand_voice: bool, checker,
) -> tuple[llm.CallResult, list[str]]:
    result = llm.generate_structured(
        task=task, stage=stage, formula=prompts.formula(template),
        user_prompt=prompts.render(template, **variables), schema=schema,
        with_brand_voice=with_brand_voice, use_cache=use_cache,
    )
    content = result.output.model_dump(mode="json")
    current = storage.get_current_version(key)
    # Önbellekten aynı sonuç geldiyse yinelenen versiyon oluşturma
    if not (result.cached and current and current["log_id"] == result.log_id):
        storage.save_version(key, content, source="ai", log_id=result.log_id)
    return result, checker(result.output)


def _ctx() -> dict:
    seed = storage.load_brand_seed()
    return {
        "seed": render.seed_block(seed),
        "identity": render.identity_block(storage.get_current("brand_identity")),
        "personas": render.persona_block(storage.get_current("personas")),
        "address_form": seed.get("address_form", "sen"),
        "audience": seed["target_audience_hint"],
        "channels": ", ".join(seed.get("channels", [])),
        "persona_count": int(seed.get("persona_count", 1)),
    }


# --------------------------------------------------------------------- Aşama 1


def generate_identity(use_cache: bool = True):
    # Marka sesi henüz yok ve kimlik sesin kaynağı; bu yüzden enjeksiyon kapalı.
    return _run(key="brand_identity", template="brand_identity", task="brand_identity", stage="aşama1",
                schema=models.BrandIdentity, variables=_ctx(), use_cache=use_cache,
                with_brand_voice=False, checker=models.check_identity)


def generate_competitors(use_cache: bool = True):
    result, issues = _run(key="competitors", template="competitor_analysis", task="competitor_analysis",
                          stage="aşama1", schema=models.CompetitorAnalysis, variables=_ctx(),
                          use_cache=use_cache, with_brand_voice=False, checker=models.check_competitors)
    if any(c.verified for c in result.output.competitors):
        # Model kurala uymasa bile doğrulanmamış olarak işaretle.
        content = storage.get_current("competitors")
        for c in content["competitors"]:
            c["verified"] = False
        storage.save_version("competitors", content, source="ai", log_id=result.log_id,
                             note="verified alanları false'a zorlandı")
    return result, issues


# --------------------------------------------------------------------- Aşama 2


def generate_personas(use_cache: bool = True):
    ctx = _ctx()
    return _run(key="personas", template="personas", task="personas", stage="aşama2",
                schema=models.PersonaSet, variables=ctx, use_cache=use_cache, with_brand_voice=False,
                checker=lambda x: models.check_personas(x, ctx["persona_count"]))


def generate_voice(use_cache: bool = True):
    # Rehberi yeniden üretirken eski rehberi enjekte etmek modeli eskisine kilitler; kapalı.
    return _run(key="brand_voice", template="brand_voice", task="brand_voice", stage="aşama2",
                schema=models.BrandVoice, variables=_ctx(), use_cache=use_cache,
                with_brand_voice=False, checker=models.check_voice)


def generate_strategy(use_cache: bool = True):
    """Neden-Kime-Ne-Nasıl + içerik sütunları. Marka sesi burada system prompt'a girer."""
    return _run(key="content_strategy", template="content_pillars", task="content_pillars",
                stage="aşama2", schema=models.ContentStrategy, variables=_ctx(),
                use_cache=use_cache, with_brand_voice=True, checker=models.check_strategy)
