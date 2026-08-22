"""天気データをDiscord Embedの見た目に整形し、Webhookへ送信するモジュール。

地点ごとのブロックはEmbedの「field」ではなく「description」内の
blockquote（各行先頭に`> `）として表現する。fieldはPC幅では横並びグリッドになる一方、
iPhoneなど画面の狭いDiscordアプリでは区切り線なしで縦に積まれるだけになり、
「どこからどこまでが1地点分の予報か」が分かりにくくなるため採用しない。
blockquote + 空行区切りであれば、画面幅によらず1地点＝1つの縦線付きブロックとして
見えるため、地点間の境界が常に明確になる。
"""

import sys
from datetime import datetime

import requests

from .config import REQUEST_TIMEOUT, JST
from .forecast import build_location_data
from .weather import SUNNY_CODES

# Embedの帯色（傘が必要な地点があるか/晴れ一色かで切り替える）
COLOR_RAIN = 0x3498DB    # 青: 傘が必要な地点が1つでもある
COLOR_SUNNY = 0xF39C12   # オレンジ: 全地点が晴れ
COLOR_CLOUDY = 0x95A5A6  # グレー: 曇り中心（雨なし・晴れなし）
COLOR_UNKNOWN = 0x2C3E50 # 濃紺: 全地点で取得失敗

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def build_location_block(data):
    """1地点分のデータを、blockquoteで囲んだ1ブロックのMarkdownにする。"""
    lines = [
        f"### 📍 {data['display_name']}",
        f"{data['weather_emoji']} {data['weather_text']}",
        f"🌡️ 最高 **{round(data['temp_max'])}℃** / 最低 **{round(data['temp_min'])}℃**",
        f"☂️ 傘: **{data['umbrella']}**",
        f"👕 服装: {data['advice']}",
    ]
    return "\n".join(f"> {line}" for line in lines)


def build_error_block(zipcode):
    """1地点分の取得に失敗した場合のblockquoteブロックを作る。"""
    lines = [
        f"### 📍 (郵便番号: {zipcode})",
        "⚠️ *天気情報の取得に失敗しました*",
    ]
    return "\n".join(f"> {line}" for line in lines)


def determine_embed_color(location_data_list):
    """地点ごとの天気からEmbedの帯色を決める（傘要否 > 全晴れ > 曇り中心の優先度）。"""
    if not location_data_list:
        return COLOR_UNKNOWN
    if any(d["umbrella"] == "必要" for d in location_data_list):
        return COLOR_RAIN
    if all(d["weathercode"] in SUNNY_CODES for d in location_data_list):
        return COLOR_SUNNY
    return COLOR_CLOUDY


def build_summary(zip_codes, location_data_list):
    """全地点をまとめたサマリー行（日付・対象地点数・傘が必要な地点数）を作る。"""
    now_jst = datetime.now(JST)
    date_str = f"{now_jst.month}月{now_jst.day}日({WEEKDAY_JA[now_jst.weekday()]})"

    summary = f"**{date_str}** の予報（対象 {len(zip_codes)}地点）"

    failed_count = len(zip_codes) - len(location_data_list)
    if failed_count > 0:
        summary += f" ⚠️ {failed_count}件取得失敗"

    if location_data_list:
        # 分母は「取得できた地点数」。失敗地点を含む全体数と混同しないよう、
        # 取得失敗があった場合は上の一文で別途明示している。
        umbrella_needed = sum(1 for d in location_data_list if d["umbrella"] == "必要")
        summary += f"\n☂️ 傘が必要な地点: **{umbrella_needed} / {len(location_data_list)}**"

    return summary, now_jst


def build_embed(zip_codes):
    """全地点分の天気情報をまとめたDiscord Embedを組み立てる。"""
    blocks = []
    location_data_list = []

    for zipcode in zip_codes:
        try:
            data = build_location_data(zipcode)
            location_data_list.append(data)
            blocks.append(build_location_block(data))
        except Exception as e:  # 1地点の失敗で通知全体を止めない
            print(f"[WARN] failed to build report for zipcode={zipcode}: {e}", file=sys.stderr)
            blocks.append(build_error_block(zipcode))

    summary, now_jst = build_summary(zip_codes, location_data_list)

    # サマリーと地点ブロック、地点ブロック同士を空行で区切ることで、
    # blockquoteが途切れて隣接ブロックと視覚的に混ざらないようにする。
    description = "\n\n".join([summary] + blocks)

    return {
        "title": "🌤️ 今日の天気予報",
        "description": description,
        "color": determine_embed_color(location_data_list),
        "timestamp": now_jst.isoformat(),
        "footer": {"text": "Data by Open-Meteo"},
    }


def send_discord(webhook_url, embed):
    """Discord Webhookに1回のPOSTでEmbedメッセージを送信する。"""
    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp
