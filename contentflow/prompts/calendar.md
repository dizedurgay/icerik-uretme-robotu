<!-- formül: CO-STAR — Takvim stratejik bir planlama görevi; persona rutini, sütunlar ve zorunlu formatlar ayrı bağlam başlıklarıyla verilince her satırın gerekçesi bunlara dayanır (Stratejik Netlik kriteri). -->
# Context
Kurgusal kahve markası için 7 günlük içerik takvimi hazırlıyoruz. Marka sesi rehberi system prompt'ta.

Marka bilgisi:
$seed

Hedef persona:
$personas

İçerik sütunları:
$pillars

Takvim günleri:
$days

# Objective
7 güne yayılmış 7-10 satırlık bir takvim üret. Kısıtlar (hepsi zorunlu):
1. Her gün en az bir satır olsun.
2. Teslim çıktıları (`deliverables`) toplamında en az: 1 × blog, 3 × social_post, 3 × image, 1 × video, 1 × voiceover bulunsun.
   - Görselli sosyal gönderi satırı: ['social_post', 'image']
   - Seslendirmeli kısa video satırı: ['video', 'voiceover']
   - Blog satırı: ['blog'] (istersen kapak görseli için 'image' ekleyebilirsin)
3. Her içerik sütunu en az bir kez kullanılsın. `pillar` alanına sütun adını AYNEN yaz: $pillar_names
4. `persona` alanına persona adını AYNEN yaz: $persona_names
5. Kanallar yalnızca şunlardan olsun: $channels
6. Amaç (`goal`) dağılımı dengeli olsun: haftanın başı farkındalık ağırlıklı, ortası etkileşim, sonu dönüşüm (kafe ziyareti / online çekirdek) ağırlıklı.
7. Paylaşım saatini (`time_slot`) personanın gün içi rutinine göre seç.
8. `rationale` (gerekçe): 1-2 cümle; personanın ADINI ve sütunun ADINI açıkça anarak bu gün, saat, kanal ve formatın neden seçildiğini açıkla. Personanın rutinine veya acı noktasına atıf yap.
9. Konu başlıklarında istatistik, uydurma tarih ya da gerçek kişi/marka adı kullanma.

# Style
Uygulanabilir ve somut; konu başlıkları doğrudan içerik başlığı olarak kullanılabilecek netlikte.

# Tone
Marka sesi rehberine uygun.

# Audience
Takvimi uygulayacak içerik ekibi ve değerlendirme jürisi (stratejik gerekçeyi okuyacak).

# Response
JSON şemasına uy. `items` satırlarını gün ve saate göre sıralı ver. `strategy_note` alanında haftanın genel kurgusunu 2-3 cümleyle anlat. Tüm metinler Türkçe.
