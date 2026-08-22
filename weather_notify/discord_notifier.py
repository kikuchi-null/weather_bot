"""天気データをDiscord Embedの見た目に整形し、Webhookへ送信するモジュール。

地点ごとのブロックはEmbedの「field」ではなく「description」内の
blockquote（各行先頭に`> `）として表現する。fieldはPC幅では横並びグリッドになる一方、
iPhoneなど画面の狭いDiscordアプリでは区切り線なしで縦に積まれるだけになり、
「どこからどこまでが1地点分の予報か」が分かりにくくなるため採用しない。
blockquote + 空行区切りであれば、画面幅によらず1地点＝1つの縦線付きブロックとして
見えるため、地点間の境界が常に明確になる。
"""

import sys
import concurrent.futures
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import requests

from .config import REQUEST_TIMEOUT, JST
from .forecast import build_location_data
from .weather import SUNNY_CODES

# 郵便番号1件につきzipcloud/国土地理院/Open-Meteoの3回のHTTP通信が発生するため、
# 地点数が増えるほど逐次実行では待ち時間が積み上がる。並列実行時の同時実行数の上限。
MAX_WORKERS = 8

# Embedの帯色（傘が必要な地点があるか/晴れ一色かで切り替える）
COLOR_RAIN = 0x3498DB    # 青: 傘が必要な地点が1つでもある
COLOR_SUNNY = 0xF39C12   # オレンジ: 全地点が晴れ
COLOR_CLOUDY = 0x95A5A6  # グレー: 曇り中心（雨なし・晴れなし）
COLOR_UNKNOWN = 0x2C3E50 # 濃紺: 全地点で取得失敗

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def _round_half_up(value):
    """四捨五入で整数に丸める。

    Pythonの組み込み round() は銀行丸め（偶数への丸め）のため、
    24.5 のようなちょうど.5の値が期待と異なる向きに丸まることがある
    （例: round(24.5) == 24）。気温表示は直感的な四捨五入にしたいため、
    Decimalを使って明示的にROUND_HALF_UPで丸める。
    """
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _to_blockquote(lines):
    """各行の先頭に`> `を付け、1つのblockquoteブロックにまとめる。"""
    return "\n".join(f"> {line}" for line in lines)


def build_location_block(data):
    """1地点分のデータを、blockquoteで囲んだ1ブロックのMarkdownにする。"""
    lines = [
        f"### 📍 {data['display_name']}",
        f"{data['weather_emoji']} {data['weather_text']}",
        f"🌡️ 最高 **{_round_half_up(data['temp_max'])}℃** / 最低 **{_round_half_up(data['temp_min'])}℃**",
        f"☂️ 傘: **{data['umbrella']}**",
        f"👕 服装: {data['advice']}",
    ]
    return _to_blockquote(lines)


def build_error_block(zipcode):
    """1地点分の取得に失敗した場合のblockquoteブロックを作る。"""
    lines = [
        f"### 📍 (郵便番号: {zipcode})",
        "⚠️ *天気情報の取得に失敗しました*",
    ]
    return _to_blockquote(lines)


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


def _fetch_all_location_data(zip_codes):
    """全地点分の天気データを並列に取得し、zip_codesと同じ順序のリストで返す。

    各地点の取得は互いに独立しているため、ThreadPoolExecutorで並列実行して
    合計待ち時間を短縮する。1地点の失敗が他地点に影響しないという性質は
    維持し、成功/失敗を ("ok", data) / ("error", exception) のタプルで表す。
    """
    results = [None] * len(zip_codes)
    if not zip_codes:
        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(zip_codes), MAX_WORKERS)) as executor:
        future_to_index = {
            executor.submit(build_location_data, zipcode): i
            for i, zipcode in enumerate(zip_codes)
        }
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = ("ok", future.result())
            except Exception as e:  # 1地点の失敗で通知全体を止めない
                results[index] = ("error", e)

    return results


def build_embed(zip_codes):
    """全地点分の天気情報をまとめたDiscord Embedを組み立てる。"""
    blocks = []
    location_data_list = []

    for zipcode, (status, payload) in zip(zip_codes, _fetch_all_location_data(zip_codes)):
        if status == "ok":
            location_data_list.append(payload)
            blocks.append(build_location_block(payload))
        else:
            print(f"[WARN] failed to build report for zipcode={zipcode}: {payload}", file=sys.stderr)
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
