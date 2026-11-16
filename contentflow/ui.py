"""Tüm sayfalarda ortak Streamlit parçaları: sayfa ayarı, kenar çubuğu, ön koşul kontrolü."""
from __future__ import annotations

import streamlit as st

from contentflow import config, llm, storage


def setup_page(title: str, icon: str = "☕") -> None:
    st.set_page_config(page_title=f"{title} · {config.APP_NAME}", page_icon=icon, layout="wide")
    storage.ensure_workspace()
    render_sidebar()


def render_sidebar() -> None:
    with st.sidebar:
        seed = storage.load_brand_seed()
        st.markdown(f"### ☕ {seed.get('name', config.APP_NAME)}")

        # Günlük istek sayacı (Gemini ücretsiz katman)
        used = llm.requests_today()
        limit = config.GEMINI_DAILY_REQUEST_LIMIT
        ratio = min(used / limit, 1.0) if limit > 0 else 1.0
        st.caption("Bugünkü Gemini istekleri")
        st.progress(ratio, text=f"{used} / {limit}")
        st.caption("Önbellekten gelen yanıtlar sayılmaz. Gerçek limit AI Studio'da görünür; "
                   "değeri .env'deki GEMINI_DAILY_REQUEST_LIMIT ile ayarla.")
        if ratio >= 1.0:
            st.warning("Günlük tahmini limite ulaşıldı; istekler 429 ile reddedilebilir.")

        # İlerleme
        st.caption("İlerleme")
        for s in storage.stage_progress():
            mark = "✅" if s["done"] else ("🟡" if s["partial"] else "⬜")
            st.markdown(f"{mark} {s['title']}")

        # Mod / ayar bilgisi
        st.divider()
        st.caption(f"Metin: `{config.TEXT_MODEL}` · Kontrol: `{config.REVIEW_MODEL}`  \n"
                   f"Ses: `{config.TTS_ENGINE}` · Görsel: harici araç + yükleme")
        if not config.api_key_present():
            st.error("GEMINI_API_KEY yok. aistudio.google.com'dan ücretsiz anahtar alıp `.env` dosyasına yaz.")


def require(keys: list[str]) -> bool:
    """Gerekli önceki aşama çıktıları yoksa uyarı gösterir ve False döner."""
    missing = storage.first_missing_stage(keys)
    if missing:
        st.info(f"Bu sayfa için önce **{missing}** aşamasını tamamlamalısın. Soldaki menüden o sayfaya git.")
        return False
    return True


def run_safely(fn, *args, **kwargs):
    """Üretim çağrısını sarar; LLMError'ı Türkçe hata kutusuyla gösterir. Hata olursa None döner."""
    try:
        return fn(*args, **kwargs)
    except llm.QuotaExhausted as exc:
        st.error(f"⏳ {exc}")
    except llm.LLMError as exc:
        st.error(f"⚠️ {exc}")
    return None


SOURCE_LABELS = {"ai": "🤖 YZ", "human": "✍️ elle", "fix": "🛠️ düzeltme"}


def flash() -> None:
    """Önceki çalıştırmadan kalan mesajları gösterir (st.rerun sonrası kaybolmasınlar diye)."""
    for kind, msg in st.session_state.pop("_flash", []):
        getattr(st, kind)(msg)


def _push_flash(kind: str, msg: str) -> None:
    st.session_state.setdefault("_flash", []).append((kind, msg))


def generate_buttons(key: str, generate_fn, label: str) -> None:
    """'Üret' (önbellekli) ve 'Yeniden üret' (önbelleği atlar) düğmeleri."""
    exists = storage.get_current(key) is not None
    cols = st.columns([1, 1, 4])
    clicked_gen = cols[0].button(f"✨ {label} üret", key=f"gen_{key}", disabled=exists,
                                 type="primary", width="stretch")
    clicked_regen = cols[1].button("🔄 Yeniden üret", key=f"regen_{key}", disabled=not exists,
                                   width="stretch",
                                   help="Önbelleği atlayıp yeni bir versiyon üretir; eski versiyon silinmez.")
    if not (clicked_gen or clicked_regen):
        return
    with st.spinner(f"{label} üretiliyor..."):
        out = run_safely(generate_fn, use_cache=not clicked_regen)
    if out is None:
        return
    result, issues = out
    info = "önbellekten geldi (kota harcanmadı)" if result.cached else "1 Gemini isteği kullanıldı"
    _push_flash("success", f"{label} hazır — {info}.")
    for issue in issues:
        _push_flash("warning", f"⚠️ {issue} Yeniden üretebilir veya elle düzeltebilirsin.")
    st.rerun()


def version_picker(key: str) -> None:
    section = storage.get_section(key)
    if not section or len(section["versions"]) < 2:
        return
    labels = [
        f"v{v['v']} · {SOURCE_LABELS.get(v['source'], v['source'])} · {v['created_at'][:16].replace('T', ' ')}"
        for v in section["versions"]
    ]
    choice = st.selectbox("Versiyon", range(len(labels)), index=section["current"] - 1,
                          format_func=lambda i: labels[i], key=f"ver_{key}",
                          help="Eski versiyonlar silinmez; istediğine geri dönebilirsin.")
    if choice + 1 != section["current"]:
        storage.set_current(key, choice + 1)
        st.rerun()


def to_yaml(data) -> str:
    """Çok satırlı metinleri '|' blok biçiminde yazar (blog gövdesi okunur kalsın)."""
    import yaml

    class _Dumper(yaml.SafeDumper):
        pass

    def _str(dumper, value):
        style = "|" if "\n" in value else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)

    _Dumper.add_representer(str, _str)
    return yaml.dump(data, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=100)


def yaml_editor(key: str, schema: type, task: str, stage: str) -> None:
    """Güncel içeriği YAML olarak düzenletir; şemaya göre doğrulayıp yeni versiyon kaydeder."""
    import yaml
    from pydantic import ValidationError

    ver = storage.get_current_version(key)
    if not ver:
        return
    with st.expander("✏️ Elle düzenle"):
        text = st.text_area(
            "İçerik (YAML)", value=to_yaml(ver["content"]),
            height=400, key=f"edit_{key}_v{ver['v']}",
        )
        if st.button("💾 Düzenlemeyi kaydet", key=f"save_{key}"):
            try:
                data = schema.model_validate(yaml.safe_load(text)).model_dump(mode="json")
            except yaml.YAMLError as exc:
                st.error(f"YAML biçim hatası: {exc}")
                return
            except ValidationError as exc:
                fields = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:5])
                st.error(f"İçerik şemaya uymuyor — {fields}")
                return
            if data == ver["content"]:
                st.info("Değişiklik yok.")
                return
            log_id = llm.log_human_edit(task=task, stage=stage, output=data, parent_log_id=ver["log_id"])
            v = storage.save_version(key, data, source="human", log_id=log_id)
            _push_flash("success", f"Elle düzenleme v{v} olarak kaydedildi.")
            st.rerun()


def color_swatches(palette: list[dict]) -> None:
    cols = st.columns(len(palette))
    for col, c in zip(cols, palette):
        col.markdown(
            f"<div style='background:{c['hex']};height:72px;border-radius:10px;"
            f"border:1px solid rgba(128,128,128,.35)'></div>",
            unsafe_allow_html=True,
        )
        col.markdown(f"**{c['name']}**  \n`{c['hex']}`  \n<small>{c['usage']}</small>", unsafe_allow_html=True)


def placeholder(milestone: int, what: str) -> None:
    st.info(f"🚧 Bu sayfa Milestone {milestone}'de doldurulacak: {what}")
