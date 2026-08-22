"""weather_notify.geocoding のテスト（zipcloud / 国土地理院APIをモック）。"""

import pytest

from weather_notify import geocoding


class TestGetAddressFromZipcode:
    def test_success_prefers_city_as_display_name(self, requests_mock):
        requests_mock.get(
            geocoding.ZIPCLOUD_URL,
            json={
                "status": 200,
                "message": None,
                "results": [
                    {
                        "address1": "東京都",
                        "address2": "渋谷区",
                        "address3": "神南",
                    }
                ],
            },
        )

        result = geocoding.get_address_from_zipcode("1500041")

        assert result == {
            "full_address": "東京都渋谷区神南",
            "display_name": "渋谷区",
        }

    def test_falls_back_to_full_address_when_city_missing(self, requests_mock):
        requests_mock.get(
            geocoding.ZIPCLOUD_URL,
            json={
                "status": 200,
                "results": [{"address1": "東京都", "address2": "", "address3": ""}],
            },
        )

        result = geocoding.get_address_from_zipcode("1000001")

        assert result["display_name"] == "東京都"

    def test_treats_explicit_null_fields_as_empty_string(self, requests_mock):
        # zipcloudは町域情報が無い郵便番号に対して、キー自体を省略するのではなく
        # 値をnullで返すことがある。.get(key, "")はこのケースを拾えないため、
        # "東京都None"のような文字列が組み立てられないことを確認する。
        requests_mock.get(
            geocoding.ZIPCLOUD_URL,
            json={
                "status": 200,
                "results": [{"address1": "東京都", "address2": None, "address3": None}],
            },
        )

        result = geocoding.get_address_from_zipcode("1000001")

        assert result == {"full_address": "東京都", "display_name": "東京都"}
        assert "None" not in result["full_address"]

    def test_raises_when_status_is_not_200(self, requests_mock):
        requests_mock.get(
            geocoding.ZIPCLOUD_URL,
            json={"status": 400, "message": "郵便番号の形式が違います", "results": None},
        )

        with pytest.raises(ValueError, match="郵便番号の形式が違います"):
            geocoding.get_address_from_zipcode("invalid")

    def test_raises_when_results_empty(self, requests_mock):
        requests_mock.get(
            geocoding.ZIPCLOUD_URL,
            json={"status": 200, "results": []},
        )

        with pytest.raises(ValueError):
            geocoding.get_address_from_zipcode("9999999")


class TestGetCoordinatesFromAddress:
    def test_success_parses_lon_lat_order_correctly(self, requests_mock):
        # geometry.coordinates は [経度, 緯度] の順で返ってくる
        requests_mock.get(
            geocoding.GSI_ADDRESS_SEARCH_URL,
            json=[
                {
                    "geometry": {"coordinates": [139.7016, 35.6598]},
                    "properties": {"title": "神南"},
                }
            ],
        )

        result = geocoding.get_coordinates_from_address("東京都渋谷区神南")

        assert result == {"lat": 35.6598, "lon": 139.7016}

    def test_raises_when_no_results(self, requests_mock):
        requests_mock.get(geocoding.GSI_ADDRESS_SEARCH_URL, json=[])

        with pytest.raises(ValueError):
            geocoding.get_coordinates_from_address("存在しない住所")
