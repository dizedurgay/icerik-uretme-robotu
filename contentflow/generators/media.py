"""Aşama 3c: seslendirme (edge-tts) ve kısa video (moviepy montajı).

State anahtarları:
  voiceover_script  → VoiceoverScript (metin)
  voiceover         → {"path", "voice", "rate", "pitch", "text", "duration_s"}
  video_script      → VideoScript
  video             → {"path", "duration", "audio_duration", "scenes": [{image_key, text}]}
"""
from __future__ import annotations

from pathlib import Path

from contentflow import config, llm, models, prompts, render, storage, video
from contentflow.generators import content


def video_item() -> dict | None:
    rows = content.items_with("video") or content.items_with("voiceover")
    return rows[0] if rows else None


def voice_settings() -> tuple[str, str]:
    """Marka sesi rehberinden edge-tts hız/perde değerleri."""
    v = storage.get_current("brand_voice") or {}
    return f"{int(v.get('tts_rate_percent', 0)):+d}%", f"{int(v.get('tts_pitch_hz', 0)):+d}Hz"


def generate_voiceover_script(use_cache: bool = True):
    item, seed = video_item(), storage.load_brand_seed()
    result = llm.generate_structured(
        task="voiceover_script", stage="aşama3", formula=prompts.formula("voiceover"), schema=models.VoiceoverScript,
        user_prompt=prompts.render(
            "voiceover", brand_name=seed["name"], topic=item["topic"], channel=item["channel"],
            pillar=item["pillar"], goal=item["goal"], persona=content.persona_text(item["persona"]),
            one_liner=seed["one_liner"], address_form=seed.get("address_form", "sen")),
        with_brand_voice=True, calendar_item_id=item["id"], use_cache=use_cache,
    )
    content._save("voiceover_script", result, result.output.model_dump(mode="json"), item["id"])
    return result, models.check_voiceover(result.output)


def synthesize_voiceover(voice: str, rate: str, pitch: str, use_cache: bool = True):
    script = storage.get_current("voiceover_script")
    if not script:
        raise llm.LLMError("Önce seslendirme metnini üret.")
    item = video_item()
    result = llm.generate_speech(task="voiceover", stage="aşama3", text=script["text"], voice=voice, rate=rate,
                                 pitch=pitch, filename_stem="seslendirme", calendar_item_id=item["id"],
                                 use_cache=use_cache)
    from moviepy import AudioFileClip
    with AudioFileClip(str(result.output)) as a:
        duration = round(a.duration, 2)
    rel = Path(result.output).resolve().relative_to(storage.workspace().resolve()).as_posix()
    data = {"path": rel, "voice": voice, "rate": rate, "pitch": pitch, "text": script["text"], "duration_s": duration}
    content._save("voiceover", result, data, item["id"])
    issues = [] if 15 <= duration <= 20 else [f"Seslendirme {duration} sn; hedef 15-20 sn. Metni kısalt/uzat "
                                              f"veya hızı ayarla."]
    return result, issues


def uploaded_images() -> list[tuple[str, dict]]:
    """[(state anahtarı, içerik)] — yüklenmiş tüm görseller."""
    return [(k, storage.get_current(k)) for k in storage.keys_with_prefix("image:")]


def generate_video_script(use_cache: bool = True):
    item, seed = video_item(), storage.load_brand_seed()
    vo = storage.get_current("voiceover_script")
    if not vo:
        raise llm.LLMError("Önce seslendirme metnini üret; senaryo ona göre kurulur.")
    imgs = "\n".join(f"- {k.split(':', 1)[1]}: {(storage.get_current('image_prompt:' + k.split(':', 1)[1]) or {}).get('description_tr', '')}"
                     for k, _ in uploaded_images()) or "(henüz yüklenmiş görsel yok)"
    result = llm.generate_structured(
        task="video_script", stage="aşama3", formula=prompts.formula("video_script"), schema=models.VideoScript,
        user_prompt=prompts.render("video_script", voiceover=vo["text"], images=imgs, brand_name=seed["name"],
                                   one_liner=seed["one_liner"], persona=content.persona_text(item["persona"])),
        with_brand_voice=True, calendar_item_id=item["id"], use_cache=use_cache,
    )
    content._save("video_script", result, result.output.model_dump(mode="json"), item["id"])
    return result, models.check_video_script(result.output)


def accent_color() -> str:
    """Paletten vurgu rengi: 'vurgu' geçen renk, yoksa en doygun olanı."""
    palette = (storage.get_current("brand_identity") or {}).get("palette", [])
    for c in palette:
        if "vurgu" in c.get("usage", "").casefold() and models.HEX_RE.match(c["hex"]):
            return c["hex"]
    valid = [c["hex"] for c in palette if models.HEX_RE.match(c.get("hex", ""))]
    if not valid:
        return "#E07A3F"
    sat = lambda h: max(video._hex(h)) - min(video._hex(h))  # noqa: E731
    return max(valid, key=sat)


def render_video(image_keys: list[str]) -> dict:
    """Seçilen görsellerle videoyu montajlar. image_keys: sahne başına 'image:cal-xx' anahtarı."""
    script, vo = storage.get_current("video_script"), storage.get_current("voiceover")
    if not script or not vo:
        raise llm.LLMError("Video için önce seslendirme sesi ve video senaryosu gerekli.")
    seed = storage.load_brand_seed()
    scenes = []
    for i, (s, key) in enumerate(zip(script["scenes"], image_keys)):
        img = storage.get_current(key)
        closing = i == len(script["scenes"]) - 1
        scenes.append(video.Scene(content.image_path(img), seed["name"] if closing else s["on_screen_text"],
                                  s["duration_s"], closing=closing))
    music = next(iter(sorted(config.MUSIC_DIR.glob("*.mp3"))), None) if config.MUSIC_DIR.exists() else None
    n = len((storage.get_section("video") or {"versions": []})["versions"]) + 1
    out = storage.subdir("video") / f"video_v{n}.mp4"
    try:
        info = video.build_video(scenes, storage.workspace() / vo["path"], out, accent_color(),
                                 brand_subtitle=script["closing_text"], music_path=music)
    except video.VideoError as exc:
        raise llm.LLMError(str(exc)) from exc
    data = {"path": out.relative_to(storage.workspace()).as_posix(), "duration": info["duration"],
            "audio_duration": info["audio_duration"], "music": music.name if music else None,
            "scenes": [{"image_key": k, "text": sc.text} for k, sc in zip(image_keys, scenes)]}
    storage.save_version("video", data, source="ai", calendar_item_id=(video_item() or {}).get("id"),
                         note="moviepy montajı")
    return data
