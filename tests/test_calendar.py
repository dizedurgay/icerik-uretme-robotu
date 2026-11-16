"""Aşama 3a testleri: takvim üretimi (mock), kısıtlar, xlsx. Gerçek API çağrısı yok."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from contentflow import config, llm, models, prompts, storage
from contentflow.exporters import xlsx
from contentflow.generators import calendar as cal_gen
from tests import sample_data as sd

ROOT = Path(__file__).resolve().parent.parent
START = date(2026, 11, 23)  # Pazartesi


@pytest.fixture(autouse=True)
def stage2_done(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    for key, obj in (("brand_identity", sd.IDENTITY), ("personas", sd.PERSONAS),
                     ("brand_voice", sd.VOICE), ("content_strategy", sd.STRATEGY)):
        storage.save_version(key, obj.model_dump(mode="json"))


@pytest.fixture
def generated(monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw)
        return llm.CallResult(sd.CALENDAR, "logcal", cached=False)

    monkeypatch.setattr(llm, "generate_structured", fake)
    result, issues = cal_gen.generate_calendar(START)
    return calls, issues


def test_generation_valid_and_dates(generated):
    calls, issues = generated
    assert issues == []
    cal = storage.get_current("calendar")
    first, last = cal["items"][0], cal["items"][-1]
    assert (first["id"], first["date"], first["weekday"]) == ("cal-01", "2026-11-23", "Pazartesi")
    assert (last["date"], last["weekday"]) == ("2026-11-29", "Pazar")
    assert all(i["status"] == "Planlandı" for i in cal["items"])
    assert calls[0]["with_brand_voice"] is True  # marka sesi enjekte
    assert "$" not in calls[0]["user_prompt"] and "23.11" not in calls[0]["user_prompt"]
    assert "# Context" in prompts.load_raw("calendar") and "# Response" in prompts.load_raw("calendar")


def test_check_calendar_catches_problems(generated):
    items = [dict(i) for i in storage.get_current("calendar")["items"]]
    items = [i for i in items if "video" not in i["deliverables"]]  # videoyu ve 4. günü kaldır
    items[0]["rationale"] = "Genel bir gerekçe."
    items[1]["pillar"] = "Uydurma"
    found = " | ".join(models.check_calendar(items, ["S0", "S1", "S2"], ["Ece"]))
    for expected in ("Boş gün var: 4", "Kısa video 0/1", "Seslendirme 0/1",
                     "gerekçe personaya atıf yapmıyor", "tanımlı sütunlardan biri değil"):
        assert expected in found, expected


def test_normalize_keeps_existing_ids(generated):
    cal = storage.get_current("calendar")
    rows = [dict(i) for i in cal["items"]] + [{"day": 1, "time_slot": "07:00", "topic": "yeni"}]
    rows[2]["day"] = 7
    out = cal_gen.normalize_items(rows, START)
    assert out[0]["topic"] == "yeni" and out[0]["id"] == "cal-08"
    assert sorted(r["id"] for r in out) == sorted({r["id"] for r in out})  # benzersiz
    moved = next(r for r in out if r["id"] == "cal-03")
    assert moved["date"] == "2026-11-29"


def test_xlsx_export(generated, tmp_path):
    path = xlsx.export_calendar(storage.get_current("calendar"), sd.IDENTITY.model_dump(),
                                sd.STRATEGY.model_dump(), sd.PERSONAS.model_dump(), tmp_path / "t.xlsx")
    wb = load_workbook(path)
    ws = wb["İçerik Takvimi"]
    assert ws["A1"].value == "Gün" and ws["K1"].value == "Gerekçe"
    assert ws["A1"].fill.fgColor.rgb.endswith("3B2A20")  # paletin en koyu rengi
    assert ws.auto_filter.ref.startswith("A1:")
    assert ws.freeze_panes == "A2"
    dvs = ws.data_validations.dataValidation
    assert dvs and "Planlandı" in dvs[0].formula1
    assert ws["F3"].value == "Sosyal gönderi, Görsel"
    assert "Sütunlar ve Persona" in wb.sheetnames


def test_page_renders(generated):
    at = AppTest.from_file(str(ROOT / "pages/3_Icerik_Takvimi.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Tüm kısıtlar sağlanıyor" in s.value for s in at.success)
