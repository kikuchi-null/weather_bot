"""weather_notify.weather のテスト（Open-Meteo APIのモック、および純粋な判定ロジック）。"""

import pytest

from weather_notify import weather


class TestGetWeather:
    def test_parses_daily_forecast_fields(self, requests_mock):
        requests_mock.get(
            weather.OPEN_METEO_URL,
            json={
                "daily": {
                    "weathercode": [61],
                    "temperature_2m_max": [24.4],
                    "temperature_2m_min": [18.2],
                    "precipitation_probability_max": [80],
                }
            },
        )

        result = weather.get_weather(35.6598, 139.7016)

        assert result == {
            "weathercode": 61,
            "temp_max": 24.4,
            "temp_min": 18.2,
            "precipitation_probability": 80,
        }

    def test_precipitation_probability_defaults_to_none_when_missing(self, requests_mock):
        requests_mock.get(
            weather.OPEN_METEO_URL,
            json={
                "daily": {
                    "weathercode": [0],
                    "temperature_2m_max": [30.0],
                    "temperature_2m_min": [22.0],
                }
            },
        )

        result = weather.get_weather(35.0, 135.0)

        assert result["precipitation_probability"] is None


class TestWeathercodeToJapanese:
    @pytest.mark.parametrize(
        "code, expected_text, expected_emoji",
        [
            (0, "快晴", "☀️"),
            (2, "晴れ時々曇り", "🌤️"),
            (61, "雨", "🌧️"),
            (95, "雷雨", "⛈️"),
        ],
    )
    def test_known_codes(self, code, expected_text, expected_emoji):
        assert weather.weathercode_to_japanese(code) == (expected_text, expected_emoji)

    def test_unknown_code_falls_back(self):
        assert weather.weathercode_to_japanese(9999) == ("不明", "❓")


class TestJudgeUmbrella:
    def test_not_needed_when_sunny_and_low_probability(self):
        assert weather.judge_umbrella(10, 0) == "不要"

    def test_needed_when_weathercode_is_rainy_even_with_low_probability(self):
        assert weather.judge_umbrella(5, 61) == "必要"

    def test_needed_when_probability_is_high_even_if_code_is_cloudy(self):
        assert weather.judge_umbrella(50, 3) == "必要"

    def test_not_needed_when_probability_just_below_threshold(self):
        assert weather.judge_umbrella(49, 3) == "不要"

    def test_not_needed_when_probability_is_none(self):
        assert weather.judge_umbrella(None, 3) == "不要"


class TestClothingAdvice:
    @pytest.mark.parametrize(
        "temp_max, expected",
        [
            (28, "半袖で快適です"),
            (30, "半袖で快適です"),
            (27, "半袖でも快適に過ごせます"),
            (25, "半袖でも快適に過ごせます"),
            (24, "羽織るものがあると安心です"),
            (20, "羽織るものがあると安心です"),
            (19, "長袖が欲しくなる気温です"),
            (15, "長袖が欲しくなる気温です"),
            (14, "しっかりした上着が必要です"),
            (10, "しっかりした上着が必要です"),
            (9, "防寒対策をしっかりと"),
            (-5, "防寒対策をしっかりと"),
        ],
    )
    def test_temperature_bands(self, temp_max, expected):
        assert weather.clothing_advice(temp_max) == expected
