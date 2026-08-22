"""緯度経度から天気予報を取得し、天気コードの日本語化や各種判定を行うモジュール。"""

import requests

from .config import REQUEST_TIMEOUT

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes -> (日本語表現, 絵文字)
WEATHER_CODE_MAP = {
    0: ("快晴", "☀️"),
    1: ("晴れ", "☀️"),
    2: ("晴れ時々曇り", "🌤️"),
    3: ("曇り", "☁️"),
    45: ("霧", "🌫️"),
    48: ("霧", "🌫️"),
    51: ("小雨", "🌦️"),
    53: ("小雨", "🌦️"),
    55: ("小雨", "🌦️"),
    56: ("着氷性の霧雨", "🌦️"),
    57: ("着氷性の霧雨", "🌦️"),
    61: ("雨", "🌧️"),
    63: ("雨", "🌧️"),
    65: ("強い雨", "🌧️"),
    66: ("着氷性の雨", "🌧️"),
    67: ("着氷性の雨", "🌧️"),
    71: ("雪", "❄️"),
    73: ("雪", "❄️"),
    75: ("強い雪", "❄️"),
    77: ("雪", "❄️"),
    80: ("にわか雨", "🌦️"),
    81: ("にわか雨", "🌦️"),
    82: ("激しいにわか雨", "🌧️"),
    85: ("にわか雪", "🌨️"),
    86: ("にわか雪", "🌨️"),
    95: ("雷雨", "⛈️"),
    96: ("雷雨（ひょうを伴う）", "⛈️"),
    99: ("雷雨（ひょうを伴う）", "⛈️"),
}

# 傘が必要と判断する天気コード（雨・雪・雷雨系）
RAINY_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}

# 「全地点が晴れ」とみなすweathercode（Discord Embedの帯色判定に利用）
SUNNY_CODES = {0, 1}


def get_weather(lat, lon):
    """Open-Meteo APIで当日の天気予報（最高/最低気温・天気・降水確率）を取得する。"""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Asia/Tokyo",
        "forecast_days": 1,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    daily = data["daily"]
    return {
        "weathercode": daily["weathercode"][0],
        "temp_max": daily["temperature_2m_max"][0],
        "temp_min": daily["temperature_2m_min"][0],
        "precipitation_probability": daily.get("precipitation_probability_max", [None])[0],
    }


def weathercode_to_japanese(code):
    """weathercodeを日本語表現と絵文字に変換する。"""
    return WEATHER_CODE_MAP.get(code, ("不明", "❓"))


def judge_umbrella(precipitation_probability, weathercode):
    """降水確率とweathercodeから傘の要否を判定する。"""
    is_rainy_code = weathercode in RAINY_CODES
    is_high_probability = precipitation_probability is not None and precipitation_probability >= 50

    if is_rainy_code or is_high_probability:
        return "必要"
    return "不要"


def clothing_advice(temp_max):
    """最高気温から服装のアドバイスを一言で返す。"""
    if temp_max >= 28:
        return "半袖で快適です"
    if temp_max >= 25:
        return "半袖でも快適に過ごせます"
    if temp_max >= 20:
        return "羽織るものがあると安心です"
    if temp_max >= 15:
        return "長袖が欲しくなる気温です"
    if temp_max >= 10:
        return "しっかりした上着が必要です"
    return "防寒対策をしっかりと"
