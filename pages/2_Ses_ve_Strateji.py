import streamlit as st

from contentflow import models, render, storage, ui
from contentflow.generators import strategy

ui.setup_page("Ses ve Strateji")
st.title("2 · Ses ve Strateji")
if not ui.require(["brand_identity"]):
    st.stop()
ui.flash()

tab_persona, tab_voice, tab_strategy = st.tabs(["👤 Persona", "🗣️ Marka Sesi Rehberi", "🧭 Strateji ve Sütunlar"])

# ------------------------------------------------------------------ persona
with tab_persona:
    ui.generate_buttons("personas", strategy.generate_personas, "Persona")
    personas = storage.get_current("personas")
    if personas:
        ui.version_picker("personas")
        for p in personas["personas"]:
            st.subheader(f"{p['name']}, {p['age']}")
            st.caption(f"{p['occupation']} · {p['location']}")
            st.markdown(f"> {p['quote']}")
            c1, c2 = st.columns(2)
            c1.markdown("**Gün içi rutin**\n\n" + p["daily_routine"])
            c1.markdown("**Kahve alışkanlığı**\n\n" + p["coffee_habit"])
            c2.markdown("**Acı noktaları**\n" + "\n".join(f"- {x}" for x in p["pain_points"]))
            c2.markdown("**Motivasyonlar**\n" + "\n".join(f"- {x}" for x in p["motivations"]))
            st.markdown("**Kanal alışkanlıkları**\n" +
                        "\n".join(f"- **{h['channel']}:** {h['habit']}" for h in p["channel_habits"]))
        ui.yaml_editor("personas", models.PersonaSet, task="personas", stage="aşama2")

# ------------------------------------------------------------------ ses
with tab_voice:
    st.info("Bu rehber bundan sonraki **her** metin üretiminde system prompt'a otomatik eklenir "
            "(Marka Tutarlılığı). Prompt logundaki `brand_voice_injected` alanından doğrulanabilir.")
    if not storage.get_current("personas"):
        st.warning("Rehberin persona diline oturması için önce Persona sekmesinde persona üret.")
    else:
        ui.generate_buttons("brand_voice", strategy.generate_voice, "Marka sesi rehberi")
        voice = storage.get_current("brand_voice")
        if voice:
            ui.version_picker("brand_voice")
            st.markdown(render.brand_voice_markdown(voice))
            st.markdown(f"**Seslendirme tonu:** {voice['tts_tone']} · hız `{voice['tts_rate_percent']:+d}%` · "
                        f"perde `{voice['tts_pitch_hz']:+d}Hz` (edge-tts)")
            ui.yaml_editor("brand_voice", models.BrandVoice, task="brand_voice", stage="aşama2")

# ------------------------------------------------------------------ strateji
with tab_strategy:
    if not storage.get_current("brand_voice"):
        st.warning("Sütunlar marka sesiyle üretilir; önce Marka Sesi Rehberi sekmesini tamamla.")
    else:
        ui.generate_buttons("content_strategy", strategy.generate_strategy, "Strateji ve sütunlar")
        strat = storage.get_current("content_strategy")
        if strat:
            ui.version_picker("content_strategy")
            f = strat["frame"]
            st.subheader("Neden – Kime – Ne – Nasıl")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Neden?**\n\n{f['why']}")
            c2.markdown(f"**Kime?**\n\n{f['who']}")
            c1.markdown(f"**Ne?**\n\n{f['what']}")
            c2.markdown(f"**Nasıl?**\n\n{f['how']}")

            st.subheader("İçerik sütunları")
            for issue in models.check_strategy(models.ContentStrategy.model_validate(strat)):
                st.warning(issue)
            cols = st.columns(len(strat["pillars"]))
            for col, p in zip(cols, strat["pillars"]):
                with col.container(border=True):
                    st.markdown(f"**{p['name']}**")
                    st.caption(p["purpose"])
                    st.write(p["description"])
                    st.markdown(f"🎯 _{p['persona_match']}_")
                    st.markdown("**Örnek konular**\n" + "\n".join(f"- {t}" for t in p["example_topics"]))
                    st.markdown("**Kanallar:** " + ", ".join(p["best_channels"]))
            ui.yaml_editor("content_strategy", models.ContentStrategy, task="content_pillars", stage="aşama2")
