"""State içeriğini okunur Markdown'a çeviren yardımcılar.

Aynı metinler hem promptlara bağlam olarak girer hem de (Milestone 7'de) dışa aktarılan
dokümanlarda kullanılır; tek yerde tutmak tutarlılık sağlar.
"""
from __future__ import annotations

from typing import Any


def seed_block(seed: dict) -> str:
    values = ", ".join(seed.get("values_hint", []))
    channels = ", ".join(seed.get("channels", []))
    return (
        f"- Marka adı: {seed['name']}\n"
        f"- Sektör: {seed['sector']}\n"
        f"- Konum: {seed['location']}\n"
        f"- Tek cümlelik vaat: {seed['one_liner']}\n"
        f"- Hedef kitle ipucu: {seed['target_audience_hint']}\n"
        f"- Değer ipuçları: {values}\n"
        f"- Kanallar: {channels}\n"
        f"- Hitap: {seed.get('address_form', 'sen')}"
    )


def identity_block(identity: dict | None) -> str:
    if not identity:
        return "(Henüz marka kimliği yok.)"
    values = "\n".join(f"  - {v['name']}: {v['description']}" for v in identity["values"])
    palette = "\n".join(f"  - {c['name']} {c['hex']}: {c['usage']}" for c in identity["palette"])
    return (
        f"- Hikâye: {identity['story']}\n"
        f"- Misyon: {identity['mission']}\n"
        f"- Değerler:\n{values}\n"
        f"- Renk paleti:\n{palette}"
    )


def visual_style_block(identity: dict) -> str:
    vs = identity["visual_style"]
    hexes = ", ".join(f"{c['hex']} ({c['name']})" for c in identity["palette"])
    return (
        f"Stil: {vs['style']}\nIşık: {vs['lighting']}\nKompozisyon: {vs['composition']}\n"
        f"Renk kullanımı: {vs['color_usage']} Palet: {hexes}\n"
        f"Yasaklar: {'; '.join(vs['forbidden'])}"
    )


def persona_block(personas: dict | None) -> str:
    if not personas:
        return "(Henüz persona yok.)"
    out = []
    for p in personas["personas"]:
        habits = "; ".join(f"{h['channel']}: {h['habit']}" for h in p["channel_habits"])
        out.append(
            f"### {p['name']} ({p['age']}, {p['occupation']}, {p['location']})\n"
            f"- Gün içi rutin: {p['daily_routine']}\n"
            f"- Kahve alışkanlığı: {p['coffee_habit']}\n"
            f"- Acı noktaları: {'; '.join(p['pain_points'])}\n"
            f"- Motivasyonlar: {'; '.join(p['motivations'])}\n"
            f"- Kanal alışkanlıkları: {habits}\n"
            f"- Söz: \"{p['quote']}\""
        )
    return "\n\n".join(out)


def pillars_block(strategy: dict | None) -> str:
    if not strategy:
        return "(Henüz içerik sütunu yok.)"
    return "\n".join(
        f"- **{p['name']}** — amaç: {p['purpose']}; persona eşleşmesi: {p['persona_match']}; "
        f"kanallar: {', '.join(p['best_channels'])}"
        for p in strategy["pillars"]
    )


def brand_voice_markdown(voice: dict) -> str:
    """Marka Sesi Rehberi: system prompt'a giren ve dışa aktarılan tek sayfalık metin."""
    personality = "\n".join(f"- **{a['adjective']}**: {a['meaning']}" for a in voice["personality"])
    table = "\n".join(f"| {r['we_are']} | {r['we_are_not']} |" for r in voice["we_are_table"])
    good = "\n".join(f"- ✅ {s}" for s in voice["good_examples"])
    bad = "\n".join(f"- ❌ {b['sentence']} — _{b['why_bad']}_" for b in voice["bad_examples"])
    return (
        f"**Kişilik:**\n{personality}\n\n"
        f"| Biz şuyuz | Şu değiliz |\n|---|---|\n{table}\n\n"
        f"**Kullan:** {', '.join(voice['words_to_use'])}\n\n"
        f"**Kaçın:** {', '.join(voice['words_to_avoid'])}\n\n"
        f"**Hitap:** {voice['address_rule']}\n\n"
        f"**Emoji:** {voice['emoji_rule']}\n\n"
        f"**İyi örnekler:**\n{good}\n\n"
        f"**Kötü örnekler:**\n{bad}"
    )


def generic_markdown(value: Any, indent: int = 0) -> str:
    """Şeması bilinmeyen sözlük/listeler için basit Markdown."""
    pad = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines += [f"{pad}- {k}:", generic_markdown(v, indent + 1)]
            else:
                lines.append(f"{pad}- {k}: {v}")
        return "\n".join(lines)
    if isinstance(value, list):
        return "\n".join(
            generic_markdown(v, indent) if isinstance(v, (dict, list)) else f"{pad}- {v}" for v in value
        )
    return f"{pad}{value}"
