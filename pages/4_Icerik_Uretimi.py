from functools import partial

import streamlit as st

from contentflow import config, models, storage, ui
from contentflow.generators import content, media

ui.setup_page("İçerik Üretimi")
st.title("4 · İçerik Üretimi")
if not ui.require(["calendar"]):
    st.stop()
ui.flash()


def item_label(item: dict) -> str:
    return f"{item['id']} · {item['weekday']} · {item['channel']} — {item['topic']}"


def item_caption(item: dict) -> None:
    st.caption(f"📅 {item['weekday']} {item['date']} {item.get('time_slot', '')} · {item['format']} · "
               f"Sütun: **{item['pillar']}** · Persona: **{item['persona']}** · Amaç: {item['goal']}")


def show_issues(issues: list[str]) -> None:
    if issues:
        with st.expander(f"⚠️ {len(issues)} denetim uyarısı", expanded=False):
            for i in issues:
                st.markdown(f"- {i}")
    else:
        st.success("Otomatik denetimden geçti.", icon="✅")


tab_blog, tab_social, tab_img, tab_av = st.tabs(
    ["📝 Blog (CO-STAR)", "📱 Sosyal gönderiler (RTF)", "🖼️ Görseller", "🎬 Seslendirme ve video"])

# ------------------------------------------------------------------ blog
with tab_blog:
    rows = content.items_with("blog")
    if not rows:
        st.warning("Takvimde blog satırı yok. İçerik Takvimi sayfasında bir satıra 'Blog yazısı' ekle.")
    else:
        existing = storage.get_current_version("blog")
        ids = [r["id"] for r in rows]
        default = ids.index(existing["calendar_item_id"]) if existing and existing["calendar_item_id"] in ids else 0
        item = st.selectbox("Takvim satırı", rows, index=default, format_func=item_label, key="blog_row")
        item_caption(item)
        ui.generate_buttons("blog", partial(content.generate_blog, item["id"]), "Blog yazısı")
        blog = storage.get_current("blog")
        if blog:
            ui.version_picker("blog")
            post = models.BlogPost.model_validate(blog)
            show_issues(models.check_blog(post))
            c1, c2, c3 = st.columns(3)
            c1.metric("Kelime", models.word_count(post.body_markdown), help="Hedef 800-1200")
            c2.metric("Meta açıklama", f"{len(post.meta_description)} / 155 kr.")
            c3.metric(models.SOURCE_TAG, post.body_markdown.count(models.SOURCE_TAG),
                      help="Kaynak gerektiren iddia sayısı; Kontrol aşamasında doğrulanacak")
            st.markdown(f"**Odak anahtar kelime:** `{post.focus_keyword}` · **İkincil:** "
                        + ", ".join(f"`{k}`" for k in post.secondary_keywords))
            st.markdown(f"**Meta açıklama:** {post.meta_description}  \n**Slug:** `/{post.slug}`")
            with st.container(border=True):
                st.markdown(f"# {post.title_h1}")
                st.markdown(post.body_markdown.replace(models.SOURCE_TAG, f"**:red[{models.SOURCE_TAG}]**"))
                st.markdown(f"**👉 {post.cta}**")
            if post.flagged_claims:
                st.warning("İşaretlenen iddialar (kaynak bulunmalı veya çıkarılmalı):\n"
                           + "\n".join(f"- {c}" for c in post.flagged_claims))
            ui.yaml_editor("blog", models.BlogPost, task="blog", stage="aşama3")

# ------------------------------------------------------------------ sosyal
with tab_social:
    rows = content.items_with("social_post")
    done = sum(storage.get_current(f"social_post:{r['id']}") is not None for r in rows)
    st.markdown(f"Takvimdeki sosyal gönderi satırları: **{len(rows)}** · Üretilen: **{done}** (en az 3 gerekli)")
    st.caption("Her gönderinin promptu açıkça # Role / # Task / # Format bölümleriyle kurulur.")
    for item in rows:
        key = f"social_post:{item['id']}"
        with st.container(border=True):
            st.markdown(f"#### {item_label(item)}")
            item_caption(item)
            ui.generate_buttons(key, partial(content.generate_social, item["id"]), "Gönderi")
            post_d = storage.get_current(key)
            if post_d:
                ui.version_picker(key)
                post = models.SocialPost.model_validate(post_d)
                show_issues(models.check_social(post))
                st.markdown(f"**{post.hook}**\n\n{post.body}\n\n👉 {post.cta}\n\n" + " ".join(post.hashtags))
                st.caption(f"🖼️ Görsel tarifi: {post.image_description}  \n♿ Alt metin: {post.alt_text}")
                ui.yaml_editor(key, models.SocialPost, task="social_post", stage="aşama3")

