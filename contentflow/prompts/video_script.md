<!-- formül: CO-STAR — Video senaryosu görsel, metin ve sesin eşzamanlı planlanmasını ister; bağlam (seslendirme + mevcut görseller), amaç ve kitle ayrı verilince sahneler seslendirmeyle uyumlu olur. -->
# Context
Kurgusal kahve markası için 15-20 saniyelik dikey (9:16) tanıtım videosu planlıyoruz. Video, hazır görsellerin yavaş yakınlaştırma ve geçişlerle montajından oluşacak; üzerine seslendirme ve kısa ekran metinleri gelecek. Marka sesi rehberi system prompt'ta.

Seslendirme metni (video bu sesle eşzamanlı akacak):
"$voiceover"

Elimizdeki görseller (sahnelerde bunları yeniden kullanacağız):
$images

Marka adı: $brand_name — vaat: $one_liner

# Objective
4-5 sahnelik bir senaryo üret:
- Her sahnede: görselin tarifi (mümkünse elimizdeki görsellerden birine karşılık gelsin), en fazla 6 kelimelik ekran metni, 3-5 sn süre.
- Ekran metinleri seslendirmeyi tekrar etmesin, tamamlasın.
- Son sahne kapanış: ekran metni marka adı, `closing_text` kısa slogan (logo yok, yalnızca metin).
- Süreler toplamı yaklaşık 15-20 sn.

# Style
Ritmi hızlı, sakin ama canlı; her sahne tek bir fikir.

# Tone
Marka sesi rehberine uygun.

# Audience
$persona

# Response
JSON şemasına uy. Tüm metinler Türkçe.
