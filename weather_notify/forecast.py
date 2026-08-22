"""郵便番号1件分の「住所取得 -> 座標取得 -> 天気取得 -> 判定」を束ねるオーケストレーション層。

geocoding / weather はそれぞれ外部APIとの単純なやり取りだけに専念させ、
このモジュールが両者を組み合わせて「1地点分の通知用データ」を作る。
"""

from . import geocoding
from . import weather


def build_location_data(zipcode):
    """1つの郵便番号から、通知に必要な情報一式を取得して返す。"""
    address = geocoding.get_address_from_zipcode(zipcode)
    coords = geocoding.get_coordinates_from_address(address["full_address"])
    forecast = weather.get_weather(coords["lat"], coords["lon"])

    weather_text, weather_emoji = weather.weathercode_to_japanese(forecast["weathercode"])
    umbrella = weather.judge_umbrella(forecast["precipitation_probability"], forecast["weathercode"])
    advice = weather.clothing_advice(forecast["temp_max"])

    return {
        "display_name": address["display_name"],
        "weathercode": forecast["weathercode"],
        "weather_text": weather_text,
        "weather_emoji": weather_emoji,
        "temp_max": forecast["temp_max"],
        "temp_min": forecast["temp_min"],
        "umbrella": umbrella,
        "advice": advice,
    }
