# İçerik Üretme Robotu — Yapay Zeka Destekli Marka İçerik Üretim Sistemi

Kurgusal kahve markası **Demlik & Co.** için marka stratejisi, içerik takvimi, blog, sosyal medya
gönderileri, görseller, seslendirme ve kısa video üreten Streamlit uygulaması.

**Tamamen ücretsiz çalışır:**

| Görev | Araç | Ücret |
|---|---|---|
| Metin (strateji, takvim, blog, gönderi, görsel promptu, kontrol) | Google Gemini API ücretsiz katmanı | Ücretsiz (günlük/dakikalık kota var) |
| Görsel | Uygulama promptu üretir → sen ChatGPT / Gemini / Canva'da üretip yüklersin | Ücretsiz |
| Seslendirme | edge-tts (Türkçe sesler) | Ücretsiz, anahtar gerekmez |
| Video | moviepy + ffmpeg (yerel montaj) | Ücretsiz |

## Kurulum

Gereksinimler: **Python 3.11+**, **ffmpeg** (video montajı için), ücretsiz bir **Gemini API anahtarı**.

```bash
# 1) Sanal ortam (Windows'ta birden fazla Python varsa: py -3.13 -m venv .venv)
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate

# 2) Bağımlılıklar
pip install -r requirements.txt

# 3) Ayarlar
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

### Gemini API anahtarı (ücretsiz)
1. [aistudio.google.com](https://aistudio.google.com) adresine Google hesabınla gir.
2. **Get API key → Create API key**.
3. Anahtarı `.env` dosyasındaki `GEMINI_API_KEY=` satırına yapıştır.

> **Gizlilik notu:** Ücretsiz katmanda gönderilen içerik Google ürünlerini geliştirmek için kullanılabilir.
> Bu projede yalnızca kurgusal marka bilgisi gönderildiği için sorun yoktur; kişisel/gizli veri gönderme.

### ffmpeg kurulumu
- Windows: `winget install Gyan.FFmpeg` (sonra terminali yeniden aç)
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

Kontrol: `ffmpeg -version`

## Çalıştırma

```bash
streamlit run app.py
```

Soldaki menüdeki sayfaları sırayla izle: Marka Kimliği → Ses ve Strateji → İçerik Takvimi →
İçerik Üretimi → Kontrol → Dışa Aktar.

### Görseller nasıl eklenir?
1. **İçerik Üretimi → Görseller** sekmesinde bir satır için **Görsel promptu üret**.
2. Promptu kutunun sağ üstündeki kopyala simgesiyle kopyala; ChatGPT, Gemini veya Canva'da görseli üret.
3. **Hangi araçla ürettin?** kutusundan aracı seç, dosyayı yükle. Araç bilgisi prompt kütüphanesine ve
   AI kullanım raporuna otomatik yazılır.

### Video
Seslendirme metni → ses (edge-tts, Emel/Ahmet) → video senaryosu → sahnelere yüklediğin görselleri ata →
**Videoyu oluştur**. 1080×1920, 30 fps, H.264 MP4; üretim yaklaşık 1 dakika sürer. Video süresi seslendirmeye
göre ayarlanır; 15-20 sn için seslendirme metnini veya hız ayarını değiştir.

- **Müzik (isteğe bağlı):** Telif riski nedeniyle varsayılan olarak yok. Kendi telifsiz MP3'ünü
  `assets/music/` klasörüne koyarsan düşük sesle eklenir.
- **Font:** `assets/fonts/` içindeki Noto Sans (SIL Open Font License 1.1) — Türkçe karakter destekli.

### Kontrol ve dışa aktarım
**Kontrol** sayfasında her içerik ikinci bir LLM geçişiyle dört alanda denetlenir (ton, anahtar kelime,
telif/etik, kaynak). Riskli alanlarda **Öneriye göre düzelt** yeni sürüm üretir (eskisi silinmez); son kararı
sen verirsin. **Dışa Aktar** sayfası tüm teslim dosyalarını ve `icerik_seti.zip`'i `workspace/exports/` altına
üretir. Ana sayfadaki **Sunum Görünümü** tüm içeriği tek sayfada gösterir (Canva için ekran görüntüsü).

## Ücretsiz kota

- Kenar çubuğunda **bugünkü Gemini istek sayısı** görünür (önbellekten gelen yanıtlar sayılmaz).
- Aynı prompt tekrar gönderilirse yanıt önbellekten gelir; kota harcanmaz. **Yeniden üret** önbelleği atlar.
- **Dakikalık** sınıra takılınca uygulama Gemini'nin önerdiği süre kadar bekleyip otomatik tekrar dener.
- **Günlük** kota dolunca beklemez, açıklayıcı bir mesaj gösterir. Kota genellikle TR saatiyle sabah
  sıfırlanır; ya da `.env`'de `TEXT_MODEL`'i başka bir ücretsiz modele çevirebilirsin (kotalar model bazında).

## Ayarlar (.env)

| Değişken | Açıklama |
|---|---|
| `GEMINI_API_KEY` | Gemini API anahtarı (zorunlu) |
| `TEXT_MODEL` | Metin üretimi modeli (varsayılan `gemini-3.8-flash`) |
| `REVIEW_MODEL` | Kontrol katmanı modeli (varsayılan `gemini-3.5-flash-lite`) |
| `GEMINI_DAILY_REQUEST_LIMIT` | Günlük sayacın gösterdiği üst sınır; yalnızca bilgi amaçlı |
| `TTS_VOICE` | Varsayılan ses: `tr-TR-EmelNeural` veya `tr-TR-AhmetNeural` |

## Testler

```bash
pytest
```
Testler gerçek API çağrısı yapmaz (Gemini istemcisi ve edge-tts mock'lanır).

## Veri

Üretilen her şey `workspace/` altında durur (git'e girmez): `state.json` (tüm aşamalar, versiyonlu),
`prompt_log.jsonl` (her Gemini çağrısı, seslendirme, görsel yüklemesi ve elle düzenleme), `images/`,
`audio/`, `video/`, `exports/`.
