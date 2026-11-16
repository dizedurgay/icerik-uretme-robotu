"""Tüm LLM çıktıları için pydantic v2 şemaları (structured outputs).

Notlar:
- Structured output şemaları sade tutulur: tüm alanlar zorunlu, varsayılan değer yok.
- Adet kısıtlarını (ör. 4-6 renk) şemaya değil prompta yazıyor ve `check_*` fonksiyonlarıyla
  üretimden SONRA denetliyoruz. Böylece model sınır dışı bir sayı döndürürse çağrı
  başarısız olmuyor; arayüz uyarı gösterip kullanıcıya "yeniden üret / düzenle" seçeneği sunuyor.
- Field açıklamaları JSON şemasına girer ve modele ek talimat görevi görür.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# =========================================================================== Aşama 1


class BrandValue(BaseModel):
    name: str = Field(description="Değerin kısa adı, ör. 'Şeffaf tedarik'")
    description: str = Field(description="Bu değerin markada somut olarak nasıl görüldüğü (1-2 cümle)")


class ColorSwatch(BaseModel):
    name: str = Field(description="Rengin Türkçe adı, ör. 'Kavrulmuş Çekirdek'")
    hex: str = Field(description="#RRGGBB biçiminde HEX kodu")
    usage: str = Field(description="Kullanım amacı: ana renk, vurgu, arka plan, metin vb.")


class Typography(BaseModel):
    heading_font: str = Field(description="Başlık fontu (yalnızca açık lisanslı, ör. Google Fonts/OFL)")
    body_font: str = Field(description="Gövde metni fontu (açık lisanslı)")
    license: str = Field(description="Lisans adı, ör. SIL Open Font License 1.1")
    rationale: str = Field(description="Neden bu ikili seçildi; Türkçe karakter desteği dahil")


class VisualStyle(BaseModel):
    style: str = Field(description="Fotoğraf mı illüstrasyon mu; genel estetik")
    lighting: str = Field(description="Işık tarifi")
    composition: str = Field(description="Kompozisyon ve kadraj kuralları")
    color_usage: str = Field(description="Paletin görsellerde nasıl kullanılacağı")
    forbidden: list[str] = Field(description="Görsellerde yasak olanlar (metin, logo, gerçek kişi vb.)")


class BrandIdentity(BaseModel):
    story: str = Field(description="Marka hikâyesi, 1-2 paragraf")
    mission: str = Field(description="Tek cümlelik misyon")
    values: list[BrandValue] = Field(description="3-5 marka değeri")
    palette: list[ColorSwatch] = Field(description="4-6 renk")
    typography: Typography
    visual_style: VisualStyle


class Competitor(BaseModel):
    name: str
    type: str = Field(description="Ör. ulusal zincir, uluslararası zincir, yerel butik kafe tipi")
    positioning: str = Field(description="Genel konumlandırması (tarafsız dille)")
    strengths: list[str]
    weaknesses: list[str] = Field(description="Tarafsız, karalayıcı olmayan ifadeler")
    our_difference: str = Field(description="Bizim markamızın buna karşı farkı")
    verified: bool = Field(description="Her zaman false döndür; doğrulamayı insan yapar")


class CompetitorAnalysis(BaseModel):
    competitors: list[Competitor] = Field(description="3-5 rakip")
    market_note: str = Field(description="Pazardaki boşluğa dair kısa genel değerlendirme, rakamsız")


# =========================================================================== Aşama 2


class ChannelHabit(BaseModel):
    channel: str
    habit: str = Field(description="Bu kanalı ne zaman, nasıl, ne için kullanıyor")


class Persona(BaseModel):
    name: str = Field(description="Kurgusal ad (gerçek/ünlü bir kişi değil)")
    age: int
    occupation: str
    location: str
    daily_routine: str = Field(description="Gün içi rutin: sabahtan geceye kısa akış")
    coffee_habit: str
    pain_points: list[str] = Field(description="3-5 acı noktası")
    motivations: list[str] = Field(description="3-4 motivasyon / beklenti")
    channel_habits: list[ChannelHabit]
    quote: str = Field(description="Personanın ağzından tek cümle (kurgusal)")


class PersonaSet(BaseModel):
    personas: list[Persona]


class AdjectiveRule(BaseModel):
    adjective: str
    meaning: str = Field(description="Bu sıfat metinde nasıl görünür")


class WeAreRow(BaseModel):
    we_are: str
    we_are_not: str


class BadExample(BaseModel):
    sentence: str
    why_bad: str


class BrandVoice(BaseModel):
    personality: list[AdjectiveRule] = Field(description="3-4 kişilik sıfatı")
    we_are_table: list[WeAreRow] = Field(description="4-5 satır 'biz şuyuz / şu değiliz'")
    words_to_use: list[str] = Field(description="8-12 kelime/ifade")
    words_to_avoid: list[str] = Field(description="6-10 kelime/ifade")
    address_rule: str = Field(description="Hitap kuralı (sen/siz) ve gerekçesi")
    emoji_rule: str = Field(description="Emoji kullanım kuralı, kanal bazında")
    good_examples: list[str] = Field(description="3-4 iyi örnek cümle")
    bad_examples: list[BadExample] = Field(description="3 kötü örnek cümle ve neden kötü")
    tts_tone: str = Field(description="Seslendirme tonunun kısa Türkçe tarifi (ör. sıcak, sakin, gülümseyen)")
    tts_rate_percent: int = Field(description="edge-tts konuşma hızı ayarı, yüzde; -20 ile +20 arası (0 = normal)")
    tts_pitch_hz: int = Field(description="edge-tts ses perdesi ayarı, Hz; -10 ile +10 arası (0 = normal)")


class StrategyFrame(BaseModel):
    why: str = Field(description="Neden: markanın var olma nedeni")
    who: str = Field(description="Kime: hedef kitle ve persona")
    what: str = Field(description="Ne: ne tür içerik / değer sunuyoruz")
    how: str = Field(description="Nasıl: hangi kanallar, ton ve formatlarla")


class ContentPillar(BaseModel):
    name: str
    purpose: str = Field(description="Bu sütunun iş amacı (farkındalık/etkileşim/dönüşüm bağlamında)")
    description: str
    persona_match: str = Field(description="Personanın hangi ihtiyacına/acı noktasına karşılık gelir")
    example_topics: list[str] = Field(description="3 örnek konu")
    best_channels: list[str]


class ContentStrategy(BaseModel):
    frame: StrategyFrame
    pillars: list[ContentPillar] = Field(description="3-4 içerik sütunu")


# =========================================================================== Aşama 3a — takvim

Deliverable = Literal["blog", "social_post", "image", "video", "voiceover"]
Goal = Literal["farkındalık", "etkileşim", "dönüşüm"]

DELIVERABLE_LABELS: dict[str, str] = {
    "blog": "Blog yazısı", "social_post": "Sosyal gönderi", "image": "Görsel",
    "video": "Kısa video", "voiceover": "Seslendirme",
}
# Teslim edilecek içerik setinin takvimde en az kaç kez yer alması gerektiği (CLAUDE.md §1)
REQUIRED_DELIVERABLES: dict[str, int] = {"blog": 1, "social_post": 3, "image": 3, "video": 1, "voiceover": 1}
STATUS_OPTIONS = ["Planlandı", "Üretiliyor", "Hazır", "Onaylandı", "Yayınlandı"]


class CalendarItemDraft(BaseModel):
    """LLM'in ürettiği satır. id, tarih, gün adı ve durum kodda eklenir (uydurulmasın diye)."""
    day: int = Field(description="1-7 arası gün numarası")
    time_slot: str = Field(description="Önerilen paylaşım saati, ör. '08:30' — persona rutinine göre")
    channel: str = Field(description="Markanın kanallarından biri")
    format: str = Field(description="Ör. 'Instagram carousel', 'Reels (dikey video)', 'SEO blog yazısı'")
    deliverables: list[Deliverable] = Field(
        description="Bu satırın ürettiği teslim çıktıları; ör. görselli gönderi için ['social_post','image'], "
                    "seslendirmeli video için ['video','voiceover']")
    pillar: str = Field(description="İçerik sütununun adı, listedekiyle birebir aynı")
    persona: str = Field(description="Hedef personanın adı, birebir aynı")
    topic: str = Field(description="Konu / başlık")
    goal: Goal
    rationale: str = Field(description="Gerekçe: personanın adını ve sütunun adını anarak neden bu gün/kanal/format")