# ------------------------------------------------------------------ görseller
with tab_img:
    rows = content.items_with("image")
    done = sum(storage.get_current(f"image:{r['id']}") is not None for r in rows)
    st.markdown(f"Görsel gerektiren satırlar: **{len(rows)}** · Yüklenen: **{done}** (en az 3 gerekli)")
    st.info(
        "Görseller ücretsiz araçlarla üretilir: **1)** Uygulama, görsel stil dili + palet HEX'leri + sahne "
        "tarifinden İngilizce bir prompt yazar. **2)** Promptu sağ üstteki kopyala simgesiyle kopyala, "
        "ChatGPT / Gemini / Canva'da görseli üret. **3)** Kullandığın aracı seçip görseli yükle; araç bilgisi "
        "prompt kütüphanesine ve AI kullanım raporuna yazılır. Sosyal gönderisi olan satırlarda gönderinin "
        "görsel tarifi kullanıldığı için önce gönderileri üretmen önerilir.")
    for item in rows:
        pkey, ikey = f"image_prompt:{item['id']}", f"image:{item['id']}"
        with st.container(border=True):
            st.markdown(f"#### {item_label(item)}")
            item_caption(item)
            left, right = st.columns([3, 2])
            with left:
                st.markdown("**1) Görsel promptu**")
                ui.generate_buttons(pkey, partial(content.generate_image_prompt, item["id"]), "Görsel promptu")
                ip = storage.get_current(pkey)
                if ip:
                    ui.version_picker(pkey)
                    show_issues(models.check_image_prompt(models.ImagePrompt.model_validate(ip)))
                    sizes = list(content.ASPECT_TEXT)
                    size = st.radio("Oran", sizes, index=sizes.index(content.default_size(item)), horizontal=True,
                                    key=f"size_{item['id']}",
                                    format_func=lambda s: "Kare 1:1 (feed)" if s == "1024x1024" else "Dikey 2:3 (story/video)")
                    st.markdown("**Kopyalanacak prompt** (sağ üstteki simgeyle kopyala):")
                    st.code(content.final_image_prompt(ip["prompt_en"], size), language=None, wrap_lines=True)
                    st.caption(f"Türkçe özet: {ip['description_tr']}")
                    ui.yaml_editor(pkey, models.ImagePrompt, task="image_prompt", stage="aşama3")
            with right:
                st.markdown("**2) Görseli yükle**")
                if not ip:
                    st.caption("Önce görsel promptunu üret.")
                else:
                    with st.form(f"upload_{item['id']}", clear_on_submit=True):
                        tool = st.selectbox("Hangi araçla ürettin?", config.IMAGE_TOOLS, key=f"tool_{item['id']}")
                        up = st.file_uploader("Görsel dosyası", type=content.ALLOWED_IMAGE_TYPES,
                                              key=f"file_{item['id']}")
                        if st.form_submit_button("📤 Yükle ve kaydet", type="primary"):
                            if up is None:
                                st.warning("Önce bir dosya seç.")
                            elif (v := ui.run_safely(content.save_uploaded_image, item["id"], up.getvalue(),
                                                     up.name, tool, size)) is not None:
                                st.session_state.setdefault("_flash", []).append(
                                    ("success", f"{item['id']} görseli v{v} olarak kaydedildi ({tool})."))
                                st.rerun()
                    img = storage.get_current(ikey)
                    if img:
                        ui.version_picker(ikey)
                        path = content.image_path(img)
                        if path.exists():
                            st.image(str(path), caption=f"{img['tool']} · {img['size']} · {img['original_name']}")
                        else:
                            st.error(f"Görsel dosyası bulunamadı: {path}")
                        if img["prompt"] != content.final_image_prompt(ip["prompt_en"], img["size"]):
                            st.caption("ℹ️ Prompt bu görselden sonra değişti; istersen yeni promptla üretip tekrar yükle.")

