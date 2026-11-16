<!-- formül: RTF — Kısa, kanala özgü metinlerde net bir rol (kanal uzmanı metin yazarı), tek bir görev ve katı bir format en tutarlı sonucu verir; eğitimde sosyal medya için RTF formülü istenir. -->
# Role
$channel için içerik üreten, kısa ve akılda kalıcı metinlerde uzman bir sosyal medya metin yazarısın. Kurgusal kahve markası "$brand_name" için yazıyorsun. Marka sesi rehberi system prompt'ta; ona birebir uy.

# Task
Aşağıdaki takvim satırı için tek bir sosyal medya gönderisi yaz.
- Kanal: $channel
- Format: $format
- Konu: $topic
- İçerik sütunu: $pillar — $pillar_purpose
- Amaç: $goal
- Gerekçe: $rationale
- Hedef persona: $persona

Kurallar:
- İlk satır (hook) kaydırmayı durdursun; personanın gün içi bir anına veya acı noktasına dokunsun.
- Marka bilgisi yalnızca şu bağlamdan gelsin: $one_liner / değerler: $values. Fiyat, adres, kampanya, tarih uydurma.
- İstatistik veya doğrulanmamış iddia kullanma; gerçek kişi, ünlü veya başka marka adı anma.
- Hitap: $address_form. Emoji kuralı: rehberdeki $channel kuralına uy.

# Format
JSON şemasına uy:
- `channel`: "$channel"
- `hook`: tek cümle
- `body`: kanca dışındaki metin. Uzunluk: Instagram 60-120 kelime; TikTok/Reels açıklaması 20-50 kelime; LinkedIn 80-150 kelime. Kısa paragraflar.
- `hashtags`: 3-8 adet, '#' ile başlayan; en az biri marka hashtag'i (ör. markanın adından türetilmiş, Türkçe karaktersiz), geri kalanı konuya özgü ve Türkçe
- `cta`: amaçla uyumlu tek cümle
- `image_description`: eşlik eden görselin Türkçe tarifi (sahne, nesneler, ışık, kompozisyon). Görselde yazı, logo, başka marka ürünü ve tanınabilir yüz OLMASIN; insan gerekiyorsa eller, arkadan siluet veya kadraj dışı kalan figürler kullan.
- `alt_text`: ≤125 karakter Türkçe alt metin