class CalendarDraft(BaseModel):
    items: list[CalendarItemDraft] = Field(description="7 güne yayılmış 7-10 satır")
    strategy_note: str = Field(description="Haftanın genel kurgusunu açıklayan 2-3 cümle")


# =========================================================================== Aşama 3b — içerik

SOURCE_TAG = "[KAYNAK GEREKLİ]"


class BlogPost(BaseModel):
    title_h1: str = Field(description="H1 başlık; odak anahtar kelimeyi içersin, ~60 karakter")
    meta_description: str = Field(description="Meta açıklama, EN FAZLA 155 karakter, odak anahtar kelimeyi içersin")
    slug: str = Field(description="URL kısaltması, küçük harf, Türkçe karakter yok, tire ile")
    focus_keyword: str
    secondary_keywords: list[str] = Field(description="3-5 ikincil anahtar kelime")
    body_markdown: str = Field(
        description="H1 OLMADAN yazı gövdesi; Markdown '## ' (H2) ve '### ' (H3) başlıklarıyla, 800-1200 kelime")
    cta: str = Field(description="Yazının sonundaki eylem çağrısı")
    flagged_claims: list[str] = Field(
        description=f"Metinde {SOURCE_TAG} ile işaretlediğin iddiaların listesi; yoksa boş liste")


