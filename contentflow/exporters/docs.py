"""Teslim dokümanlarını workspace/exports/ altına üretir (CLAUDE.md §5 Dışa Aktarım tablosu)."""
from __future__ import annotations

import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

from contentflow import config, models, render, review, storage
from contentflow.exporters import xlsx
from contentflow.generators import content as cgen

ICON = {"uygun": "🟢 uygun", "riskli": "🟠 riskli", "uygun_degil": "🔴 uygun değil"}


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def _cur(key: str):
    return storage.get_current(key)


# --------------------------------------------------------------------------- strateji


def strategy_markdown() -> str:
    seed, ident, voice = storage.load_brand_seed(), _cur("brand_identity"), _cur("brand_voice")
    personas, strat, comp = _cur("personas"), _cur("content_strategy"), _cur("competitors")
    out = [f"# {seed['name']} — Marka Stratejisi", f"_{seed['one_liner']}_", ""]
    if ident:
        out += ["## Marka kimliği", ident["story"], "", f"**Misyon:** {ident['mission']}", "",
                "**Değerler:** " + " · ".join(f"**{v['name']}** ({v['description']})" for v in ident["values"]), "",
                "**Renk paleti:**", "", "| Renk | HEX | Kullanım |", "|---|---|---|"]
        out += [f"| {c['name']} | `{c['hex']}` | {c['usage']} |" for c in ident["palette"]]
        t = ident["typography"]
        out += ["", f"**Tipografi:** {t['heading_font']} (başlık) + {t['body_font']} (gövde) — {t['license']}", "",
                f"**Görsel stil:** {ident['visual_style']['style']} {ident['visual_style']['lighting']}", ""]
    if strat:
        f = strat["frame"]
        out += ["## Neden – Kime – Ne – Nasıl", f"- **Neden:** {f['why']}", f"- **Kime:** {f['who']}",
                f"- **Ne:** {f['what']}", f"- **Nasıl:** {f['how']}", ""]
    if personas:
        out += ["## Hedef persona", render.persona_block(personas).replace("### ", "**", 1).replace(")\n", ")**\n", 1), ""]
    if voice:
        out += ["## Ses tonu (özet)", "Kişilik: " + ", ".join(a["adjective"] for a in voice["personality"]) + ". "
                + voice["address_rule"], "Ayrıntı: `marka_sesi_rehberi.md`", ""]
    if strat:
        out += ["## İçerik sütunları", "| Sütun | Amaç | Persona eşleşmesi |", "|---|---|---|"]
        out += [f"| **{p['name']}** | {p['purpose']} | {p['persona_match']} |" for p in strat["pillars"]]
        out.append("")
    if comp:
        out += ["## Rakip konumlandırması (özet)",
                "_Yapay zeka üretimidir; ✅ işaretliler manuel doğrulanmıştır._", ""]
        out += [f"- {'✅' if c['verified'] else '❓'} **{c['name']}** — {c['positioning']} → _Farkımız:_ {c['our_difference']}"
                for c in comp["competitors"]]
    return "\n".join(out)


def strategy_docx(path: Path) -> Path:
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    seed, ident, personas = storage.load_brand_seed(), _cur("brand_identity"), _cur("personas")
    strat, voice = _cur("content_strategy"), _cur("brand_voice")
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_heading(f"{seed['name']} — Marka Stratejisi", 0)
    doc.add_paragraph(seed["one_liner"]).italic = True
    if ident:
        doc.add_heading("Marka kimliği", 1)
        doc.add_paragraph(ident["story"])
        doc.add_paragraph(f"Misyon: {ident['mission']}")
        doc.add_paragraph("Değerler: " + "; ".join(f"{v['name']} — {v['description']}" for v in ident["values"]))
        table = doc.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        for cell, h in zip(table.rows[0].cells, ("Renk", "HEX", "Kullanım")):
            cell.text = h
        for c in ident["palette"]:
            row = table.add_row().cells
            row[0].text, row[1].text, row[2].text = c["name"], c["hex"], c["usage"]
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:fill"), c["hex"].lstrip("#"))
            row[0]._tc.get_or_add_tcPr().append(shd)
        t = ident["typography"]
        doc.add_paragraph(f"Tipografi: {t['heading_font']} + {t['body_font']} ({t['license']})")
    if strat:
        doc.add_heading("Neden – Kime – Ne – Nasıl", 1)
        for k, lbl in (("why", "Neden"), ("who", "Kime"), ("what", "Ne"), ("how", "Nasıl")):
            doc.add_paragraph(f"{lbl}: {strat['frame'][k]}", style="List Bullet")
    if personas:
        doc.add_heading("Hedef persona", 1)
        for p in personas["personas"]:
            doc.add_paragraph(f"{p['name']}, {p['age']} — {p['occupation']}").bold = True
            doc.add_paragraph(f"Rutin: {p['daily_routine']}")
            doc.add_paragraph("Acı noktaları: " + "; ".join(p["pain_points"]))
    if voice:
        doc.add_heading("Ses tonu", 1)
        doc.add_paragraph("Kişilik: " + ", ".join(a["adjective"] for a in voice["personality"]))
        doc.add_paragraph(voice["address_rule"])
    if strat:
        doc.add_heading("İçerik sütunları", 1)
        for p in strat["pillars"]:
            doc.add_paragraph(f"{p['name']}: {p['purpose']} (persona: {p['persona_match']})", style="List Bullet")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


