<!-- formül: CO-STAR — Marka Sesi Rehberi sonraki TÜM metin üretimlerine system prompt olarak eklenecek; bu yüzden bağlam (kimlik + persona), amaç ve kitleyi ayrı ayrı vermek, rehberin persona diline gerçekten oturmasını sağlar. -->
# Context
Kurgusal kahve markası için tek sayfalık bir Marka Sesi Rehberi yazıyoruz. Bu rehber, bundan sonra üretilecek her blog, sosyal medya gönderisi, video senaryosu ve seslendirme metnine otomatik olarak eklenecek.

Marka bilgisi:
$seed

Marka kimliği:
$identity

Hedef persona:
$personas

# Objective
Şunları içeren uygulanabilir bir rehber üret:
- 3-4 kişilik sıfatı ve her birinin metinde nasıl görüneceği
- 4-5 satırlık "biz şuyuz / şu değiliz" tablosu
- Kullanılacak 8-12 kelime/ifade ve kaçınılacak 6-10 kelime/ifade (abartılı pazarlama klişeleri, kitleyi küçümseyen dil, sağlık iddiaları gibi)
- Hitap kuralı: kitleye "$address_form" diye hitap edilecek; kuralı ve gerekçesini yaz
- Kanal bazında emoji kuralı (Instagram, TikTok/Reels, Blog, LinkedIn)
- 3-4 iyi örnek cümle ve 3 kötü örnek cümle (neden kötü olduğuyla)
- Seslendirme ayarları (Türkçe TTS motoru yalnızca hız ve perde ayarı kabul eder):
  - `tts_tone`: tonun kısa Türkçe tarifi (ör. "sıcak, sakin, hafif gülümseyen")
  - `tts_rate_percent`: konuşma hızı, -20 ile +20 arası tam sayı (sakin marka → hafif negatif, enerjik → hafif pozitif)
  - `tts_pitch_hz`: ses perdesi, -10 ile +10 arası tam sayı (çoğu marka için 0'a yakın)

# Style
Kısa, maddeli, örnekli. Her kural bir yazarın hemen uygulayabileceği kadar somut olsun.

# Tone
Rehberin kendisi de markanın sesini yansıtsın: sıcak, net, hafif esprili ama özenli.

# Audience
Markanın içerik yazarları ve yapay zeka içerik üretim sistemi; nihai okur ise yukarıdaki persona.

# Response
JSON şemasına uy. Tüm metinler Türkçe olsun.