class SocialPost(BaseModel):
    channel: str
    hook: str = Field(description="İlk satır / kanca: kaydırmayı durduracak tek cümle")
    body: str = Field(description="Gönderi metni (kanca dahil değil), kanala uygun uzunlukta")
    hashtags: list[str] = Field(description="'#' ile başlayan 3-8 hashtag; biri marka hashtag'i")
    cta: str
    image_description: str = Field(
        description="Eşlik eden görselin Türkçe tarifi: sahne, nesneler, ışık; yazı/logo/tanınabilir kişi yok")
    alt_text: str = Field(description="Erişilebilirlik için görsel alt metni, Türkçe, ≤125 karakter")


class ImagePrompt(BaseModel):
    prompt_en: str = Field(description="Görsel modeli için İngilizce prompt, 60-120 kelime")
    description_tr: str = Field(description="Promptun Türkçe kısa özeti (dokümantasyon için)")
    palette_hexes: list[str] = Field(description="Promptta kullanılan palet HEX kodları")


# =========================================================================== Aşama 3c — ses + video


class VoiceoverScript(BaseModel):
    text: str = Field(description="Seslendirme metni, 40-50 kelime, yüksek sesle okunduğunda 15-20 sn")
    pronunciation_notes: list[str] = Field(
        description="Yanlış okunabilecek kelimeler ve okunuşları (ör. marka adı); yoksa boş liste")


class VideoScene(BaseModel):
    visual_description: str = Field(description="Sahnede görünecek görselin Türkçe tarifi")
    on_screen_text: str = Field(description="Ekran metni, en fazla 6 kelime")
    duration_s: float = Field(description="Sahne süresi (saniye), 3-5")


class VideoScript(BaseModel):
    scenes: list[VideoScene] = Field(description="4-5 sahne; son sahne marka adı + slogan kapanışı")
    closing_text: str = Field(description="Son sahnede marka adının altında görünecek kısa slogan")


def check_voiceover(x: VoiceoverScript) -> list[str]:
    n = word_count(x.text)
    return [] if 35 <= n <= 55 else [f"Seslendirme {n} kelime; 15-20 sn için hedef 40-50."]