# ------------------------------------------------------------------ ses / video
with tab_av:
    vitem = media.video_item()
    if not vitem:
        st.warning("Takvimde video/seslendirme satırı yok. İçerik Takvimi sayfasında ekle.")
        st.stop()
    st.markdown(f"#### {item_label(vitem)}")
    item_caption(vitem)

    st.subheader("1) Seslendirme metni")
    ui.generate_buttons("voiceover_script", media.generate_voiceover_script, "Seslendirme metni")
    vs = storage.get_current("voiceover_script")
    if vs:
        ui.version_picker("voiceover_script")
        show_issues(models.check_voiceover(models.VoiceoverScript.model_validate(vs)))
        st.markdown(f"> {vs['text']}")
        st.caption(f"{models.word_count(vs['text'])} kelime · tahmini "
                   f"{models.word_count(vs['text']) / config.TTS_WORDS_PER_SECOND:.0f} sn")
        if vs["pronunciation_notes"]:
            st.caption("Telaffuz notları: " + "; ".join(vs["pronunciation_notes"]))
        ui.yaml_editor("voiceover_script", models.VoiceoverScript, task="voiceover_script", stage="aşama3")

        st.subheader("2) Ses (edge-tts)")
        d_rate, d_pitch = media.voice_settings()
        c1, c2, c3 = st.columns(3)
        voices = list(config.TTS_VOICES)
        voice = c1.selectbox("Ses", voices, index=voices.index(config.TTS_VOICE) if config.TTS_VOICE in voices else 0,
                             format_func=lambda v: config.TTS_VOICES[v])
        rate = c2.slider("Hız (%)", -30, 30, int(d_rate.rstrip("%")), help="Marka sesi rehberinden gelen varsayılan")
        pitch = c3.slider("Perde (Hz)", -15, 15, int(d_pitch.rstrip("Hz")))
        ui.generate_buttons("voiceover", partial(media.synthesize_voiceover, voice, f"{rate:+d}%", f"{pitch:+d}Hz"),
                            "Ses")
        vo = storage.get_current("voiceover")
        if vo:
            ui.version_picker("voiceover")
            st.audio(str(storage.workspace() / vo["path"]))
            ok = 15 <= vo["duration_s"] <= 20
            (st.success if ok else st.warning)(
                f"Süre {vo['duration_s']} sn ({config.TTS_VOICES.get(vo['voice'], vo['voice'])}, hız {vo['rate']}, "
                f"perde {vo['pitch']})" + ("" if ok else " — hedef 15-20 sn"))
            if vo["text"] != vs["text"]:
                st.caption("ℹ️ Metin bu sesten sonra değişti; yeni ses için **Yeniden üret**.")

    st.subheader("3) Video senaryosu")
    if not vs:
        st.caption("Önce seslendirme metnini üret.")
    else:
        ui.generate_buttons("video_script", media.generate_video_script, "Video senaryosu")
        script = storage.get_current("video_script")
        if script:
            ui.version_picker("video_script")
            show_issues(models.check_video_script(models.VideoScript.model_validate(script)))
            ui.yaml_editor("video_script", models.VideoScript, task="video_script", stage="aşama3")

            st.subheader("4) Montaj")
            imgs = media.uploaded_images()
            vo = storage.get_current("voiceover")
            if not imgs:
                st.warning("Video için en az bir yüklenmiş görsel gerekli (Görseller sekmesi).")
            elif not vo:
                st.warning("Önce sesi üret (adım 2).")
            else:
                keys = [k for k, _ in imgs]
                chosen = []
                for n, sc in enumerate(script["scenes"]):
                    c1, c2 = st.columns([3, 1])
                    last = n == len(script["scenes"]) - 1
                    c1.markdown(f"**Sahne {n + 1}** ({sc['duration_s']} sn) — "
                                + (f"_kapanış: {storage.load_brand_seed()['name']} / {script['closing_text']}_" if last
                                   else f"“{sc['on_screen_text']}”")
                                + f"  \n<small>{sc['visual_description']}</small>", unsafe_allow_html=True)
                    chosen.append(c2.selectbox("Görsel", keys, index=n % len(keys), key=f"scene_img_{n}",
                                               format_func=lambda k: k.split(":", 1)[1], label_visibility="collapsed"))
                if st.button("🎬 Videoyu oluştur", type="primary"):
                    with st.spinner("Video montajlanıyor (yaklaşık 1 dk)..."):
                        data = ui.run_safely(media.render_video, chosen)
                    if data:
                        st.session_state.setdefault("_flash", []).append(("success", f"Video hazır: {data['duration']} sn."))
                        st.rerun()
            vid = storage.get_current("video")
            if vid:
                ui.version_picker("video")
                c1, c2 = st.columns([1, 2])
                c1.video(str(storage.workspace() / vid["path"]))
                ok = 15 <= vid["duration"] <= 20.5
                (c2.success if ok else c2.warning)(f"Süre: {vid['duration']} sn · 1080×1920 · 30 fps"
                                                   + ("" if ok else " — hedef 15-20 sn; seslendirmeyi ayarla"))