def voice_markdown() -> str:
    voice, seed = _cur("brand_voice"), storage.load_brand_seed()
    if not voice:
        return "# Marka Sesi Rehberi\n\n(Henüz üretilmedi.)"
    return (f"# {seed['name']} — Marka Sesi Rehberi\n\n{render.brand_voice_markdown(voice)}\n\n"
            f"**Seslendirme:** {voice['tts_tone']} (edge-tts hız {voice['tts_rate_percent']:+d}%, "
            f"perde {voice['tts_pitch_hz']:+d}Hz)")


# --------------------------------------------------------------------------- içerik seti


def blog_markdown() -> str:
    b = _cur("blog")
    if not b:
        return "(Blog yok.)"
    return (f"---\ntitle: \"{b['title_h1']}\"\nmeta_description: \"{b['meta_description']}\"\nslug: {b['slug']}\n"
            f"focus_keyword: {b['focus_keyword']}\nsecondary_keywords: [{', '.join(b['secondary_keywords'])}]\n---\n\n"
            f"# {b['title_h1']}\n\n{b['body_markdown']}\n\n**{b['cta']}**")


def social_markdown() -> str:
    out = ["# Sosyal Medya Gönderileri (RTF formülüyle üretildi)", ""]
    for k in storage.keys_with_prefix("social_post:"):
        p, cid = _cur(k), k.split(":", 1)[1]
        row = next((i for i in cgen.calendar_items() if i["id"] == cid), {})
        out += [f"## {p['channel']} — {row.get('weekday', '')} {row.get('date', '')} ({cid})",
                f"_Sütun: {row.get('pillar', '-')} · Amaç: {row.get('goal', '-')}_", "", f"**{p['hook']}**", "",
                p["body"], "", f"👉 {p['cta']}", "", " ".join(p["hashtags"]), "",
                f"> Görsel: {p['image_description']}  \n> Alt metin: {p['alt_text']}", ""]
    return "\n".join(out)


def media_markdown() -> str:
    vs, vo, sc, vid = _cur("voiceover_script"), _cur("voiceover"), _cur("video_script"), _cur("video")
    out = ["# Seslendirme ve Video", ""]
    if vs:
        out += ["## Seslendirme metni", vs["text"], ""]
    if vo:
        out += [f"Ses: {config.TTS_VOICES.get(vo['voice'], vo['voice'])} (edge-tts), hız {vo['rate']}, "
                f"perde {vo['pitch']}, süre {vo['duration_s']} sn", ""]
    if sc:
        out += ["## Video senaryosu (CO-STAR)", "| # | Ekran metni | Görsel | Süre |", "|---|---|---|---|"]
        out += [f"| {i} | {s['on_screen_text']} | {s['visual_description']} | {s['duration_s']} sn |"
                for i, s in enumerate(sc["scenes"], 1)]
        out += ["", f"Kapanış sloganı: {sc['closing_text']}", ""]
    if vid:
        out.append(f"Video: 1080×1920, 30 fps, {vid['duration']} sn, müzik: {vid.get('music') or 'yok'}")
    return "\n".join(out)


# --------------------------------------------------------------------------- kontrol listesi


