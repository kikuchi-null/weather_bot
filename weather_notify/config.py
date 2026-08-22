"""環境変数と設定値の読み込みをまとめるモジュール。

Lambda環境には .env も python-dotenv も存在しないため、
import / 読み込みに失敗しても処理を止めないようにする。
"""

import os
import sys
from datetime import timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Lambda環境ではpython-dotenvを同梱しないため、ここに来るのは正常。
    # ローカル実行でここに来る場合は大抵venv未有効化 or pip install忘れが原因で、
    # .envが読み込まれずDISCORD_WEBHOOK_URL等が「未設定」に見えてしまうため、
    # 原因を切り分けやすいようstderrに一言残す（処理自体は継続する）。
    print(
        "[INFO] python-dotenv が見つからないため .env の読み込みをスキップしました。"
        "Lambda環境ではこれが正常な状態です。ローカル実行でこのメッセージが出る場合は、"
        "venvを有効化して `pip install -r requirements.txt` を実行済みか確認してください。",
        file=sys.stderr,
    )

REQUEST_TIMEOUT = 10  # seconds（外部API呼び出し共通のタイムアウト）

JST = timezone(timedelta(hours=9))


def get_webhook_url():
    """環境変数 DISCORD_WEBHOOK_URL を取得する。"""
    return os.environ.get("DISCORD_WEBHOOK_URL")


def get_zip_codes():
    """環境変数 ZIP_CODES からカンマ区切りの郵便番号リストを取得する。"""
    raw = os.environ.get("ZIP_CODES", "")
    return [c.strip().replace("-", "") for c in raw.split(",") if c.strip()]