def check_video_script(x: VideoScript) -> list[str]:
    issues = _count("Sahne", x.scenes, 4, 5)
    issues += [f"Sahne {i}: ekran metni {word_count(s.on_screen_text)} kelime (en fazla 6)."
               for i, s in enumerate(x.scenes, 1) if word_count(s.on_screen_text) > 6]
    return issues


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def check_blog(x: BlogPost) -> list[str]:
    issues = []
    n = word_count(x.body_markdown)
    if not 800 <= n <= 1200:
        issues.append(f"Kelime sayısı {n}; hedef 800-1200.")
    if len(x.meta_description) > 155:
        issues.append(f"Meta açıklama {len(x.meta_description)} karakter; en fazla 155.")
    if x.focus_keyword.casefold() not in x.title_h1.casefold():
        issues.append("Odak anahtar kelime H1 başlıkta geçmiyor.")
    if x.focus_keyword.casefold() not in x.meta_description.casefold():
        issues.append("Odak anahtar kelime meta açıklamada geçmiyor.")
    issues += _count("İkincil anahtar kelime", x.secondary_keywords, 3, 5)
    h2 = len(re.findall(r"^## ", x.body_markdown, re.M))
    if h2 < 3:
        issues.append(f"Yalnızca {h2} H2 başlık var; en az 3 olmalı.")
    if re.search(r"^# ", x.body_markdown, re.M):
        issues.append("Gövdede H1 (# ) var; H1 yalnızca başlık alanında olmalı.")
    # Rakam içeren ama işaretlenmemiş cümleler: halüsinasyon riski.
    # Etiket noktadan sonra gelse de ("…%73. [KAYNAK GEREKLİ]") aynı cümleye ait sayılır.
    for sent in re.split(r"(?<=[.!?])\s+(?!\[)", x.body_markdown):
        if re.search(r"%|\b\d{2,}\b", sent) and SOURCE_TAG not in sent:
            issues.append(f"Sayısal ifade kaynak işaretsiz olabilir: “{sent.strip()[:80]}…”")
    return issues


def check_social(x: SocialPost) -> list[str]:
    issues = _count("Hashtag", x.hashtags, 3, 8)
    issues += [f"Hashtag '#' ile başlamıyor: {h}" for h in x.hashtags if not h.startswith("#")]
    if len(x.alt_text) > 125:
        issues.append(f"Alt metin {len(x.alt_text)} karakter; en fazla 125.")
    return issues


# Görsel promptlarında yasak kalıplar (isim bazlı stil taklidi, marka/logo, gerçek kişi)
FORBIDDEN_IMAGE_PATTERNS = [
    r"in the style of", r"style of [A-Z]", r"\binspired by [A-Z]", r"tarzında", r"\blogo\b(?! ?free)",
    r"starbucks", r"kahve dünyası", r"espressolab", r"nescaf", r"celebrity", r"famous",
]


def check_image_prompt(x: ImagePrompt) -> list[str]:
    issues = []
    text = x.prompt_en
    # "no logos" gibi olumsuz ifadeleri ayıklayıp kalanında yasak kalıp ara
    scrubbed = re.sub(r"\b(no|without|avoid)\b[^,.;]*", "", text, flags=re.I)
    for pat in FORBIDDEN_IMAGE_PATTERNS:
        if re.search(pat, scrubbed, re.I):
            issues.append(f"Görsel promptunda yasak kalıp: '{pat}'")
    issues += [f"Geçersiz HEX: {h}" for h in x.palette_hexes if not HEX_RE.match(h)]
    n = word_count(text)
    if not 40 <= n <= 160:
        issues.append(f"Prompt {n} kelime; hedef 60-120.")
    return issues


# =========================================================================== denetimler


def _count(label: str, items: list, lo: int, hi: int) -> list[str]:
    n = len(items)
    return [] if lo <= n <= hi else [f"{label}: {n} adet üretildi, beklenen {lo}-{hi}."]


def check_identity(x: BrandIdentity) -> list[str]:
    issues = _count("Değerler", x.values, 3, 5) + _count("Renk paleti", x.palette, 4, 6)
    issues += [f"Geçersiz HEX kodu: {c.hex} ({c.name})" for c in x.palette if not HEX_RE.match(c.hex)]
    return issues


def check_competitors(x: CompetitorAnalysis) -> list[str]:
    return _count("Rakipler", x.competitors, 3, 5)


def check_personas(x: PersonaSet, expected: int) -> list[str]:
    return _count("Persona", x.personas, expected, expected)


def check_voice(x: BrandVoice) -> list[str]:
    issues = _count("Kişilik sıfatları", x.personality, 3, 4)
    if not -20 <= x.tts_rate_percent <= 20:
        issues.append(f"Seslendirme hızı {x.tts_rate_percent}%; -20 ile +20 arası olmalı.")
    if not -10 <= x.tts_pitch_hz <= 10:
        issues.append(f"Seslendirme perdesi {x.tts_pitch_hz}Hz; -10 ile +10 arası olmalı.")
    return issues


