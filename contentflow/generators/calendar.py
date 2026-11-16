"""Aşama 3a: 7 günlük içerik takvimi.

LLM yalnızca stratejik alanları üretir (gün, kanal, format, sütun, persona, konu, amaç, gerekçe).
id, tarih, gün adı ve durum kodda eklenir: tarih hesabını modele bırakmak hata riskidir.
"""
from __future__ import annotations

from datetime import date, timedelta

from contentflow import llm, models, prompts, render, storage

WEEKDAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def next_monday(today: date | None = None) -> date:
    today = today or date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def day_info(start: date, day: int) -> tuple[str, str]:
    d = start + timedelta(days=day - 1)
    return d.isoformat(), WEEKDAYS_TR[d.weekday()]


def pillar_names() -> list[str]:
    strat = storage.get_current("content_strategy") or {"pillars": []}
    return [p["name"] for p in strat["pillars"]]


def persona_names() -> list[str]:
    personas = storage.get_current("personas") or {"personas": []}
    return [p["name"] for p in personas["personas"]]


def normalize_items(items: list[dict], start: date) -> list[dict]:
    """Satırları gün/saate göre sıralar; tarih ve gün adını yeniden hesaplar; eksik id/durum ekler.
    Var olan id'ler korunur (üretilen içerikler calendar_item_id ile bu satırlara bağlı)."""
    rows = sorted(items, key=lambda i: (int(i["day"]), str(i.get("time_slot") or "")))
    used = {r["id"] for r in rows if r.get("id")}
    n = 0
    for r in rows:
        r["day"] = int(r["day"])
        r["date"], r["weekday"] = day_info(start, r["day"])
        r["deliverables"] = list(r.get("deliverables") or [])
        r.setdefault("status", models.STATUS_OPTIONS[0])
        if not r.get("status"):
            r["status"] = models.STATUS_OPTIONS[0]
        if not r.get("id"):
            while f"cal-{(n := n + 1):02d}" in used:
                pass
            r["id"] = f"cal-{n:02d}"
            used.add(r["id"])
    return rows


def issues(calendar: dict) -> list[str]:
    return models.check_calendar(calendar["items"], pillar_names(), persona_names())


def generate_calendar(start: date, use_cache: bool = True) -> tuple[llm.CallResult, list[str]]:
    seed = storage.load_brand_seed()
    days = "\n".join(f"- {d}. gün: {day_info(start, d)[1]} {day_info(start, d)[0]}" for d in range(1, 8))
    user_prompt = prompts.render(
        "calendar",
        seed=render.seed_block(seed),
        personas=render.persona_block(storage.get_current("personas")),
        pillars=render.pillars_block(storage.get_current("content_strategy")),
        days=days,
        pillar_names=" | ".join(pillar_names()),
        persona_names=" | ".join(persona_names()),
        channels=", ".join(seed.get("channels", [])),
    )
    result = llm.generate_structured(
        task="calendar", stage="aşama3", formula=prompts.formula("calendar"), user_prompt=user_prompt,
        schema=models.CalendarDraft, with_brand_voice=True, use_cache=use_cache,
    )
    draft = result.output
    calendar = {
        "start_date": start.isoformat(),
        "strategy_note": draft.strategy_note,
        "items": normalize_items([i.model_dump(mode="json") for i in draft.items], start),
    }
    current = storage.get_current_version("calendar")
    if not (result.cached and current and current["log_id"] == result.log_id):
        storage.save_version("calendar", calendar, source="ai", log_id=result.log_id)
    return result, issues(calendar)