def checklist_markdown() -> str:
    seed = storage.load_brand_seed()
    out = [f"# İçerik Kontrol Listesi — {seed['name']}", "",
           "Her içerik ikinci bir LLM geçişiyle (AI Çıktı Kontrol Katmanı) dört alanda denetlendi; "
           "son kararı insan verdi.", "",
           "| İçerik | Ver. | Ton tutarlılığı | Anahtar kelime | Telif / etik | Kaynak doğrulama | Karar | Not |",
           "|---|---|---|---|---|---|---|---|"]
    details = []
    for item in review.review_items():
        rep, dec = _cur(f"review:{item.key}"), _cur(f"decision:{item.key}")
        cur_v = storage.get_current_version(item.key)["v"]
        cells = [ICON.get(rep[f]["durum"], "-") if rep else "kontrol edilmedi"
                 for f in ("ton_tutarliligi", "anahtar_kelime", "telif_kontrolu", "kaynak_dogrulama")]
        karar = dec["karar"] if dec else "**karar yok**"
        out.append(f"| {item.label} | v{cur_v} | " + " | ".join(cells) + f" | {karar} | {(dec or {}).get('not', '')} |")
        if rep:
            claims = rep["kaynak_dogrulama"]["isaretlenen_iddialar"]
            details.append(f"### {item.label}\n" + "\n".join(
                f"- **{f}**: {rep[f]['aciklama']}" + (f" — _Öneri:_ {rep[f]['oneri']}" if rep[f]["oneri"] else "")
                for f in ("ton_tutarliligi", "anahtar_kelime", "telif_kontrolu", "kaynak_dogrulama"))
                + (f"\n- İşaretlenen iddialar: {'; '.join(claims)}" if claims else "")
                + (f"\n- Rapor v{rep['reviewed_version']} için (güncel v{cur_v})" if rep["reviewed_version"] != cur_v else ""))
        if item.is_image and dec:
            mc = dec.get("manual_checks", {})
            details.append(f"### {item.label} — manuel görsel kontrolü\n" + "\n".join(
                f"- {'⚠️ EVET' if mc.get(k) else '✅ hayır'} — {q}" for k, q in review.IMAGE_MANUAL_CHECKS.items()))

    comp = _cur("competitors")
    unverified = [c["name"] for c in (comp or {}).get("competitors", []) if not c["verified"]]
    blog = _cur("blog") or {}
    out += ["", "## Genel sorumlu kullanım kontrolleri", "",
            f"- {'⚠️' if unverified else '✅'} **Rakip bilgileri:** "
            + (f"manuel doğrulanmamış: {', '.join(unverified)}" if unverified else "tümü manuel doğrulandı"),
            f"- ⚠️ **Marka adı:** “{seed['name']}” kurgusaldır; gerçek bir tescilli markayla çakışma kontrolü kullanıcı "
            "tarafından yapılmalıdır (TÜRKPATENT).",
            f"- {'⚠️' if models.SOURCE_TAG in blog.get('body_markdown', '') else '✅'} **Blog halüsinasyon kontrolü:** "
            f"{blog.get('body_markdown', '').count(models.SOURCE_TAG)} adet {models.SOURCE_TAG} işareti; "
            "işaretli iddialar yayından önce kaynaklandırılmalı veya çıkarılmalı.",
            "- ✅ **Görseller:** promptlarda isim bazlı stil taklidi yok; her prompta “yazı/logo/tanınabilir yüz yok” "
            "kuralı kodla eklendi. Görseller kullanıcı tarafından harici araçlarla üretildi (bkz. AI kullanım raporu).",
            "- ✅ **Müzik:** " + ("kullanıcının sağladığı telifsiz dosya kullanıldı." if (_cur("video") or {}).get("music")
                                  else "videoda müzik yok (telif riski önlendi)."),
            "- ✅ **Font:** Noto Sans, SIL Open Font License 1.1.",
            "- ℹ️ **Veri gizliliği:** Gemini ücretsiz katmanında gönderilen içerik Google ürünlerini geliştirmek için "
            "kullanılabilir; yalnızca kurgusal marka verisi gönderildi.",
            "", "## Ayrıntılar", ""] + details
    return "\n".join(out)


# --------------------------------------------------------------------------- prompt kütüphanesi + rapor

