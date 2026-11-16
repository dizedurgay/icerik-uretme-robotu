"""İçerik takvimini biçimlendirilmiş .xlsx olarak dışa aktarır (openpyxl).

- Başlık satırı marka paletinin en koyu rengiyle, beyaz kalın yazı
- Sütun genişlikleri ayarlı, metin kaydırmalı, başlık dondurulmuş, filtre açık
- "Durum" sütununda açılır liste (veri doğrulama)
- İkinci sayfa: içerik sütunları ve persona özeti (takvimin stratejik dayanağı)
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from contentflow import models

# (başlık, alan, genişlik)
COLUMNS = [
    ("Gün", "weekday", 12), ("Tarih", "date", 12), ("Saat", "time_slot", 8), ("Kanal", "channel", 16),
    ("Format", "format", 22), ("Teslim çıktıları", "deliverables", 22), ("İçerik sütunu", "pillar", 22),
    ("Hedef persona", "persona", 16), ("Konu / Başlık", "topic", 40), ("Amaç", "goal", 13),
    ("Gerekçe", "rationale", 60), ("Durum", "status", 13), ("ID", "id", 8),
]


def _luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def header_color(palette: list[dict]) -> str:
    valid = [c["hex"] for c in palette if models.HEX_RE.match(c.get("hex", ""))]
    return min(valid, key=_luminance).lstrip("#").upper() if valid else "3B2A20"


def _light_color(palette: list[dict]) -> str:
    valid = [c["hex"] for c in palette if models.HEX_RE.match(c.get("hex", ""))]
    return max(valid, key=_luminance).lstrip("#").upper() if valid else "F4EBDD"


def _style_header(ws, ncols: int, fill_hex: str) -> None:
    fill = PatternFill("solid", fgColor=fill_hex)
    for col in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = fill
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"


def export_calendar(calendar: dict, identity: dict | None, strategy: dict | None,
                    personas: dict | None, path: Path) -> Path:
    palette = (identity or {}).get("palette", [])
    head_hex, band_hex = header_color(palette), _light_color(palette)
    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    wb = Workbook()
    ws = wb.active
    ws.title = "İçerik Takvimi"
    ws.append([c[0] for c in COLUMNS])
    for item in calendar["items"]:
        row = []
        for _, field, _ in COLUMNS:
            value = item.get(field, "")
            if field == "deliverables":
                value = ", ".join(models.DELIVERABLE_LABELS.get(d, d) for d in value or [])
            row.append(value)
        ws.append(row)

    _style_header(ws, len(COLUMNS), head_hex)
    band = PatternFill("solid", fgColor=band_hex)
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(COLUMNS) + 1):
            cell = ws.cell(row=r, column=c)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border
            if r % 2 == 0:
                cell.fill = band
    for i, (_, _, width) in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    last = get_column_letter(len(COLUMNS))
    ws.auto_filter.ref = f"A1:{last}{ws.max_row}"

    status_col = get_column_letter([c[1] for c in COLUMNS].index("status") + 1)
    dv = DataValidation(type="list", formula1='"' + ",".join(models.STATUS_OPTIONS) + '"', allow_blank=False,
                        showErrorMessage=True, errorTitle="Geçersiz durum",
                        error="Listeden bir durum seç: " + ", ".join(models.STATUS_OPTIONS))
    ws.add_data_validation(dv)
    dv.add(f"{status_col}2:{status_col}{max(ws.max_row, 2) + 20}")

    if note := calendar.get("strategy_note"):
        ws.cell(row=ws.max_row + 2, column=1, value="Haftanın kurgusu:").font = Font(bold=True)
        ws.cell(row=ws.max_row, column=2, value=note).alignment = Alignment(wrap_text=False)

    # --- 2. sayfa: strateji dayanağı
    ws2 = wb.create_sheet("Sütunlar ve Persona")
    ws2.append(["İçerik sütunu", "Amaç", "Persona eşleşmesi", "Kanallar"])
    for p in (strategy or {}).get("pillars", []):
        ws2.append([p["name"], p["purpose"], p["persona_match"], ", ".join(p["best_channels"])])
    _style_header(ws2, 4, head_hex)
    start = ws2.max_row + 2
    ws2.cell(row=start, column=1, value="Persona").font = Font(bold=True)
    for p in (personas or {}).get("personas", []):
        start += 1
        ws2.cell(row=start, column=1, value=f"{p['name']} ({p['age']}, {p['occupation']})")
        ws2.cell(row=start, column=2, value="Acı noktaları: " + "; ".join(p["pain_points"]))
    for i, w in enumerate((26, 50, 50, 30), 1):
        ws2.column_dimensions[get_column_letter(i)].width = w
    for row in ws2.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
