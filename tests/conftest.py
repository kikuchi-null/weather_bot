"""テスト共通のfixture。

各テストで環境変数 DISCORD_WEBHOOK_URL / ZIP_CODES を必ず明示的にセットするため、
ここでは「テスト前に一度クリアしておく」ことだけを行い、
実行環境やリポジトリの .env に依存した値が紛れ込まないようにする。
"""

import pytest


@pytest.fixture(autouse=True)
def clear_weather_bot_env(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("ZIP_CODES", raising=False)
