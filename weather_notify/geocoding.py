"""郵便番号から緯度経度を求めるためのAPI呼び出し。

    1. zipcloud API        : 郵便番号 -> 住所（都道府県・市区町村・町域）
    2. 国土地理院 地名検索API : 住所      -> 緯度経度
"""

import requests

from .config import REQUEST_TIMEOUT

ZIPCLOUD_URL = "https://zipcloud.ibsnet.co.jp/api/search"
GSI_ADDRESS_SEARCH_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"


def get_address_from_zipcode(zipcode):
    """zipcloud APIで郵便番号から住所（都道府県・市区町村・町域）を取得する。"""
    resp = requests.get(ZIPCLOUD_URL, params={"zipcode": zipcode}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != 200 or not data.get("results"):
        message = data.get("message") or "該当する住所が見つかりませんでした"
        raise ValueError(f"zipcloud lookup failed for {zipcode}: {message}")

    result = data["results"][0]
    # .get(key, "") はキー自体が無い場合しかフォールバックしないため、
    # zipcloudが値をnullで返すケース（町域情報が無い郵便番号など）を
    # 取りこぼさないよう `or ""` で明示的にNoneも空文字へ変換する。
    pref = result.get("address1") or ""
    city = result.get("address2") or ""
    town = result.get("address3") or ""
    full_address = f"{pref}{city}{town}"
    # 通知に出す地名は市区町村（例: 渋谷区 / 大阪市）を優先する
    display_name = city or full_address

    return {"full_address": full_address, "display_name": display_name}


def get_coordinates_from_address(address):
    """国土地理院 地名検索APIで住所から緯度経度を取得する。"""
    headers = {"User-Agent": "weather-notify-bot/1.0"}
    resp = requests.get(
        GSI_ADDRESS_SEARCH_URL,
        params={"q": address},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json()

    if not results:
        raise ValueError(f"GSI address search returned no results for: {address}")

    # geometry.coordinates は [経度, 緯度] の順
    lon, lat = results[0]["geometry"]["coordinates"]
    return {"lat": lat, "lon": lon}
