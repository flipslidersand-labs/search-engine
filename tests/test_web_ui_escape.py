"""web/index.html の innerHTML 代入が動的値をエスケープしていることの静的検査"""

import re
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "searchengine" / "web" / "index.html"


def _interpolations():
    text = HTML.read_text(encoding="utf-8")
    found = []
    for m in re.finditer(r"innerHTML\s*=[^`;]*`(.*?)`", text, re.DOTALL):
        for expr in re.findall(r"\$\{(.*?)\}", m.group(1), re.DOTALL):
            found.append(expr.strip())
    return found


def test_innerhtml_templates_found():
    assert _interpolations()


def test_innerhtml_interpolations_are_escaped():
    bad = [e for e in _interpolations() if not e.startswith("escHtml(")]
    assert bad == []


def test_error_message_is_escaped():
    text = HTML.read_text(encoding="utf-8")
    assert "${e.message}" not in text
