from functools import partial

import streamlit as st

from contentflow import config, models, review, storage, ui
from contentflow.generators import content as cgen

ui.setup_page("Kontrol")
st.title("5 · Kontrol")
if not ui.require(["blog", "social_post:"]):
    st.stop()
ui.flash()

ICON = {"uygun": "🟢", "riskli": "🟠", "uygun_degil": "🔴"}
LABEL = {"ton_tutarliligi": "Ton tutarlılığı", "anahtar_kelime": "Anahtar kelime",
         "telif_kontrolu": "Telif / etik", "kaynak_dogrulama": "Kaynak doğrulama"}

s = review.summary()
c1, c2, c3 = st.columns(3)
c1.metric("İçerik", s["total"])
c2.metric("Kontrol edildi", f"{s['reviewed']} / {s['total']}")
c3.metric("Karar verildi", f"{s['decided']} / {s['total']}")
st.caption(f"Kontrol katmanı ikinci bir LLM geçişidir (`{config.REVIEW_MODEL}`); marka sesi rehberini ölçüt alır. "
           "Son karar her zaman senindir.")

comp = storage.get_current("competitors")
if comp and not all(c["verified"] for c in comp["competitors"]):
    st.warning("Rakip analizinde manuel doğrulanmamış bilgiler var (Marka Kimliği sayfası). "
               "Bu durum kontrol listesine yazılacak.")

for item in review.review_items():
    rep = storage.get_current(f"review:{item.key}")
    dec = storage.get_current(f"decision:{item.key}")
    cur_v = storage.get_current_version(item.key)["v"]
    head = ("✅ " + dec["karar"]) if dec else ("🔎 kontrol edildi" if rep else "⬜ bekliyor")
    with st.expander(f"{item.label} — {head}", expanded=dec is None):
        if item.is_image:
            img = storage.get_current(f"image:{item.calendar_item_id}")
            if img and cgen.image_path(img).exists():
                st.image(str(cgen.image_path(img)), width=220, caption=f"{img['tool']} ile üretildi")
            else:
                st.caption("Bu görsel henüz yüklenmedi.")
        st.markdown(f"Güncel içerik: **v{cur_v}**")
        ui.generate_buttons(f"review:{item.key}", partial(review.run_review, item), "Kontrol")
        if rep:
            if rep["reviewed_version"] != cur_v:
                st.info(f"Bu rapor v{rep['reviewed_version']} içindir; güncel v{cur_v} için **Yeniden üret** ile tekrar kontrol et.")
            report = models.ReviewReport.model_validate({k: v for k, v in rep.items() if k != "reviewed_version"})
            for name, f in report.fields().items():
                text = f"{ICON[f.durum]} **{LABEL[name]}: {f.durum}** — {f.aciklama}"
                if f.oneri:
                    text += f"  \n💡 _Öneri:_ {f.oneri}"
                if name == "kaynak_dogrulama" and f.isaretlenen_iddialar:
                    text += "  \n🔎 İşaretlenen iddialar: " + "; ".join(f"“{c}”" for c in f.isaretlenen_iddialar)
                if f.durum == "uygun":
                    st.markdown(text)
                else:
                    st.error(text) if f.durum == "uygun_degil" else st.warning(text)
            if report.risky():
                label = "🛠️ Öneriye göre düzelt" + (" (yeni görsel promptu)" if item.is_image else "")
                if st.button(label, key=f"fix_{item.key}", type="primary"):
                    with st.spinner("Düzeltiliyor..."):
                        v = ui.run_safely(review.apply_fix, item)
                    if v:
                        msg = f"Düzeltilmiş sürüm v{v} olarak kaydedildi (eski sürüm korunuyor). Tekrar kontrol et."
                        if item.is_image:
                            msg += " Yeni promptla görseli yeniden üretip İçerik Üretimi sayfasından yükle."
                        st.session_state.setdefault("_flash", []).append(("success", msg))
                        st.rerun()

        st.markdown("**Karar**")
        with st.form(f"decision_{item.key}"):
            checks = {}
            if item.is_image:
                st.caption("Görseli kendin incele ve işaretle (yalnızca insan kontrol edebilir):")
                prev = (dec or {}).get("manual_checks", {})
                for k, q in review.IMAGE_MANUAL_CHECKS.items():
                    checks[k] = st.checkbox(q, value=prev.get(k, False), key=f"chk_{item.key}_{k}")
            default = models.DECISIONS.index(dec["karar"]) if dec else (
                1 if storage.get_current_version(item.key)["source"] == "fix" else 0)
            karar = st.radio("Karar", models.DECISIONS, index=default, horizontal=True, key=f"karar_{item.key}")
            note = st.text_input("Not", value=(dec or {}).get("not", ""), key=f"note_{item.key}")
            if st.form_submit_button("Kararı kaydet"):
                if item.is_image and any(checks.values()) and karar == "onaylandı":
                    st.error("İşaretli bir görsel riski varken 'onaylandı' seçilemez. Görseli yeniden üretip yükle "
                             "veya 'reddedildi' seç.")
                else:
                    review.save_decision(item, karar, note, checks)
                    st.rerun()
