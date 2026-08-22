"""天気予報通知ツールの実処理をまとめたパッケージ。

lambda_function.py はこのパッケージを呼び出すだけの薄いエントリポイントとし、
郵便番号 -> 住所 -> 座標 -> 天気 -> Discord通知 という各段階の実処理は
責務ごとに分割したモジュールに置く。

    config.py           : 環境変数・タイムアウトなどの設定値
    geocoding.py         : 郵便番号 -> 住所 -> 緯度経度（zipcloud / 国土地理院）
    weather.py           : 緯度経度 -> 天気予報、weathercodeの日本語化、判定ロジック
    forecast.py          : 1地点分の「取得 -> 判定」をまとめるオーケストレーション層
    discord_notifier.py  : Embedの整形とWebhook送信
"""
