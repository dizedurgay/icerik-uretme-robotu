"""Tüm Python dosyalarının sözdizimi hatasız derlendiğini doğrular.
(Streamlit AppTest bazı sözdizimi hatalarını exception listesine koymadığı için ayrıca gerekli.)"""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "app.py", *sorted((ROOT / "pages").glob("*.py")), *sorted((ROOT / "contentflow").rglob("*.py"))]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_compiles(path):
    src = path.read_text(encoding="utf-8")
    compile(src, str(path), "exec")
    # Proje hedefi Python 3.11+; Streamlit de sayfaları feature_version ile ayrıştırır. 3.12'ye özgü
    # sözdizimi (ör. satır içinde kırılan f-string) burada yakalanır.
    ast.parse(src, filename=str(path), feature_version=(3, 11))