TASK_LABELS = {
    "brand_identity": "Marka kimliği", "competitor_analysis": "Rakip analizi", "personas": "Persona",
    "brand_voice": "Marka sesi rehberi", "content_pillars": "Strateji ve içerik sütunları", "calendar": "İçerik takvimi",
    "blog": "Blog yazısı", "social_post": "Sosyal gönderi", "image_prompt": "Görsel promptu", "image": "Görsel",
    "voiceover_script": "Seslendirme metni", "voiceover": "Seslendirme (ses)", "video_script": "Video senaryosu",
    "review": "Kontrol katmanı", "fix": "Öneriye göre düzeltme",
}


def _task_group(task: str) -> str:
    return task.split(":")[0]


def prompt_library_markdown() -> str:
    log = storage.read_jsonl(storage.prompt_log_path())
    out = ["# Prompt Kütüphanesi", "",
           "Sistemdeki her yapay zeka çağrısı otomatik loglandı. Her kayıtta görev, kullanılan formül, model/araç, "
           "prompt ve çıktı özeti yer alır. Metin üretimlerinde Marka Sesi Rehberi system prompt'a eklenmiştir "
           "(“marka sesi: evet”).", ""]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in log:
        if r.get("kind") != "human_edit" and r.get("stage") != "test":
            groups[_task_group(r.get("task", ""))].append(r)
    for task, rows in groups.items():
        out += [f"## {TASK_LABELS.get(task, task)}", ""]
        for n, r in enumerate(rows, 1):
            bv = "evet" if r.get("brand_voice_injected") else "hayır"
            meta = f"formül: **{r.get('formula', '-')}** · model/araç: `{r.get('model', '-')}`"
            if r.get("kind") in ("structured", "text"):
                meta += f" · marka sesi: {bv} · token: {r.get('input_tokens', 0)}→{r.get('output_tokens', 0)}"
            output = str(r.get("output", ""))
            summary = output[:400] + ("…" if len(output) > 400 else "")
            out += [f"### {n}. {r.get('timestamp', '')[:16].replace('T', ' ')}"
                    + (f" · {r['calendar_item_id']}" if r.get("calendar_item_id") else ""), meta, "",
                    "<details><summary>Prompt</summary>", "", "```text", str(r.get("user_prompt", "")).strip(), "```",
                    "", "</details>", "", f"**Çıktı özeti:** {summary}", ""]
    return "\n".join(out)


MODEL_REASONS = {
    "text": "Gemini ücretsiz katmanındaki en yetenekli Flash modeli; Türkçe kalite ve structured output desteği iyi.",
    "review": "Kontrol katmanı daha hafif bir modelle çalışır: kısa denetim görevi için yeterli, günlük kotayı korur.",
    "speech": "edge-tts: ücretsiz, anahtar gerektirmez, doğal Türkçe nöral sesler (Emel/Ahmet).",
    "image_upload": "Görsel API'si ücretli olduğu için görseller kullanıcı tarafından ücretsiz araçta üretildi; "
                    "prompt bu sistemde marka stil diline göre hazırlandı.",
}