def check_strategy(x: ContentStrategy) -> list[str]:
    return _count("İçerik sütunları", x.pillars, 3, 4)


def check_calendar(items: list[dict], pillar_names: list[str], persona_names: list[str]) -> list[str]:
    """Takvim kısıtları (CLAUDE.md §5): 7 gün dolu, zorunlu formatlar var, her sütun kullanılmış,
    her satırda persona + sütun + gerekçe dolu ve gerekçe persona ile sütuna atıf yapıyor."""
    issues: list[str] = []
    days = {int(i["day"]) for i in items if str(i.get("day", "")).strip()}
    if missing := sorted(set(range(1, 8)) - days):
        issues.append(f"Boş gün var: {', '.join(map(str, missing))}. gün.")

    counts = {k: 0 for k in REQUIRED_DELIVERABLES}
    for i in items:
        for d in i.get("deliverables") or []:
            if d in counts:
                counts[d] += 1
    for k, need in REQUIRED_DELIVERABLES.items():
        if counts[k] < need:
            issues.append(f"Zorunlu format eksik: {DELIVERABLE_LABELS[k]} {counts[k]}/{need}.")

    used = {i.get("pillar") for i in items}
    if unused := [p for p in pillar_names if p not in used]:
        issues.append(f"Hiç kullanılmayan içerik sütunu: {', '.join(unused)}.")

    for n, i in enumerate(items, 1):
        label = f"Satır {n} ({i.get('topic', '')[:30]})"
        for field, name in (("persona", "persona"), ("pillar", "sütun"), ("rationale", "gerekçe")):
            if not str(i.get(field) or "").strip():
                issues.append(f"{label}: {name} boş.")
        if i.get("pillar") and i["pillar"] not in pillar_names:
            issues.append(f"{label}: '{i['pillar']}' tanımlı sütunlardan biri değil.")
        if i.get("persona") and i["persona"] not in persona_names:
            issues.append(f"{label}: '{i['persona']}' tanımlı persona değil.")
        rationale = str(i.get("rationale") or "").casefold()
        if rationale and i.get("persona") and i["persona"].split()[0].casefold() not in rationale:
            issues.append(f"{label}: gerekçe personaya atıf yapmıyor.")
        if rationale and i.get("pillar") and i["pillar"].casefold() not in rationale:
            issues.append(f"{label}: gerekçe sütun adını anmıyor.")
    return issues


# =========================================================================== Aşama 4 — kontrol

Status = Literal["uygun", "riskli", "uygun_degil"]
DECISIONS = ["onaylandı", "düzeltildi", "reddedildi"]


class ReviewField(BaseModel):
    durum: Status
    aciklama: str = Field(description="Kısa gerekçe, somut örnekle")
    oneri: str = Field(description="Durum 'uygun' değilse somut düzeltme önerisi; uygunsa boş string")


class SourceCheck(BaseModel):
    durum: Status
    aciklama: str
    oneri: str
    isaretlenen_iddialar: list[str] = Field(
        description="Doğrulanması gereken her sayısal/olgusal iddia (metindeki haliyle); yoksa boş liste")


class ReviewReport(BaseModel):
    ton_tutarliligi: ReviewField = Field(description="Marka sesi rehberine uyum: hitap, kelime seçimi, emoji")
    anahtar_kelime: ReviewField = Field(description="Hedef anahtar kelime / konu / hashtag uyumu")
    telif_kontrolu: ReviewField = Field(
        description="İsim bazlı stil taklidi, başka marka/logo/slogan, gerçek kişi, uzun alıntı var mı")
    kaynak_dogrulama: SourceCheck = Field(description="Uydurma olabilecek istatistik, tarih, alıntı, olgu")

    def fields(self) -> dict[str, ReviewField | SourceCheck]:
        return {"ton_tutarliligi": self.ton_tutarliligi, "anahtar_kelime": self.anahtar_kelime,
                "telif_kontrolu": self.telif_kontrolu, "kaynak_dogrulama": self.kaynak_dogrulama}

    def risky(self) -> bool:
        return any(f.durum != "uygun" for f in self.fields().values())
