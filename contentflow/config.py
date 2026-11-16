"""Merkezi ayarlar: model adları, ses seçenekleri, kota ve yollar.

Sistem tamamen ücretsiz araçlarla çalışır:
- Metin: Google Gemini API ücretsiz katmanı (google-genai SDK)
- Görsel: API yok; kullanıcı promptu ChatGPT/Gemini/Canva'da ücretsiz üretip yükler
- Ses: edge-tts (anahtar gerektirmez)
Model adları değişir; hepsi .env'den okunur, burada yalnızca varsayılanlar durur.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# --- Uygulama adı ---
APP_NAME = "İçerik Üretme Robotu"
APP_SLUG = "icerik-uretme-robotu"

# --- Yollar ---
BRAND_SEED_PATH = ROOT_DIR / "brand" / "brand_seed.yaml"
PROMPTS_DIR = ROOT_DIR / "contentflow" / "prompts"
FONTS_DIR = ROOT_DIR / "assets" / "fonts"
MUSIC_DIR = ROOT_DIR / "assets" / "music"
# Alt yollar (state.json, images/ ...) storage.py içinde WORKSPACE_DIR'dan türetilir;
# böylece testler yalnızca bu değişkeni geçici bir klasöre yönlendirebilir.
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", ROOT_DIR / "workspace"))

# --- Metin modelleri (Gemini ücretsiz katman; güncel liste: aistudio.google.com/docs/pricing) ---
TEXT_MODEL = os.getenv("TEXT_MODEL", "gemini-3.8-flash")
# Kontrol katmanı daha hafif bir modelle çalışır; günlük ücretsiz kotayı korur.
REVIEW_MODEL = os.getenv("REVIEW_MODEL", "gemini-3.5-flash-lite")

# Ana model yoğunsa (503) veya günlük kotası dolduysa sırayla denenecek yedek ücretsiz modeller.
# Her modelin kotası ayrıdır; bu yüzden yedek zinciri hem yoğunluğa hem kotaya çare olur.
FALLBACK_MODELS = [m.strip() for m in os.getenv(
    "FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite").split(",") if m.strip()]

# Günlük istek sayacının üst sınırı. YALNIZCA BİLGİ AMAÇLI: gerçek limit modele ve hesaba göre
# değişir; AI Studio → Rate limits sayfasından kendi değerini bakıp .env'ye yaz.
GEMINI_DAILY_REQUEST_LIMIT = int(os.getenv("GEMINI_DAILY_REQUEST_LIMIT", "250"))

# --- 429 (kota) davranışı ---
MAX_RETRIES = 5                # geçici hatalarda toplam deneme
RETRY_BASE_DELAY_S = 2.0       # üstel geri çekilme tabanı: 2, 4, 8, ... sn
MAX_RATE_LIMIT_WAIT_S = 65.0   # dakikalık kota için tek seferde en fazla bekleme
SERVER_ERROR_RETRIES = 2       # 5xx/503'te aynı modelde deneme sayısı; sonra yedek modele geçilir

# --- Görsel üretim araçları (kullanıcı kendi üretip yükler) ---
IMAGE_TOOLS = ["ChatGPT", "Gemini", "Canva", "Diğer"]

# --- Ses (edge-tts) ---
TTS_ENGINE = "edge-tts"
TTS_VOICES = {
    "tr-TR-EmelNeural": "Emel (kadın)",
    "tr-TR-AhmetNeural": "Ahmet (erkek)",
}
TTS_VOICE = os.getenv("TTS_VOICE", "tr-TR-EmelNeural")
TTS_WORDS_PER_SECOND = 2.3  # Türkçe konuşma hızı için kaba tahmin (süre tahmini)


def api_key_present() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())
