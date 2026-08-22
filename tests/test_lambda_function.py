"""lambda_function.lambda_handler のテスト。

実際のAPI呼び出しは行わず、config / discord_notifier をモックして
「環境変数のバリデーション」と「各関数への処理の受け渡し」だけを検証する。
"""

import json

import pytest

import lambda_function


def test_raises_when_webhook_url_is_missing(mocker):
    mocker.patch("lambda_function.get_webhook_url", return_value=None)
    mocker.patch("lambda_function.get_zip_codes", return_value=["1500041"])

    with pytest.raises(ValueError, match="DISCORD_WEBHOOK_URL"):
        lambda_function.lambda_handler(None, None)


def test_raises_when_zip_codes_is_missing(mocker):
    mocker.patch("lambda_function.get_webhook_url", return_value="https://discord.com/api/webhooks/xxx/yyy")
    mocker.patch("lambda_function.get_zip_codes", return_value=[])

    with pytest.raises(ValueError, match="ZIP_CODES"):
        lambda_function.lambda_handler(None, None)


def test_happy_path_builds_embed_and_sends_it_once(mocker):
    webhook_url = "https://discord.com/api/webhooks/xxx/yyy"
    zip_codes = ["1500041", "5300001"]
    fake_embed = {"title": "🌤️ 今日の天気予報"}

    mocker.patch("lambda_function.get_webhook_url", return_value=webhook_url)
    mocker.patch("lambda_function.get_zip_codes", return_value=zip_codes)
    build_embed = mocker.patch("lambda_function.build_embed", return_value=fake_embed)
    send_discord = mocker.patch("lambda_function.send_discord")

    response = lambda_function.lambda_handler(None, None)

    build_embed.assert_called_once_with(zip_codes)
    send_discord.assert_called_once_with(webhook_url, fake_embed)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"message": "notified", "zip_codes": zip_codes}
