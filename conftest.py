import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest


@pytest.fixture(autouse=True)
def _allow_no_auth_by_default(monkeypatch):
    """既存テストは API_KEY 未設定を前提とするため ALLOW_NO_AUTH=1 を既定にする (#121)。

    fail-closed の挙動を検証するテストは自身で delenv する。
    """
    monkeypatch.setenv("ALLOW_NO_AUTH", "1")
