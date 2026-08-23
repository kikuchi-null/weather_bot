"""weather_notify.forecast のテスト。

geocoding / weather はこのモジュールの外側の関心事なのでモックし、
「取得した値をどう組み合わせるか」というforecast.py自身のロジックだけを検証する。
"""

import pytest

from weather_notify import forecast


def test_build_location_data_combines_geocoding_and_weather(mocker):
    mocker.patch(
        "weather_notify.forecast.geocoding.get_address_from_zipcode",
        return_value={"full_address": "東京都渋谷区神南", "display_name": "渋谷区"},
    )
    mocker.patch(
        "weather_notify.forecast.geocoding.get_coordinates_from_address",
        return_value={"lat": 35.6598, "lon": 139.7016},
    )
    mocker.patch(
        "weather_notify.forecast.weather.get_weather",
        return_value={
            "weathercode": 61,
            "temp_max": 24.0,
            "temp_min": 18.0,
            "precipitation_probability": 80,
        },
    )

    result = forecast.build_location_data("1500041")

    assert result == {
        "display_name": "渋谷区",
        "weathercode": 61,
        "weather_text": "雨",
        "weather_emoji": "🌧️",
        "temp_max": 24.0,
        "temp_min": 18.0,
        "umbrella": "必要(最高降水確率: 80%)",
        "advice": "羽織るものがあると安心です",
    }


def test_build_location_data_passes_full_address_to_coordinate_lookup(mocker):
    mocker.patch(
        "weather_notify.forecast.geocoding.get_address_from_zipcode",
        return_value={"full_address": "大阪府大阪市北区", "display_name": "大阪市北区"},
    )
    get_coordinates = mocker.patch(
        "weather_notify.forecast.geocoding.get_coordinates_from_address",
        return_value={"lat": 34.6937, "lon": 135.5023},
    )
    mocker.patch(
        "weather_notify.forecast.weather.get_weather",
        return_value={
            "weathercode": 0,
            "temp_max": 33.0,
            "temp_min": 26.0,
            "precipitation_probability": 0,
        },
    )

    forecast.build_location_data("5300001")

    get_coordinates.assert_called_once_with("大阪府大阪市北区")


def test_build_location_data_propagates_errors(mocker):
    mocker.patch(
        "weather_notify.forecast.geocoding.get_address_from_zipcode",
        side_effect=ValueError("zipcloud lookup failed"),
    )

    with pytest.raises(ValueError, match="zipcloud lookup failed"):
        forecast.build_location_data("0000000")
