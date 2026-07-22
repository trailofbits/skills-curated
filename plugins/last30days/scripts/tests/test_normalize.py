"""Tests for lib.normalize module."""

from lib import normalize, schema


class TestFilterByDateRange:
    def _reddit(self, date=None):
        return schema.RedditItem(
            id="r1",
            title="Test",
            url="",
            subreddit="test",
            date=date,
        )

    def test_in_range_kept(self):
        items = [self._reddit("2026-01-15")]
        result = normalize.filter_by_date_range(items, "2026-01-01", "2026-01-31")
        assert len(result) == 1

    def test_before_range_excluded(self):
        items = [self._reddit("2025-12-15")]
        result = normalize.filter_by_date_range(items, "2026-01-01", "2026-01-31")
        assert len(result) == 0

    def test_after_range_excluded(self):
        items = [self._reddit("2026-02-15")]
        result = normalize.filter_by_date_range(items, "2026-01-01", "2026-01-31")
        assert len(result) == 0

    def test_on_boundary_start_kept(self):
        items = [self._reddit("2026-01-01")]
        result = normalize.filter_by_date_range(items, "2026-01-01", "2026-01-31")
        assert len(result) == 1

    def test_on_boundary_end_kept(self):
        items = [self._reddit("2026-01-31")]
        result = normalize.filter_by_date_range(items, "2026-01-01", "2026-01-31")
        assert len(result) == 1

    def test_none_date_kept_by_default(self):
        items = [self._reddit(None)]
        result = normalize.filter_by_date_range(items, "2026-01-01", "2026-01-31")
        assert len(result) == 1

    def test_none_date_excluded_when_required(self):
        items = [self._reddit(None)]
        result = normalize.filter_by_date_range(
            items,
            "2026-01-01",
            "2026-01-31",
            require_date=True,
        )
        assert len(result) == 0

    def test_mixed_items(self):
        items = [
            self._reddit("2026-01-15"),  # in range
            self._reddit("2025-06-01"),  # too old
            self._reddit(None),  # no date
            self._reddit("2026-01-20"),  # in range
        ]
        result = normalize.filter_by_date_range(items, "2026-01-01", "2026-01-31")
        assert len(result) == 3  # 2 in range + 1 no date

    def test_empty_list(self):
        assert normalize.filter_by_date_range([], "2026-01-01", "2026-01-31") == []


class TestNormalizeRedditItems:
    def test_basic_normalization(self):
        raw = [
            {
                "id": "abc123",
                "title": "Test Post",
                "url": "https://reddit.com/r/test/abc123",
                "subreddit": "test",
                "date": "2026-01-15",
                "relevance": 0.9,
                "why_relevant": "Very relevant",
                "engagement": {"score": 100, "num_comments": 50, "upvote_ratio": 0.95},
                "top_comments": [
                    {
                        "score": 42,
                        "date": "2026-01-15",
                        "author": "commenter",
                        "excerpt": "Great post",
                        "url": "https://reddit.com/r/test/abc123/comment",
                    },
                ],
            },
        ]
        result = normalize.normalize_reddit_items(raw, "2026-01-01", "2026-01-31")
        assert len(result) == 1
        item = result[0]
        assert isinstance(item, schema.RedditItem)
        assert item.id == "abc123"
        assert item.title == "Test Post"
        assert item.relevance == 0.9
        assert item.engagement.score == 100
        assert len(item.top_comments) == 1
        assert item.date_confidence == "high"

    def test_missing_fields_use_defaults(self):
        raw = [{"id": "x"}]
        result = normalize.normalize_reddit_items(raw, "2026-01-01", "2026-01-31")
        assert result[0].title == ""
        assert result[0].relevance == 0.5
        assert result[0].engagement is None

    def test_empty_list(self):
        assert normalize.normalize_reddit_items([], "2026-01-01", "2026-01-31") == []


class TestNormalizeXItems:
    def test_basic_normalization(self):
        raw = [
            {
                "id": "tweet1",
                "text": "Test tweet about AI",
                "url": "https://x.com/user/tweet1",
                "author_handle": "testuser",
                "date": "2026-01-15",
                "relevance": 0.85,
                "why_relevant": "On topic",
                "engagement": {"likes": 500, "reposts": 50, "replies": 20, "quotes": 5},
            },
        ]
        result = normalize.normalize_x_items(raw, "2026-01-01", "2026-01-31")
        assert len(result) == 1
        item = result[0]
        assert isinstance(item, schema.XItem)
        assert item.text == "Test tweet about AI"
        assert item.engagement.likes == 500
        assert item.date_confidence == "high"

    def test_missing_engagement(self):
        raw = [{"id": "t1", "text": "No engagement"}]
        result = normalize.normalize_x_items(raw, "2026-01-01", "2026-01-31")
        assert result[0].engagement is None


class TestNormalizeYoutubeItems:
    def test_basic_normalization(self):
        raw = [
            {
                "video_id": "dQw4w9WgXcQ",
                "title": "AI Tutorial",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                "channel_name": "TechChannel",
                "date": "2026-01-15",
                "relevance": 0.9,
                "engagement": {"views": 50000, "likes": 1000, "comments": 100},
                "transcript_snippet": "Today we'll learn about...",
            },
        ]
        result = normalize.normalize_youtube_items(raw, "2026-01-01", "2026-01-31")
        assert len(result) == 1
        item = result[0]
        assert isinstance(item, schema.YouTubeItem)
        assert item.id == "dQw4w9WgXcQ"
        assert item.channel_name == "TechChannel"
        assert item.engagement.views == 50000
        assert item.date_confidence == "high"  # YouTube always high


class TestItemsToDicts:
    def test_reddit_roundtrip(self):
        items = [
            schema.RedditItem(
                id="r1",
                title="Test",
                url="https://reddit.com/r/test/r1",
                subreddit="test",
                date="2026-01-15",
                relevance=0.8,
            ),
        ]
        dicts = normalize.items_to_dicts(items)
        assert len(dicts) == 1
        assert dicts[0]["id"] == "r1"
        assert dicts[0]["title"] == "Test"
        assert dicts[0]["relevance"] == 0.8
