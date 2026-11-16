from datetime import date
from functools import partial

import pandas as pd
import streamlit as st

from contentflow import llm, models, storage, ui
from contentflow.exporters import xlsx
from contentflow.generators import calendar as cal_gen

ui.setup_page("İçerik Takvimi")
st.title("3 · İçerik Takvimi")
if not ui.require(["brand_voice", "personas", "content_strategy"]):
    st.stop()
ui.flash()

calendar = storage.get_current("calendar")
default_start = date.fromisoformat(calendar["start_date"]) if calendar else cal_gen.next_monday()
start = st.date_input("Takvim başlangıç tarihi", default_start, format="DD.MM.YYYY",
                      help="Gün numaraları bu tarihe göre gerçek tarihe çevrilir.")

ui.generate_buttons("calendar", partial(cal_gen.generate_calendar, start), "7 günlük takvim")
if not calendar:
    st.caption("Takvim; persona, içerik sütunları ve marka sesi bağlamıyla üretilir. Zorunlu formatlar: "
               + ", ".join(f"{n} × {models.DELIVERABLE_LABELS[k]}" for k, n in models.REQUIRED_DELIVERABLES.items()))
    st.stop()

ui.version_picker("calendar")
st.markdown(f"**Haftanın kurgusu:** {calendar['strategy_note']}")

# ------------------------------------------------------------------ kısıt denetimi
counts = {k: sum(k in (i.get("deliverables") or []) for i in calendar["items"]) for k in models.REQUIRED_DELIVERABLES}
cols = st.columns(len(counts))
for col, (k, n) in zip(cols, counts.items()):
    need = models.REQUIRED_DELIVERABLES[k]
    col.metric(models.DELIVERABLE_LABELS[k], f"{n} / {need}", delta="tamam" if n >= need else "eksik",
               delta_color="normal" if n >= need else "inverse")

problems = cal_gen.issues(calendar)
if problems:
    with st.expander(f"⚠️ {len(problems)} kısıt sorunu — yeniden üret veya tabloda düzelt", expanded=True):
        for p in problems:
            st.markdown(f"- {p}")
else:
    st.success("Tüm kısıtlar sağlanıyor: 7 gün dolu, zorunlu formatlar var, her sütun kullanılmış, "
               "her gerekçe persona ve sütuna atıf yapıyor.")

# ------------------------------------------------------------------ düzenlenebilir tablo
st.subheader("Takvim")
st.caption("Hücrelere tıklayıp düzenleyebilir, satır ekleyip silebilirsin. Tarih ve gün adı, gün numarasından "
           "otomatik hesaplanır. Değişiklikler **Kaydet** ile yeni versiyon olur.")
seed = storage.load_brand_seed()
order = ["id", "day", "weekday", "date", "time_slot", "channel", "format", "deliverables", "pillar",
         "persona", "topic", "goal", "rationale", "status"]
df = pd.DataFrame(calendar["items"])[order]
edited = st.data_editor(
    df,
    key=f"cal_editor_v{storage.get_section('calendar')['current']}",
    num_rows="dynamic", hide_index=True, width="stretch",
    column_config={
        "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "day": st.column_config.NumberColumn("Gün no", min_value=1, max_value=7, step=1, required=True, width="small"),
        "weekday": st.column_config.TextColumn("Gün", disabled=True),
        "date": st.column_config.TextColumn("Tarih", disabled=True),
        "time_slot": st.column_config.TextColumn("Saat", width="small"),
        "channel": st.column_config.SelectboxColumn("Kanal", options=seed["channels"], required=True),
        "format": st.column_config.TextColumn("Format"),
        "deliverables": st.column_config.MultiselectColumn(
            "Teslim çıktıları", options=list(models.DELIVERABLE_LABELS),
            format_func=lambda k: models.DELIVERABLE_LABELS.get(k, k)),
        "pillar": st.column_config.SelectboxColumn("İçerik sütunu", options=cal_gen.pillar_names(), required=True),
        "persona": st.column_config.SelectboxColumn("Persona", options=cal_gen.persona_names(), required=True),
        "topic": st.column_config.TextColumn("Konu / Başlık", width="large"),
        "goal": st.column_config.SelectboxColumn("Amaç", options=["farkındalık", "etkileşim", "dönüşüm"], required=True),
        "rationale": st.column_config.TextColumn("Gerekçe", width="large"),
        "status": st.column_config.SelectboxColumn("Durum", options=models.STATUS_OPTIONS, required=True),
    },
)

c1, c2 = st.columns([1, 3])
if c1.button("💾 Kaydet", type="primary"):
    rows = [{k: (None if (not isinstance(v, list) and pd.isna(v)) else v) for k, v in r.items()}
            for r in edited.to_dict("records")]
    rows = [r for r in rows if r.get("day")]  # gün numarası olmayan boş satırları at
    new_cal = {**calendar, "start_date": start.isoformat(), "items": cal_gen.normalize_items(rows, start)}
    if new_cal == calendar:
        st.info("Değişiklik yok.")
    else:
        ver = storage.get_current_version("calendar")
        log_id = llm.log_human_edit(task="calendar", stage="aşama3", output=new_cal, parent_log_id=ver["log_id"])
        v = storage.save_version("calendar", new_cal, source="human", log_id=log_id)
        st.session_state.setdefault("_flash", []).append(("success", f"Takvim v{v} olarak kaydedildi."))
        st.rerun()
if start.isoformat() != calendar["start_date"]:
    c2.info("Başlangıç tarihi değişti; tarihleri güncellemek için **Kaydet**'e bas.")

# ------------------------------------------------------------------ dışa aktarım
st.subheader("Dışa aktar")
if st.button("📊 icerik_takvimi.xlsx oluştur"):
    path = xlsx.export_calendar(calendar, storage.get_current("brand_identity"),
                                storage.get_current("content_strategy"), storage.get_current("personas"),
                                storage.subdir("exports") / "icerik_takvimi.xlsx")
    st.session_state["xlsx_bytes"] = path.read_bytes()
    st.success(f"Kaydedildi: {path}")
if data := st.session_state.get("xlsx_bytes"):
    st.download_button("⬇️ İndir", data, file_name="icerik_takvimi.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
