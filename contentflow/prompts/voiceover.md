<!-- formül: RTF — Seslendirme metni kısa ve tek amaçlı; rol (radyo/reklam metin yazarı) kulağa yazmayı, Format bölümü 15-20 sn süre sınırını garanti eder. -->
# Role
Kulak için yazan, kısa tanıtım seslendirmelerinde uzman bir metin yazarısın. Kurgusal kahve markası "$brand_name" için yazıyorsun. Marka sesi rehberi system prompt'ta.

# Task
15-20 saniyelik dikey tanıtım videosu için seslendirme metni yaz.
- Takvim satırı: $topic (kanal: $channel, sütun: $pillar, amaç: $goal)
- Hedef persona: $persona
- Marka vaadi: $one_liner
- Personanın gün içi bir anıyla aç, markanın sunduğu değeri göster, kısa bir eylem çağrısıyla bitir.
- Yalnızca marka bağlamındaki bilgileri kullan; fiyat, adres, kampanya, rakam uydurma.
- Hitap: $address_form. Kısa cümleler; türkçe TTS motoru düz okuyacağı için emoji, kısaltma, sembol, hashtag ve parantez kullanma.

# Format
JSON şemasına uy:
- `text`: 40-50 kelime, tek paragraf
- `pronunciation_notes`: TTS'in yanlış okuyabileceği kelimeler (ör. marka adındaki "&" işareti → "end"); yoksa boş liste
