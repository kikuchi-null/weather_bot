"""
天気予報通知ツール - エントリポイント
======================================

指定した郵便番号（複数可）の天気予報を Open-Meteo から取得し、
Discord Webhook に1回のPOSTでまとめて通知する。

実処理は `weather_notify` パッケージ側に分割して置いてあり、
このファイルはLambdaハンドラー / ローカル実行の入り口としてのみ機能する薄いラッパー。
処理の内訳は `weather_notify/__init__.py` のモジュール一覧を参照。

ローカル実行:
    python lambda_function.py

AWS Lambda 実行:
    handler = lambda_function.lambda_handler
"""

import json

from weather_notify.config import get_webhook_url, get_zip_codes
from weather_notify.discord_notifier import build_embed, send_discord


def lambda_handler(event, context):
    webhook_url = get_webhook_url()
    if not webhook_url:
        raise ValueError("環境変数 DISCORD_WEBHOOK_URL が設定されていません")

    zip_codes = get_zip_codes()
    if not zip_codes:
        raise ValueError("環境変数 ZIP_CODES が設定されていません")

    embed = build_embed(zip_codes)
    print(json.dumps(embed, ensure_ascii=False, indent=2))

    send_discord(webhook_url, embed)

    return {"statusCode": 200, "body": json.dumps({"message": "notified", "zip_codes": zip_codes})}


if __name__ == "__main__":
    lambda_handler(None, None)
