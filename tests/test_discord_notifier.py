"""weather_notify.discord_notifier のテスト。"""

import pytest

from weather_notify import discord_notifier


def _location_data(
    display_name="渋谷区",
    weathercode=61,
    weather_text="雨",
    weather_emoji="🌧️",
    temp_max=24.0,
    temp_min=18.0,
    umbrella="必要",
    precipitation_probability=80,
    advice="羽織るものがあると安心です",
):
    return {
        "display_name": display_name,
        "weathercode": weathercode,
        "weather_text": weather_text,
        "weather_emoji": weather_emoji,
        "temp_max": temp_max,
        "temp_min": temp_min,
        "umbrella": umbrella,
        "umbrella_needed": umbrella == "必要",
        "precipitation_probability": precipitation_probability,
        "advice": advice,
    }


class TestBuildLocationBlock:
    def test_every_line_is_quoted(self):
        block = discord_notifier.build_location_block(_location_data())
        lines = block.split("\n")

        assert len(lines) == 5
        assert all(line.startswith("> ") for line in lines)

    def test_contains_expected_content(self):
        block = discord_notifier.build_location_block(_location_data())

        assert "📍 渋谷区" in block
        assert "🌧️ 雨" in block
        assert "🌡️ 気温: 🔺**24℃** / 🔻 **18℃**" in block
        assert "傘: **必要(最高降水確率: 80%)**" in block
        assert "服装: 羽織るものがあると安心です" in block

    def test_temperature_is_rounded_half_up_not_banker_rounded(self):
        # Python組み込みのround()だとround(24.5) == 24（偶数丸め）になってしまうため、
        # 24.5が25として表示される（四捨五入）ことを確認する。
        block = discord_notifier.build_location_block(_location_data(temp_max=24.5, temp_min=17.5))

        assert "🔺**25℃**" in block
        assert "🔻 **18℃**" in block


class TestRoundHalfUp:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (24.5, 25),
            (17.5, 18),
            (28.0, 28),
            (-0.5, -1),
            (-24.5, -25),
        ],
    )
    def test_rounds_ties_away_from_zero(self, value, expected):
        assert discord_notifier._round_half_up(value) == expected


class TestBuildErrorBlock:
    def test_every_line_is_quoted_and_mentions_zipcode(self):
        block = discord_notifier.build_error_block("0000000")
        lines = block.split("\n")

        assert all(line.startswith("> ") for line in lines)
        assert "0000000" in block
        assert "取得に失敗" in block


class TestDetermineEmbedColor:
    def test_rain_takes_priority_when_any_location_needs_umbrella(self):
        data = [
            _location_data(weathercode=0, umbrella="不要"),
            _location_data(weathercode=61, umbrella="必要"),
        ]
        assert discord_notifier.determine_embed_color(data) == discord_notifier.COLOR_RAIN

    def test_sunny_when_all_locations_are_sunny(self):
        data = [
            _location_data(weathercode=0, umbrella="不要"),
            _location_data(weathercode=1, umbrella="不要"),
        ]
        assert discord_notifier.determine_embed_color(data) == discord_notifier.COLOR_SUNNY

    def test_cloudy_when_neither_rainy_nor_all_sunny(self):
        data = [_location_data(weathercode=3, umbrella="不要")]
        assert discord_notifier.determine_embed_color(data) == discord_notifier.COLOR_CLOUDY

    def test_unknown_when_no_location_data(self):
        assert discord_notifier.determine_embed_color([]) == discord_notifier.COLOR_UNKNOWN


class TestBuildEmbed:
    def test_success_only(self, mocker):
        # build_location_data はThreadPoolExecutorで並列に呼び出されるため、
        # どのzipcodeが先に呼ばれるかは保証されない。呼び出し順に依存する
        # side_effect=[...]ではなく、引数(zipcode)で結果を引く関数にする。
        data_by_zipcode = {
            "1500041": _location_data(display_name="渋谷区", umbrella="必要"),
            "5300001": _location_data(display_name="大阪市北区", umbrella="不要", weathercode=0),
        }
        mocker.patch(
            "weather_notify.discord_notifier.build_location_data",
            side_effect=lambda zipcode: data_by_zipcode[zipcode],
        )

        embed = discord_notifier.build_embed(["1500041", "5300001"])

        assert embed["title"] == "🌤️ 今日の天気予報"
        assert "対象 2地点" in embed["description"]
        assert "取得失敗" not in embed["description"]
        assert "傘が必要な地点: **1 / 2**" in embed["description"]
        assert "📍 渋谷区" in embed["description"]
        assert "📍 大阪市北区" in embed["description"]
        # 地点ブロック同士が空行で区切られていること
        assert "\n\n" in embed["description"]
        # 並列実行の完了順によらず、zip_codesで渡した順序どおりに並ぶこと
        assert embed["description"].index("渋谷区") < embed["description"].index("大阪市北区")
        assert embed["color"] == discord_notifier.COLOR_RAIN
        assert embed["footer"] == {"text": "Data by Open-Meteo"}
        assert "timestamp" in embed

    def test_partial_failure_is_reported_without_raising(self, mocker):
        def fake_build_location_data(zipcode):
            if zipcode == "0000000":
                raise ValueError("zipcloud lookup failed")
            return _location_data(display_name="渋谷区")

        mocker.patch(
            "weather_notify.discord_notifier.build_location_data",
            side_effect=fake_build_location_data,
        )

        embed = discord_notifier.build_embed(["1500041", "0000000"])

        assert "⚠️ 1件取得失敗" in embed["description"]
        assert "取得に失敗しました" in embed["description"]
        # 失敗地点を除いた「取得できた地点数」を分母にする
        assert "傘が必要な地点: **1 / 1**" in embed["description"]

    def test_all_failed(self, mocker):
        mocker.patch(
            "weather_notify.discord_notifier.build_location_data",
            side_effect=ValueError("zipcloud lookup failed"),
        )

        embed = discord_notifier.build_embed(["0000000"])

        assert embed["color"] == discord_notifier.COLOR_UNKNOWN
        assert "傘が必要な地点" not in embed["description"]


class TestSendDiscord:
    def test_posts_embed_as_single_request(self, requests_mock):
        webhook_url = "https://discord.com/api/webhooks/xxx/yyy"
        requests_mock.post(webhook_url, status_code=204)

        embed = {"title": "test"}
        discord_notifier.send_discord(webhook_url, embed)

        assert requests_mock.call_count == 1
        assert requests_mock.last_request.json() == {"embeds": [embed]}

    def test_raises_on_http_error(self, requests_mock):
        webhook_url = "https://discord.com/api/webhooks/xxx/yyy"
        requests_mock.post(webhook_url, status_code=404)

        with pytest.raises(Exception):
            discord_notifier.send_discord(webhook_url, {"title": "test"})
