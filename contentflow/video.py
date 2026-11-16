"""Dikey tanıtım videosu montajı (moviepy 2.x + PIL).

Her kare PIL ile çizilir: Ken Burns (yavaş zoom/pan), sahneler arası crossfade, yarı saydam
şerit üzerinde Türkçe ekran metni, son sahnede marka adı + slogan. Ses: edge-tts MP3'ü.
Sahne süreleri seslendirme süresine göre orantılı ölçeklenir.
"""
from __future__ import annotations

import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from contentflow import config

W, H, FPS = 1080, 1920, 30
CROSSFADE_S = 0.4
ZOOM = 0.10          # sahne boyunca %10 yakınlaşma
TAIL_S = 0.6         # seslendirme bittikten sonra kapanış için ek süre


class VideoError(Exception):
    """Kullanıcıya gösterilecek Türkçe hata."""


@dataclass
class Scene:
    image_path: Path
    text: str
    duration: float
    closing: bool = False


def ffmpeg_available() -> bool:
    if shutil.which("ffmpeg"):
        return True
    try:  # moviepy, imageio-ffmpeg ile kendi ffmpeg ikilisini getirebilir
        import imageio_ffmpeg
        return Path(imageio_ffmpeg.get_ffmpeg_exe()).exists()
    except Exception:
        return False


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = config.FONTS_DIR / ("NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf")
    if not path.exists():
        raise VideoError(f"Font bulunamadı: {path}. assets/fonts/ klasörüne Noto Sans (OFL) ekle.")
    return ImageFont.truetype(str(path), size)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Görseli oranı bozmadan w×h alanı tamamen kaplayacak şekilde ölçekleyip ortalar."""
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _text_overlay(text: str, accent: str, closing: bool, subtitle: str = "") -> Image.Image:
    """Şeffaf katman: alt kısımda yarı saydam koyu şerit + beyaz metin (kapanışta ortada büyük)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if closing:
        d.rectangle((0, 0, W, H), fill=(0, 0, 0, 110))
        f1, f2 = _font(110), _font(52, bold=False)
        lines = textwrap.wrap(text, 14) or [text]
        y = H // 2 - 80 * len(lines)
        for line in lines:
            tw = d.textlength(line, font=f1)
            d.text(((W - tw) / 2, y), line, font=f1, fill="white")
            y += 135
        d.rectangle((W / 2 - 80, y + 10, W / 2 + 80, y + 18), fill=_hex(accent) + (255,))
        for line in textwrap.wrap(subtitle, 28):
            tw = d.textlength(line, font=f2)
            d.text(((W - tw) / 2, y + 50), line, font=f2, fill="white")
            y += 70
        return layer
    if not text.strip():
        return layer
    f = _font(72)
    lines = textwrap.wrap(text, 20)
    band_h = 90 * len(lines) + 80
    top = H - band_h - 260
    d.rectangle((0, top, W, top + band_h), fill=(0, 0, 0, 140))
    d.rectangle((0, top, 14, top + band_h), fill=_hex(accent) + (255,))
    y = top + 40
    for line in lines:
        tw = d.textlength(line, font=f)
        d.text(((W - tw) / 2, y), line, font=f, fill="white")
        y += 90
    return layer


def scale_durations(durations: list[float], target_total: float) -> list[float]:
    """Sahne sürelerini toplamı target_total olacak şekilde orantılı ölçekler."""
    total = sum(durations) or 1.0
    return [d * target_total / total for d in durations]


def build_video(scenes: list[Scene], audio_path: Path, out_path: Path, accent_hex: str,
                brand_subtitle: str = "", music_path: Path | None = None) -> dict:
    """Videoyu üretir ve {path, duration, audio_duration} döndürür."""
    from moviepy import AudioFileClip, CompositeAudioClip, VideoClip

    if not ffmpeg_available():
        raise VideoError("ffmpeg bulunamadı. Kurulum: Windows'ta `winget install Gyan.FFmpeg` "
                         "(sonra terminali yeniden aç). Ayrıntı README'de.")
    if not scenes:
        raise VideoError("Video için en az bir sahne gerekli.")
    for s in scenes:
        if not s.image_path.exists():
            raise VideoError(f"Sahne görseli bulunamadı: {s.image_path}")

    audio = AudioFileClip(str(audio_path))
    total = audio.duration + TAIL_S
    durations = scale_durations([s.duration for s in scenes], total)
    starts = np.cumsum([0.0] + durations[:-1])

    # Ön hazırlık: her sahnenin %ZOOM büyük kaplama görseli ve metin katmanı
    big_w, big_h = round(W * (1 + ZOOM)), round(H * (1 + ZOOM))
    bases, overlays = [], []
    for i, s in enumerate(scenes):
        img = Image.open(s.image_path).convert("RGB")
        img = _cover(img, big_w, big_h)
        if s.closing:
            img = ImageEnhance.Brightness(img).enhance(0.75)
        bases.append(img)
        overlays.append(_text_overlay(s.text, accent_hex, s.closing, brand_subtitle if s.closing else ""))

    def scene_frame(i: int, t_local: float) -> Image.Image:
        p = min(max(t_local / durations[i], 0.0), 1.0)
        z = 1 + ZOOM * p                       # 1.00 → 1.10 yakınlaşma
        cw, ch = big_w / z, big_h / z
        # tek/çift sahnelerde farklı yönde hafif kaydırma (pan)
        dx = (big_w - cw) * (p if i % 2 == 0 else 1 - p)
        dy = (big_h - ch) / 2
        crop = bases[i].crop((dx, dy, dx + cw, dy + ch)).resize((W, H), Image.BILINEAR)
        crop = crop.convert("RGBA")
        crop.alpha_composite(overlays[i])
        return crop

    def make_frame(t: float) -> np.ndarray:
        i = int(np.searchsorted(starts, t, side="right") - 1)
        i = max(0, min(i, len(scenes) - 1))
        frame = scene_frame(i, t - starts[i])
        end = starts[i] + durations[i]
        if i + 1 < len(scenes) and t > end - CROSSFADE_S:
            alpha = (t - (end - CROSSFADE_S)) / CROSSFADE_S
            nxt = scene_frame(i + 1, t - starts[i + 1])
            frame = Image.blend(frame, nxt, min(max(alpha, 0.0), 1.0))
        return np.asarray(frame.convert("RGB"))

    clip = VideoClip(make_frame, duration=total)
    track = audio
    if music_path and music_path.exists():
        music = AudioFileClip(str(music_path)).with_volume_scaled(0.12).with_duration(total)
        track = CompositeAudioClip([audio, music])
    clip = clip.with_audio(track)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        clip.write_videofile(str(out_path), fps=FPS, codec="libx264", audio_codec="aac",
                             preset="veryfast", threads=4, logger=None,
                             ffmpeg_params=["-pix_fmt", "yuv420p"])
    finally:
        clip.close()
        audio.close()
    return {"path": out_path, "duration": round(total, 2), "audio_duration": round(audio.duration, 2)}
