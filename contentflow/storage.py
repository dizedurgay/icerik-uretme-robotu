"""workspace/ altındaki JSON durumunu okuma/yazma.

Veritabanı yok: tüm durum tek bir state.json'da, prompt logu ise satır başına bir
JSON (jsonl) dosyasında. Hiçbir üretim silinmez; her bölüm versiyon listesi tutar.

state.json şeması (özet):
{
  "sections": {
    "<anahtar>": {"current": 2, "versions": [
        {"v": 1, "content": {...}, "source": "ai|human|fix", "log_id": "...",
         "created_at": "...", "calendar_item_id": null, "note": ""}, ...]}
  },
  "meta": {...}
}
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from contentflow import config

# --- Yollar (çağrı anında hesaplanır; testlerde WORKSPACE_DIR değiştirilebilir) ---


def workspace() -> Path:
    return Path(config.WORKSPACE_DIR)


def state_path() -> Path:
    return workspace() / "state.json"


def prompt_log_path() -> Path:
    return workspace() / "prompt_log.jsonl"


def subdir(name: str) -> Path:
    """images, audio, video, exports, cache gibi alt klasörleri oluşturup döndürür."""
    p = workspace() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_workspace() -> None:
    for name in ("images", "audio", "video", "exports", "cache"):
        subdir(name)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# --- Düşük seviye JSON yardımcıları ---


def _atomic_write_text(path: Path, text: str) -> None:
    """Önce geçici dosyaya yazıp sonra yerine koyar; yarım yazılmış state.json oluşmaz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    _atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# --- State ---


def load_state() -> dict:
    state = read_json(state_path(), default=None) or {}
    state.setdefault("sections", {})
    state.setdefault("meta", {})
    return state


def save_state(state: dict) -> None:
    write_json(state_path(), state)


def load_brand_seed() -> dict:
    """Kullanıcının arayüzde düzenlediği tohum varsa onu, yoksa brand_seed.yaml'ı döndürür."""
    edited = get_current("brand_seed")
    if edited:
        return edited
    with open(config.BRAND_SEED_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# --- Versiyonlu bölümler ---


def save_version(
    key: str,
    content: Any,
    *,
    source: str = "ai",
    log_id: str | None = None,
    calendar_item_id: str | None = None,
    note: str = "",
) -> int:
    """Bölüme yeni bir versiyon ekler ve onu güncel yapar. Yeni versiyon numarasını döner.

    source: "ai" (üretim), "human" (elle düzenleme), "fix" (kontrol önerisiyle düzeltme)
    """
    state = load_state()
    section = state["sections"].setdefault(key, {"current": 0, "versions": []})
    v = len(section["versions"]) + 1
    section["versions"].append({
        "v": v,
        "content": content,
        "source": source,
        "log_id": log_id,
        "calendar_item_id": calendar_item_id,
        "created_at": now_iso(),
        "note": note,
    })
    section["current"] = v
    save_state(state)
    return v


def get_section(key: str) -> dict | None:
    return load_state()["sections"].get(key)


def get_current_version(key: str) -> dict | None:
    section = get_section(key)
    if not section or not section["versions"]:
        return None
    return section["versions"][section["current"] - 1]


def get_current(key: str, default: Any = None) -> Any:
    ver = get_current_version(key)
    return ver["content"] if ver else default


def set_current(key: str, v: int) -> None:
    """Eski bir versiyona geri dön (silmeden)."""
    state = load_state()
    section = state["sections"][key]
    if not 1 <= v <= len(section["versions"]):
        raise ValueError(f"{key} için v{v} yok")
    section["current"] = v
    save_state(state)


def set_meta(key: str, value: Any) -> None:
    state = load_state()
    state["meta"][key] = value
    save_state(state)


def get_meta(key: str, default: Any = None) -> Any:
    return load_state()["meta"].get(key, default)


# --- İlerleme ---

# Gereksinim: (anahtar, en az adet). Anahtar ":" ile bitiyorsa önek sayılır;
# ör. ("social_post:", 3) → "social_post:cal-02" gibi en az 3 dolu bölüm.
Requirement = tuple[str, int]

# (sayfa başlığı, sayfa dosyası, tamamlanmış sayılması için gereksinimler)
STAGES: list[tuple[str, str, list[Requirement]]] = [
    ("1. Marka Kimliği", "pages/1_Marka_Kimligi.py", [("brand_identity", 1)]),
    ("2. Ses ve Strateji", "pages/2_Ses_ve_Strateji.py",
     [("brand_voice", 1), ("personas", 1), ("content_strategy", 1)]),
    ("3. İçerik Takvimi", "pages/3_Icerik_Takvimi.py", [("calendar", 1)]),
    ("4. İçerik Üretimi", "pages/4_Icerik_Uretimi.py",
     [("blog", 1), ("social_post:", 3), ("image:", 3), ("voiceover", 1), ("video", 1)]),
    ("5. Kontrol", "pages/5_Kontrol.py", [("decision:", 1)]),
    ("6. Dışa Aktar", "pages/6_Disa_Aktar.py", [("exports", 1)]),
]


def count_filled(key: str, sections: dict | None = None) -> int:
    """Anahtar (veya ':' ile biten önek) için içeriği olan bölüm sayısı."""
    sections = load_state()["sections"] if sections is None else sections
    if key.endswith(":"):
        return sum(1 for k, s in sections.items() if k.startswith(key) and s.get("versions"))
    return 1 if sections.get(key, {}).get("versions") else 0


def keys_with_prefix(prefix: str) -> list[str]:
    return sorted(k for k, s in load_state()["sections"].items() if k.startswith(prefix) and s.get("versions"))


def stage_progress() -> list[dict]:
    """Her aşama için {title, page, done, partial} listesi."""
    sections = load_state()["sections"]
    out = []
    for title, page, reqs in STAGES:
        met = [count_filled(k, sections) >= n for k, n in reqs]
        started = [count_filled(k, sections) > 0 for k, _ in reqs]
        out.append({"title": title, "page": page, "done": all(met), "partial": any(started) and not all(met)})
    return out


def first_missing_stage(required_keys: list[str]) -> str | None:
    """Gereken bölümlerden (anahtar veya önek) ilk eksik olanın aşama başlığını döndürür."""
    sections = load_state()["sections"]
    for title, _page, reqs in STAGES:
        for k, _n in reqs:
            if k in required_keys and count_filled(k, sections) == 0:
                return title
    return None
