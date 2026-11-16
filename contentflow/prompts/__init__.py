"""Prompt şablonlarını yükler ve doldurur.

Şablonlar `$degisken` sözdizimli `string.Template` kullanır. Jinja2 yerine bunu seçtik:
ek bağımlılık yok ve promptlardaki JSON örneklerinde geçen { } karakterleri
str.format'taki gibi kaçış gerektirmez.

Her şablonun ilk satırı bir HTML yorumudur (<!-- formül: ... -->); modele gönderilmez,
prompt kütüphanesinde formülü belgelemek için okunur.
"""
from __future__ import annotations

import re
from string import Template

from contentflow import config

_HEADER_RE = re.compile(r"^\s*<!--(.*?)-->\s*", re.DOTALL)


def load_raw(name: str) -> str:
    path = config.PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def header(name: str) -> str:
    """Şablonun başındaki yorum (formül ve gerekçe)."""
    m = _HEADER_RE.match(load_raw(name))
    return m.group(1).strip() if m else ""


def formula(name: str) -> str:
    """Başlık yorumundaki formül adı, ör. 'CO-STAR (uyarlanmış)'. Loga yazılır."""
    m = re.search(r"formül:\s*(.+?)\s+—", header(name))
    return m.group(1) if m else "serbest"


def render(name: str, **variables: object) -> str:
    """Şablonu doldurur. Eksik değişken varsa KeyError fırlatır (sessizce boş bırakmaz)."""
    body = _HEADER_RE.sub("", load_raw(name), count=1)
    return Template(body).substitute({k: str(v) for k, v in variables.items()}).strip()
