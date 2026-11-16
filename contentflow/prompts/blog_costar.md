<!-- formül: CO-STAR — Uzun, SEO odaklı bir metin; bağlam (marka + takvim satırı), amaç (SEO + dönüşüm), stil/ton ve kitlenin ayrı başlıklarla verilmesi tutarlı ve yapılandırılmış bir yazı üretir. -->
# Context
Kurgusal kahve markası için web sitesi blogu yazıyoruz. Marka sesi rehberi system prompt'ta.

Marka bilgisi (marka hakkında YALNIZCA bunlar doğru kabul edilir):
$seed

Marka kimliği:
$identity

Takvim satırı (bu yazının stratejik dayanağı):
- Konu / başlık fikri: $topic
- İçerik sütunu: $pillar
- Amaç: $goal
- Gerekçe: $rationale

Sütun detayı:
$pillar_detail

# Objective
800-1200 kelimelik, SEO uyumlu bir blog yazısı üret:
- Konuya uygun, gerçekçi arama niyetine karşılık gelen bir **odak anahtar kelime** ve 3-5 **ikincil anahtar kelime** seç.
- **H1** (title_h1): odak anahtar kelimeyi içersin, ~60 karakter.
- **Meta açıklama**: odak anahtar kelimeyi içersin, EN FAZLA 155 karakter (boşluklar dahil). Sınırı aşma.
- **Gövde** (body_markdown): H1 YAZMA. En az 3 adet `## ` (H2) ve gerektiğinde `### ` (H3) alt başlık. Kısa paragraflar, gerekirse madde listeleri. Odak anahtar kelime ilk paragrafta ve en az bir H2'de doğal biçimde geçsin; anahtar kelime doldurma yapma.
- Yazı personanın sorununa pratik bir çözüm sunsun; markadan doğal biçimde, satış baskısı kurmadan bahset.
- **CTA**: amaçla uyumlu (kafeye uğrama / online çekirdek / topluluk etkinliği).

**Halüsinasyon kuralları (çok önemli):**
1. İstatistik, yüzde, araştırma sonucu, tarih veya alıntı UYDURMA. Sayısal bir iddia gerçekten gerekiyorsa cümlenin sonuna $source_tag yaz ve bu cümleyi `flagged_claims` listesine de ekle.
2. Gerçek kişilerden alıntı yapma; uzman adı uydurma.
3. Marka hakkında yukarıdaki bilgilerde olmayan somut olgu ekleme (açılış yılı, adres, fiyat, ödül, çalışan adı vb.).
4. Kahvenin sağlığa etkisi hakkında tıbbi iddiada bulunma.
5. Genel kahve bilgisi (demleme yöntemleri, öğütme, su sıcaklığı aralığı gibi yaygın bilinen pratikler) kullanılabilir; emin değilsen genel ifade kullan.

# Style
Bilgilendirici ama sohbet havasında bir blog yazısı; somut ipuçları, günlük hayattan sahneler (ders arası, deadline gecesi). Klişe giriş cümlelerinden kaçın.

# Tone
Marka sesi rehberine birebir uy (hitap: $address_form).

# Audience
$persona

# Response
JSON şemasına uy. Tüm metinler Türkçe. `slug` Türkçe karakter içermesin.
