"""環境変数と設定値の読み込みをまとめるモジュール。

Lambda環境には .env も python-dotenv も存在しないため、
import / 読み込みに失敗しても処理を止めないようにする。
"""

import os
from datetime import timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REQUEST_TIMEOUT = 10  # seconds（外部API呼び出し共通のタイムアウト）

JST = timezone(timedelta(hours=9))


def get_webhook_url():
    """環境変数 DISCORD_WEBHOOK_URL を取得する。"""
    return os.environ.get("DISCORD_WEBHOOK_URL")


def get_zip_codes():
    """環境変数 ZIP_CODES からカンマ区切りの郵便番号リストを取得する。"""
    raw = os.environ.get("ZIP_CODES", "")
    return [c.strip().replace("-", "") for c in raw.split(",") if c.strip()]
