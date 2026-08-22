"""weather_notify.config のテスト。"""

from weather_notify import config


class TestGetWebhookUrl:
    def test_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/xxx/yyy")
        assert config.get_webhook_url() == "https://discord.com/api/webhooks/xxx/yyy"

    def test_returns_none_when_unset(self):
        assert config.get_webhook_url() is None


class TestGetZipCodes:
    def test_parses_comma_separated_values(self, monkeypatch):
        monkeypatch.setenv("ZIP_CODES", "1500002,5300001")
        assert config.get_zip_codes() == ["1500002", "5300001"]

    def test_strips_whitespace_around_values(self, monkeypatch):
        monkeypatch.setenv("ZIP_CODES", " 1500002 , 5300001 ")
        assert config.get_zip_codes() == ["1500002", "5300001"]

    def test_removes_hyphens(self, monkeypatch):
        monkeypatch.setenv("ZIP_CODES", "150-0002,530-0001")
        assert config.get_zip_codes() == ["1500002", "5300001"]

    def test_ignores_empty_entries_from_trailing_comma(self, monkeypatch):
        monkeypatch.setenv("ZIP_CODES", "1500002,,5300001,")
        assert config.get_zip_codes() == ["1500002", "5300001"]

    def test_returns_empty_list_when_unset(self):
        assert config.get_zip_codes() == []

    def test_returns_empty_list_when_blank(self, monkeypatch):
        monkeypatch.setenv("ZIP_CODES", "   ")
        assert config.get_zip_codes() == []
