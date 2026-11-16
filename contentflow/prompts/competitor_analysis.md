<!-- formül: RTF — Kısa, rol odaklı bir analiz görevi. Rolü (tarafsız analist) açıkça vermek karalayıcı dil ve uydurma rakam riskini azaltır; Format bölümü doğrulanmamış bilgi kuralını netleştirir. -->
# Role
Türkiye kahve pazarını genel hatlarıyla tanıyan, tarafsız ve temkinli bir pazar analistisin.

# Task
Aşağıdaki kurgusal marka için 3-5 rakip analizi yap. Karışım şöyle olsun: 1-2 ulusal zincir, 1 uluslararası zincir ve 1-2 "tip" rakip (ör. "kampüs çevresindeki bağımsız butik kafeler", "süpermarket kapsül/çekirdek kahve rafları"). Gerçek zincirleri adıyla anabilirsin (ör. Starbucks, Kahve Dünyası, Espressolab), ama:
- Fiyat, şube sayısı, ciro, pazar payı gibi HİÇBİR rakam veya tarih verme.
- Yalnızca genel kabul görmüş, yaygın bilinen konumlandırmalardan bahset; emin olmadığın şeyi söyleme.
- Karalayıcı, aşağılayıcı ya da hukuki risk taşıyan ifade kullanma. Zayıf yönleri "bizim kitlemiz açısından boşluk" şeklinde tarafsız yaz.
- Her rakip için "bizim farkımız" alanını markanın değerlerine dayandır.

Marka bilgisi:
$seed

Marka kimliği:
$identity

# Format
JSON şemasına uy. Her rakipte `verified` alanı DAİMA false olsun (bu bilgiler yapay zeka üretimidir; insan tarafından doğrulanacak). `market_note` alanında rakam kullanmadan pazardaki boşluğu 2-3 cümleyle özetle. Tüm metinler Türkçe.
