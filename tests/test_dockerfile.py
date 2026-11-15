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


def test_uid_is_pinned_for_volume_chown():
    """README/PR の chown 手順(999:999)と一致するよう uid/gid を固定する。"""
    text = DOCKERFILE.read_text()
    assert "--uid 999" in text and "--gid 999" in text


def test_all_db_paths_under_data_volume():
    """read_only 運用で書込み先が /data に収まること(SEARCH_DB と SCHEMA_DB)。"""
    text = DOCKERFILE.read_text()
    assert "SEARCH_DB=/data/" in text
    assert "SCHEMA_DB=/data/" in text


def test_compose_is_read_only_and_drops_caps():
    compose = (DOCKERFILE.parent / "docker-compose.yml").read_text()
    assert "read_only: true" in compose
    assert "cap_drop" in compose and "- ALL" in compose
