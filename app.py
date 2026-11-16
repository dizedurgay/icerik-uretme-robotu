"""İçerik Üretme Robotu giriş sayfası: genel bakış ve ilerleme.

Çalıştırma:  streamlit run app.py
"""
import streamlit as st

from contentflow import config, llm, storage, ui

ui.setup_page("Genel Bakış")

seed = storage.load_brand_seed()
st.title(f"🤖 {config.APP_NAME}")
st.caption("Yapay zeka destekli marka içerik üretim sistemi")

st.markdown(f"**Marka:** {seed['name']} — _{seed['one_liner']}_  \n**Sektör:** {seed['sector']}")

st.warning(
    f"**Sorumlu kullanım notu:** “{seed['name']}” kurgusal bir çalışma adıdır. Teslimden önce bu adın "
    "gerçek bir tescilli markayla çakışıp çakışmadığını kendin kontrol et (ör. TÜRKPATENT marka araştırması)."
)

col1, col2, col3 = st.columns(3)
col1.metric("Bugünkü Gemini isteği", llm.requests_today(),
            help=f"Bilgi amaçlı üst sınır: {config.GEMINI_DAILY_REQUEST_LIMIT} (.env)")
col2.metric("Toplam log kaydı", len(storage.read_jsonl(storage.prompt_log_path())),
            help="Gemini çağrıları, seslendirmeler, görsel yüklemeleri ve elle düzenlemeler")
col3.metric("Tamamlanan aşama", f"{sum(s['done'] for s in storage.stage_progress())} / {len(storage.STAGES)}")

st.subheader("Aşamalar")
for s in storage.stage_progress():
    mark = "✅" if s["done"] else ("🟡" if s["partial"] else "⬜")
    st.page_link(s["page"], label=f"{mark} {s['title']}")

st.divider()
if not st.toggle("🎤 Sunum Görünümü", help="Tüm içeriği tek sayfada, sade biçimde gösterir (ekran görüntüsü için)."):
    st.stop()

import pandas as pd  # noqa: E402

from contentflow import models, render  # noqa: E402
from contentflow.generators import content as cgen  # noqa: E402

cur = storage.get_current
ident, voice, personas, strat = cur("brand_identity"), cur("brand_voice"), cur("personas"), cur("content_strategy")
st.markdown(f"# {seed['name']}\n### _{seed['one_liner']}_")
if ident:
    st.markdown(f"**Misyon:** {ident['mission']}")
    ui.color_swatches(ident["palette"])
    st.markdown(" · ".join(f"**{v['name']}**" for v in ident["values"]))
if personas and voice:
    c1, c2 = st.columns(2)
    p = personas["personas"][0]
    c1.markdown(f"### 👤 {p['name']}, {p['age']}\n{p['occupation']}\n\n> {p['quote']}\n\n"
                + "\n".join(f"- {x}" for x in p["pain_points"]))
    c2.markdown("### 🗣️ Marka sesi\n" + " · ".join(f"**{a['adjective']}**" for a in voice["personality"]) + "\n\n"
                + "\n".join(f"- ✅ {r['we_are']} — ❌ {r['we_are_not']}" for r in voice["we_are_table"]))
if strat:
    st.markdown("### 🧭 İçerik sütunları")
    for col, pl in zip(st.columns(len(strat["pillars"])), strat["pillars"]):
        col.markdown(f"**{pl['name']}**  \n<small>{pl['purpose']}</small>", unsafe_allow_html=True)
if cal := cur("calendar"):
    st.markdown("### 📅 7 günlük takvim")
    df = pd.DataFrame(cal["items"])[["weekday", "channel", "format", "pillar", "topic", "goal", "rationale"]]
    df.columns = ["Gün", "Kanal", "Format", "Sütun", "Konu", "Amaç", "Gerekçe"]
    st.dataframe(df, hide_index=True, width="stretch")
if blog := cur("blog"):
    st.markdown(f"### 📝 Blog: {blog['title_h1']}")
    st.caption(f"Meta: {blog['meta_description']} · Odak: {blog['focus_keyword']} · "
               f"{models.word_count(blog['body_markdown'])} kelime")
posts = storage.keys_with_prefix("social_post:")
if posts:
    st.markdown("### 📱 Sosyal gönderiler")
    for col, k in zip(st.columns(len(posts[:3])), posts[:3]):
        post, cid = cur(k), k.split(":", 1)[1]
        img = cur(f"image:{cid}")
        if img and cgen.image_path(img).exists():
            col.image(str(cgen.image_path(img)))
        col.markdown(f"**{post['channel']}** · **{post['hook']}**\n\n{post['body']}\n\n" + " ".join(post["hashtags"]))
if (vo := cur("voiceover")) or cur("video"):
    st.markdown("### 🎬 Seslendirme ve video")
    c1, c2 = st.columns([1, 2])
    if vid := cur("video"):
        c1.video(str(storage.workspace() / vid["path"]))
    if vo:
        c2.audio(str(storage.workspace() / vo["path"]))
        c2.markdown(f"> {vo['text']}")
