"""Tests for lib.dates module."""

from datetime import UTC, datetime, timedelta

from lib import dates


class TestGetDateRange:
    def test_default_30_days(self):
        from_date, to_date = dates.get_date_range()
        today = datetime.now(UTC).date()
        assert to_date == today.isoformat()
        expected_from = (today - timedelta(days=30)).isoformat()
        assert from_date == expected_from

    def test_custom_days(self):
        from_date, to_date = dates.get_date_range(7)
        today = datetime.now(UTC).date()
        expected_from = (today - timedelta(days=7)).isoformat()
        assert from_date == expected_from
        assert to_date == today.isoformat()

    def test_one_day(self):
        from_date, to_date = dates.get_date_range(1)
        today = datetime.now(UTC).date()
        yesterday = (today - timedelta(days=1)).isoformat()
        assert from_date == yesterday
        assert to_date == today.isoformat()


class TestParseDate:
    def test_yyyy_mm_dd(self):
        result = dates.parse_date("2026-01-15")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_iso_with_time(self):
        result = dates.parse_date("2026-01-15T10:30:00Z")
        assert result.year == 2026
        assert result.hour == 10

    def test_unix_timestamp(self):
        result = dates.parse_date("1700000000")
        assert result is not None
        assert result.year == 2023

    def test_none_input(self):
        assert dates.parse_date(None) is None

    def test_empty_string(self):
        assert dates.parse_date("") is None

    def test_garbage_input(self):
        assert dates.parse_date("not-a-date") is None


class TestTimestampToDate:
    def test_valid_timestamp(self):
        # 2023-11-14 in UTC
        result = dates.timestamp_to_date(1700000000)
        assert result == "2023-11-14"

    def test_none(self):
        assert dates.timestamp_to_date(None) is None

    def test_zero(self):
        result = dates.timestamp_to_date(0)
        assert result == "1970-01-01"


class TestGetDateConfidence:
    def test_in_range_is_high(self):
        assert dates.get_date_confidence("2026-01-15", "2026-01-01", "2026-01-31") == "high"

    def test_on_boundary_start_is_high(self):
        assert dates.get_date_confidence("2026-01-01", "2026-01-01", "2026-01-31") == "high"

    def test_on_boundary_end_is_high(self):
        assert dates.get_date_confidence("2026-01-31", "2026-01-01", "2026-01-31") == "high"

    def test_before_range_is_low(self):
        assert dates.get_date_confidence("2025-12-31", "2026-01-01", "2026-01-31") == "low"

    def test_after_range_is_low(self):
        assert dates.get_date_confidence("2026-02-01", "2026-01-01", "2026-01-31") == "low"

    def test_none_is_low(self):
        assert dates.get_date_confidence(None, "2026-01-01", "2026-01-31") == "low"

    def test_invalid_format_is_low(self):
        assert dates.get_date_confidence("garbage", "2026-01-01", "2026-01-31") == "low"


class TestDaysAgo:
    def test_today_is_zero(self):
        today = datetime.now(UTC).date().isoformat()
        assert dates.days_ago(today) == 0

    def test_yesterday(self):
        yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        assert dates.days_ago(yesterday) == 1

    def test_none(self):
        assert dates.days_ago(None) is None

    def test_invalid(self):
        assert dates.days_ago("not-a-date") is None


class TestRecencyScore:
    def test_today_is_100(self):
        today = datetime.now(UTC).date().isoformat()
        assert dates.recency_score(today) == 100

    def test_max_days_ago_is_zero(self):
        old = (datetime.now(UTC).date() - timedelta(days=30)).isoformat()
        assert dates.recency_score(old) == 0

    def test_half_max_is_about_50(self):
        half = (datetime.now(UTC).date() - timedelta(days=15)).isoformat()
        assert dates.recency_score(half) == 50

    def test_none_is_zero(self):
        assert dates.recency_score(None) == 0

    def test_future_date_is_100(self):
        future = (datetime.now(UTC).date() + timedelta(days=5)).isoformat()
        assert dates.recency_score(future) == 100

    def test_custom_max_days(self):
        one_week_ago = (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
        assert dates.recency_score(one_week_ago, max_days=7) == 0
        assert dates.recency_score(one_week_ago, max_days=14) == 50