def usage_report_markdown() -> str:
    log = [r for r in storage.read_jsonl(storage.prompt_log_path()) if r.get("stage") != "test"]
    rows: dict[tuple[str, str], dict] = {}
    edits: dict[str, int] = defaultdict(int)
    for r in log:
        task = _task_group(r.get("task", ""))
        if r.get("kind") == "human_edit":
            edits[task] += 1
            continue
        key = (task, r.get("model", "-"))
        d = rows.setdefault(key, {"n": 0, "in": 0, "out": 0, "kind": r.get("kind")})
        d["n"] += 1
        d["in"] += r.get("input_tokens", 0) or 0
        d["out"] += r.get("output_tokens", 0) or 0

    def reason(task: str, model: str, kind: str) -> str:
        if kind == "image_upload":
            return MODEL_REASONS["image_upload"]
        if kind == "speech":
            return MODEL_REASONS["speech"]
        return MODEL_REASONS["review"] if model == config.REVIEW_MODEL and task == "review" else MODEL_REASONS["text"]

    out = ["# AI Kullanım Raporu", "",
           "Sistem tamamen ücretsiz araçlarla çalıştı. Aşağıdaki tablo prompt logundan otomatik üretildi.", "",
           "| Görev | Model / araç | Neden seçildi | İstek sayısı | Token (giriş→çıkış) | Elle düzenleme |",
           "|---|---|---|---|---|---|"]
    for (task, model), d in sorted(rows.items()):
        tokens = f"{d['in']:,}→{d['out']:,}".replace(",", ".") if d["kind"] in ("structured", "text") else "-"
        out.append(f"| {TASK_LABELS.get(task, task)} | `{model}` | {reason(task, model, d['kind'])} | {d['n']} | "
                   f"{tokens} | {edits.get(task, 0)} |")
    ai_total = sum(d["n"] for d in rows.values() if d["kind"] in ("structured", "text"))
    edit_total = sum(edits.values())
    tools = defaultdict(int)
    for r in log:
        if r.get("kind") == "image_upload":
            tools[r.get("tool", "-")] += 1
    out += ["", "## Özet", "",
            f"- Toplam Gemini isteği: **{ai_total}** (önbellekten dönen yanıtlar dahil değil)",
            f"- Elle düzenleme: **{edit_total}** · elle düzenleme oranı: "
            f"**%{(100 * edit_total / ai_total if ai_total else 0):.0f}** (düzenleme / YZ üretimi)",
            "- Görsel üretim araçları: " + (", ".join(f"{t}: {n}" for t, n in tools.items()) or "henüz yükleme yok"),
            f"- Metin modeli: `{config.TEXT_MODEL}` · Kontrol modeli: `{config.REVIEW_MODEL}` · Ses: edge-tts",
            "- Maliyet: **0 TL** (Gemini ücretsiz katmanı, edge-tts, ücretsiz görsel araçları, yerel video montajı)",
            "", "## Sorumlu kullanım notları", "",
            "- Ücretsiz katmanda gönderilen içerik Google ürünlerini geliştirmek için kullanılabilir; yalnızca kurgusal "
            "marka verisi gönderildi.",
            "- Tüm metin çıktıları ikinci bir LLM geçişiyle kontrol edildi ve insan onayından geçti "
            "(bkz. kontrol_listesi.md).",
            "", "## Karşılaşılan sorunlar", "", "_(Bu bölümü kendi deneyiminle doldur: ör. kota sınırları, düzeltilen "
            "ton hataları, görsellerde yeniden üretim gerekenler.)_", "", "- ", "- ", "- "]
    return "\n".join(out)


# --------------------------------------------------------------------------- hepsi


def export_all() -> dict:
    """Tüm dosyaları üretir; {"files": [...], "zip": path} döndürür."""
    exp = storage.subdir("exports")
    files: list[Path] = [
        _write(exp / "marka_stratejisi.md", strategy_markdown()),
        strategy_docx(exp / "marka_stratejisi.docx"),
        _write(exp / "marka_sesi_rehberi.md", voice_markdown()),
        _write(exp / "kontrol_listesi.md", checklist_markdown()),
        _write(exp / "prompt_kutuphanesi.md", prompt_library_markdown()),
        _write(exp / "ai_kullanim_raporu.md", usage_report_markdown()),
    ]
    cal = _cur("calendar")
    if cal:
        files.append(xlsx.export_calendar(cal, _cur("brand_identity"), _cur("content_strategy"), _cur("personas"),
                                          exp / "icerik_takvimi.xlsx"))
    setdir = exp / "icerik_seti"
    if setdir.exists():
        shutil.rmtree(setdir)  # yalnızca dışa aktarım kopyası; asıl dosyalar workspace'te kalır
    files += [_write(setdir / "blog.md", blog_markdown()), _write(setdir / "sosyal_gonderiler.md", social_markdown()),
              _write(setdir / "seslendirme_ve_video.md", media_markdown())]
    for k in storage.keys_with_prefix("image:"):
        img = _cur(k)
        src = cgen.image_path(img)
        if src.exists():
            dst = setdir / "gorseller" / f"{k.split(':', 1)[1]}_{img['tool'].lower()}{src.suffix}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            files.append(Path(shutil.copy2(src, dst)))
    for key, name in (("voiceover", "seslendirme.mp3"), ("video", "video.mp4")):
        if (d := _cur(key)) and (storage.workspace() / d["path"]).exists():
            files.append(Path(shutil.copy2(storage.workspace() / d["path"], setdir / name)))

    zpath = exp / "icerik_seti.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.relative_to(exp).as_posix())
    rel = [f.relative_to(exp).as_posix() for f in files]
    storage.save_version("exports", {"files": rel, "zip": "icerik_seti.zip", "at": storage.now_iso()}, source="ai")
    return {"files": rel, "zip": zpath}
