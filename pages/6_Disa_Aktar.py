import streamlit as st

from contentflow import review, storage, ui
from contentflow.exporters import docs

ui.setup_page("Dışa Aktar")
st.title("6 · Dışa Aktar")
ui.flash()

prog = {s["title"]: s for s in storage.stage_progress()}
missing = [t for t, s in prog.items() if not s["done"] and not t.startswith("6")]
if missing:
    st.warning("Eksik aşamalar var; dışa aktarım yine çalışır ama dosyalar eksik olur: " + ", ".join(missing))
rs = review.summary()
if rs["decided"] < rs["total"]:
    st.info(f"{rs['total'] - rs['decided']} içeriğin kontrol kararı eksik; kontrol listesinde 'karar yok' görünecek.")

if st.button("📦 Tüm dosyaları oluştur", type="primary"):
    with st.spinner("Dokümanlar hazırlanıyor..."):
        res = ui.run_safely(docs.export_all)
    if res:
        st.session_state.setdefault("_flash", []).append(("success", f"{len(res['files'])} dosya oluşturuldu."))
        st.rerun()

exp = storage.get_current("exports")
if exp:
    folder = storage.subdir("exports")
    st.success(f"Son dışa aktarım: {exp['at'][:16].replace('T', ' ')} · Klasör: `{folder}`")
    zpath = folder / exp["zip"]
    if zpath.exists():
        st.download_button("⬇️ icerik_seti.zip indir", zpath.read_bytes(), file_name="icerik_seti.zip",
                           mime="application/zip", type="primary")
    st.markdown("**Dosyalar**")
    for rel in exp["files"]:
        st.markdown(f"- `{rel}`")
    with st.expander("Önizleme: AI kullanım raporu"):
        p = folder / "ai_kullanim_raporu.md"
        st.markdown(p.read_text(encoding="utf-8") if p.exists() else "-")
    with st.expander("Önizleme: Kontrol listesi"):
        p = folder / "kontrol_listesi.md"
        st.markdown(p.read_text(encoding="utf-8") if p.exists() else "-")
