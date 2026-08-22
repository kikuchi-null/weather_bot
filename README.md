# 天気予報通知ツール

複数地点（郵便番号で指定）の天気予報をまとめて取得し、Discord Webhookに通知するツールです。
ローカル(Mac)で動作確認したのち、AWS Lambda + EventBridge Schedulerで毎日定期実行することを想定しています。

## 仕組み

郵便番号ごとに以下を実行し、最後に全地点をまとめて1回のDiscord通知にします。

1. **zipcloud API** : 郵便番号 → 住所（都道府県・市区町村・町域）
2. **国土地理院 地名検索API** : 住所 → 緯度経度
3. **Open-Meteo API** : 緯度経度 → 天気予報（最高/最低気温・天気・降水確率）

いずれもAPIキー不要です。

## コード構成

`lambda_function.py` はLambdaハンドラー/ローカル実行の入り口としてのみ機能する薄いラッパーで、
実処理は責務ごとに `weather_notify` パッケージへ分割しています。

```
lambda_function.py          # エントリポイント（lambda_handler / 単体実行）
weather_notify/
  config.py                 # 環境変数・タイムアウトなどの設定値
  geocoding.py               # 郵便番号 -> 住所 -> 緯度経度（zipcloud / 国土地理院）
  weather.py                 # 緯度経度 -> 天気予報、weathercodeの日本語化、判定ロジック
  forecast.py                # 1地点分の「取得 -> 判定」をまとめるオーケストレーション層
  discord_notifier.py        # Embedの整形とWebhook送信
```

地点を追加したい／判定ロジックを変えたい場合は `weather.py`、通知の見た目を変えたい場合は
`discord_notifier.py` など、変更したい関心事に応じて触るファイルが1つに絞られるようにしています。

## ローカルでの実行手順

1. 仮想環境の作成・有効化（任意ですが推奨）

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. 依存パッケージのインストール

   ```bash
   pip install -r requirements.txt
   ```

3. `.env` ファイルを作成し、値を設定

   ```bash
   cp .env.example .env
   ```

   `.env` の中身を編集:

   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxxx/xxxxx
   ZIP_CODES=1500002,5300001
   ```

   - `DISCORD_WEBHOOK_URL` : 通知したいDiscordチャンネルのWebhook URL
   - `ZIP_CODES` : 通知したい地点の郵便番号をカンマ区切りで指定（ハイフンあり/なしどちらも可）

4. 実行

   ```bash
   python lambda_function.py
   ```

   実行すると通知メッセージがコンソールにも出力され、指定したDiscordチャンネルに通知が届きます。

## テストの実行

外部API（zipcloud / 国土地理院 / Open-Meteo / Discord Webhook）は`requests-mock`でモックしているため、
テスト実行時にネットワーク通信は発生しません。

1. テスト用の依存関係をインストール

   ```bash
   pip install -r requirements-dev.txt
   ```

2. 実行

   ```bash
   pytest
   ```

`tests/` 配下に `weather_notify` の各モジュール（`config` / `geocoding` / `weather` / `forecast` / `discord_notifier`）と
`lambda_function.lambda_handler` に対応するテストファイルを1つずつ用意しています。

## AWS Lambdaへのデプロイ手順（概要）

1. デプロイパッケージの作成（`python-dotenv` はLambdaでは不要なので含めません）

   ```bash
   mkdir package
   pip install requests -t package/
   cp lambda_function.py package/
   cp -r weather_notify package/
   cd package
   zip -r ../lambda_function.zip .
   cd ..
   ```

2. Lambda関数の作成・更新

   - ランタイム: Python（3.11など）
   - ハンドラー: `lambda_function.lambda_handler`
   - 上記 `lambda_function.zip` をアップロード

3. Lambdaの環境変数を設定（ローカルの `.env` と同じキーを、Lambdaのコンソール/CLIから設定）

   - `DISCORD_WEBHOOK_URL`
   - `ZIP_CODES`

   Lambda環境には `.env` ファイルは存在しませんが、`lambda_function.py` は
   `python-dotenv` のimportに失敗しても処理を継続するようになっているため、
   そのままLambdaの環境変数から値を読み込みます。

4. EventBridge Schedulerでこの関数を毎日決まった時刻に呼び出すよう設定すれば完成です。

## 地点の追加・変更

コード内に郵便番号のハードコードはありません。地点を増減したい場合は、
`.env`（Lambdaの場合は環境変数）の `ZIP_CODES` をカンマ区切りで書き換えるだけで反映されます。
