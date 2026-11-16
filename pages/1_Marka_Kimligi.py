import streamlit as st

from contentflow import llm, models, storage, ui
from contentflow.generators import strategy

ui.setup_page("Marka Kimliği")
st.title("1 · Marka Kimliği")
ui.flash()

# ------------------------------------------------------------------ tohum
seed = storage.load_brand_seed()
with st.expander("🌱 Marka tohumu (başlangıç bilgisi)", expanded=storage.get_current("brand_identity") is None):
    with st.form("seed_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Marka adı", seed["name"])
        sector = c2.text_input("Sektör", seed["sector"])
        one_liner = st.text_input("Tek cümlelik vaat", seed["one_liner"])
        location = st.text_input("Konum", seed["location"])
        audience = st.text_input("Hedef kitle ipucu", seed["target_audience_hint"])
        values = st.text_input("Değer ipuçları (virgülle)", ", ".join(seed["values_hint"]))
        channels = st.text_input("Kanallar (virgülle)", ", ".join(seed["channels"]))
        c3, c4 = st.columns(2)
        persona_count = c3.number_input("Persona sayısı", 1, 2, int(seed.get("persona_count", 1)))
        address = c4.selectbox("Hitap", ["sen", "siz"], index=0 if seed.get("address_form", "sen") == "sen" else 1)
        if st.form_submit_button("Tohumu kaydet"):
            new_seed = {
                **seed, "name": name.strip(), "sector": sector.strip(), "one_liner": one_liner.strip(),
                "location": location.strip(), "target_audience_hint": audience.strip(),
                "values_hint": [v.strip() for v in values.split(",") if v.strip()],
                "channels": [c.strip() for c in channels.split(",") if c.strip()],
                "persona_count": int(persona_count), "address_form": address,
            }
            if new_seed != seed:
                log_id = llm.log_human_edit(task="brand_seed", stage="aşama1", output=new_seed)
                storage.save_version("brand_seed", new_seed, source="human", log_id=log_id)
                st.success("Tohum kaydedildi. Değişikliğin yansıması için kimliği yeniden üret.")
                st.rerun()
    st.caption("⚖️ Hatırlatma: marka adının gerçek bir tescilli markayla çakışıp çakışmadığını kendin kontrol et.")

# ------------------------------------------------------------------ kimlik
st.header("Marka kimliği")
ui.generate_buttons("brand_identity", strategy.generate_identity, "Marka kimliği")
identity = storage.get_current("brand_identity")
if identity:
    ui.version_picker("brand_identity")
    st.subheader("Hikâye")
    st.write(identity["story"])
    st.markdown(f"**Misyon:** {identity['mission']}")

    st.subheader("Değerler")
    for v in identity["values"]:
        st.markdown(f"- **{v['name']}** — {v['description']}")

    st.subheader("Renk paleti")
    ui.color_swatches(identity["palette"])
    for issue in models.check_identity(models.BrandIdentity.model_validate(identity)):
        st.warning(issue)

    t = identity["typography"]
    st.subheader("Tipografi")
    st.markdown(f"**Başlık:** {t['heading_font']} · **Gövde:** {t['body_font']} · _{t['license']}_  \n{t['rationale']}")

    vs = identity["visual_style"]
    st.subheader("Görsel stil dili")
    st.caption("Bu metin tüm görsel promptlarına otomatik eklenir.")
    st.markdown(
        f"- **Stil:** {vs['style']}\n- **Işık:** {vs['lighting']}\n- **Kompozisyon:** {vs['composition']}\n"
        f"- **Renk kullanımı:** {vs['color_usage']}\n- **Yasaklar:** " + "; ".join(vs["forbidden"])
    )
    ui.yaml_editor("brand_identity", models.BrandIdentity, task="brand_identity", stage="aşama1")

# ------------------------------------------------------------------ rakipler
st.header("Rakip analizi")
if not identity:
    st.info("Rakip analizi için önce marka kimliğini üret.")
    st.stop()

st.warning(
    "⚠️ **Manuel doğrula:** Bu analiz yapay zeka tarafından üretildi ve **doğrulanmamıştır**. "
    "Rakipler hakkındaki her bilgiyi kendin kontrol et; doğruladıklarını aşağıda işaretle. "
    "Bu durum kontrol listesine yazılır."
)
ui.generate_buttons("competitors", strategy.generate_competitors, "Rakip analizi")
comp = storage.get_current("competitors")
if comp:
    ui.version_picker("competitors")
    with st.form("verify_form"):
        flags = []
        for i, c in enumerate(comp["competitors"]):
            badge = "✅ doğrulandı" if c["verified"] else "❓ doğrulanmadı"
            st.markdown(f"#### {c['name']}  <small>({c['type']}) · {badge}</small>", unsafe_allow_html=True)
            st.markdown(
                f"**Konumlandırma:** {c['positioning']}  \n"
                f"**Güçlü:** {'; '.join(c['strengths'])}  \n"
                f"**Boşluk:** {'; '.join(c['weaknesses'])}  \n"
                f"**Bizim farkımız:** {c['our_difference']}"
            )
            flags.append(st.checkbox("Bu rakip bilgisini manuel doğruladım", value=c["verified"], key=f"verif_{i}"))
        st.markdown(f"**Pazar notu:** {comp['market_note']}")
        if st.form_submit_button("Doğrulama durumunu kaydet"):
            if flags != [c["verified"] for c in comp["competitors"]]:
                new = {**comp, "competitors": [{**c, "verified": f} for c, f in zip(comp["competitors"], flags)]}
                log_id = llm.log_human_edit(task="competitor_verification", stage="aşama1", output=new,
                                            parent_log_id=storage.get_current_version("competitors")["log_id"])
                storage.save_version("competitors", new, source="human", log_id=log_id, note="manuel doğrulama")
                st.rerun()
    ui.yaml_editor("competitors", models.CompetitorAnalysis, task="competitor_analysis", stage="aşama1")
