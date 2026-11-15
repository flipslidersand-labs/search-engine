"""Dockerfile が非 root で実行する設定になっていることの静的検査。"""

from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parent.parent / "Dockerfile"


def _user_lines():
    return [
        line.split(None, 1)[1].strip()
        for line in DOCKERFILE.read_text().splitlines()
        if line.strip().upper().startswith("USER ")
    ]


def test_user_instruction_exists():
    assert _user_lines(), "Dockerfile に USER 指定がない"


def test_final_user_is_not_root():
    user = _user_lines()[-1].split(":")[0]
    assert user not in ("root", "0")
