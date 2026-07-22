"""Tests for lib.score module."""

import math
from datetime import UTC, datetime

from lib import schema, score


class TestLog1pSafe:
    def test_positive_value(self):
        assert score.log1p_safe(100) == math.log1p(100)

    def test_zero(self):
        assert score.log1p_safe(0) == 0.0

    def test_none(self):
        assert score.log1p_safe(None) == 0.0

    def test_negative(self):
        assert score.log1p_safe(-5) == 0.0


class TestNormalizeTo100:
    def test_two_values(self):
        result = score.normalize_to_100([0, 10])
        assert result == [0.0, 100.0]

    def test_three_values(self):
        result = score.normalize_to_100([0, 5, 10])
        assert result == [0.0, 50.0, 100.0]

    def test_all_same(self):
        result = score.normalize_to_100([5, 5, 5])
        assert result == [50, 50, 50]

    def test_with_none(self):
        result = score.normalize_to_100([0, None, 10])
        assert result[0] == 0.0
        assert result[1] is None
        assert result[2] == 100.0

    def test_all_none(self):
        result = score.normalize_to_100([None, None])
        assert result == [50, 50]

    def test_empty(self):
        assert score.normalize_to_100([]) == []

    def test_single_value(self):
        result = score.normalize_to_100([42])
        assert result == [50]  # Single value -> midpoint


class TestComputeRedditEngagementRaw:
    def test_typical_post(self):
        eng = schema.Engagement(score=100, num_comments=50, upvote_ratio=0.95)
        result = score.compute_reddit_engagement_raw(eng)
        assert result is not None
        assert result > 0

    def test_none_engagement(self):
        assert score.compute_reddit_engagement_raw(None) is None

    def test_no_metrics(self):
        eng = schema.Engagement()
        assert score.compute_reddit_engagement_raw(eng) is None

    def test_only_score(self):
        eng = schema.Engagement(score=100)
        result = score.compute_reddit_engagement_raw(eng)
        assert result is not None

    def test_higher_engagement_scores_higher(self):
        low = schema.Engagement(score=10, num_comments=5, upvote_ratio=0.8)
        high = schema.Engagement(score=1000, num_comments=500, upvote_ratio=0.95)
        assert score.compute_reddit_engagement_raw(high) > score.compute_reddit_engagement_raw(low)


class TestComputeXEngagementRaw:
    def test_typical_post(self):
        eng = schema.Engagement(likes=500, reposts=50, replies=20, quotes=5)
        result = score.compute_x_engagement_raw(eng)
        assert result is not None
        assert result > 0

    def test_none_engagement(self):
        assert score.compute_x_engagement_raw(None) is None

    def test_no_metrics(self):
        eng = schema.Engagement()
        assert score.compute_x_engagement_raw(eng) is None

    def test_higher_engagement_scores_higher(self):
        low = schema.Engagement(likes=10, reposts=1)
        high = schema.Engagement(likes=10000, reposts=1000)
        assert score.compute_x_engagement_raw(high) > score.compute_x_engagement_raw(low)


class TestComputeYoutubeEngagementRaw:
    def test_typical_video(self):
        eng = schema.Engagement(views=50000, likes=1000, num_comments=100)
        result = score.compute_youtube_engagement_raw(eng)
        assert result is not None
        assert result > 0

    def test_none_engagement(self):
        assert score.compute_youtube_engagement_raw(None) is None

    def test_views_dominate(self):
        high_views = schema.Engagement(views=1000000, likes=10)
        high_likes = schema.Engagement(views=100, likes=10000)
        # Views have 0.50 weight vs likes at 0.35, and log dampens large values,
        # but million views should still outweigh
        assert score.compute_youtube_engagement_raw(
            high_views
        ) > score.compute_youtube_engagement_raw(high_likes)


class TestScoreRedditItems:
    def _make_item(self, **kwargs):
        today = datetime.now(UTC).date().isoformat()
        defaults = {
            "id": "abc",
            "title": "Test post",
            "url": "https://reddit.com/r/test/abc",
            "subreddit": "test",
            "date": today,
            "date_confidence": "high",
            "relevance": 0.8,
            "engagement": schema.Engagement(score=100, num_comments=50, upvote_ratio=0.95),
        }
        defaults.update(kwargs)
        return schema.RedditItem(**defaults)

    def test_empty_list(self):
        assert score.score_reddit_items([]) == []

    def test_single_item_gets_score(self):
        item = self._make_item()
        result = score.score_reddit_items([item])
        assert result[0].score > 0
        assert result[0].score <= 100

    def test_score_is_int(self):
        item = self._make_item()
        result = score.score_reddit_items([item])
        assert isinstance(result[0].score, int)

    def test_subscores_populated(self):
        item = self._make_item()
        result = score.score_reddit_items([item])
        assert result[0].subs.relevance > 0
        assert result[0].subs.recency > 0

    def test_high_relevance_beats_low(self):
        high = self._make_item(relevance=0.95)
        low = self._make_item(relevance=0.1)
        scored = score.score_reddit_items([high, low])
        assert scored[0].score > scored[1].score

    def test_low_date_confidence_penalized(self):
        high_conf = self._make_item(date_confidence="high")
        low_conf = self._make_item(date_confidence="low")
        score.score_reddit_items([high_conf])
        score.score_reddit_items([low_conf])
        assert high_conf.score > low_conf.score

    def test_no_engagement_gets_normalized_default(self):
        """Single item with None engagement gets normalize_to_100 default (50)."""
        item = self._make_item(engagement=None)
        result = score.score_reddit_items([item])
        # normalize_to_100([None]) returns [50] as default
        assert result[0].subs.engagement == 50


class TestScoreXItems:
    def _make_item(self, **kwargs):
        today = datetime.now(UTC).date().isoformat()
        defaults = {
            "id": "123",
            "text": "Test tweet",
            "url": "https://x.com/user/123",
            "author_handle": "user",
            "date": today,
            "date_confidence": "high",
            "relevance": 0.8,
            "engagement": schema.Engagement(likes=500, reposts=50, replies=20),
        }
        defaults.update(kwargs)
        return schema.XItem(**defaults)

    def test_empty_list(self):
        assert score.score_x_items([]) == []

    def test_single_item_gets_score(self):
        item = self._make_item()
        result = score.score_x_items([item])
        assert 0 < result[0].score <= 100

    def test_high_engagement_beats_low(self):
        high = self._make_item(
            engagement=schema.Engagement(likes=10000, reposts=1000),
        )
        low = self._make_item(
            engagement=schema.Engagement(likes=5, reposts=0),
        )
        scored = score.score_x_items([high, low])
        assert scored[0].score > scored[1].score


class TestScoreWebSearchItems:
    def _make_item(self, **kwargs):
        today = datetime.now(UTC).date().isoformat()
        defaults = {
            "id": "w1",
            "title": "Test page",
            "url": "https://example.com/test",
            "source_domain": "example.com",
            "snippet": "A test page",
            "date": today,
            "date_confidence": "high",
            "relevance": 0.8,
        }
        defaults.update(kwargs)
        return schema.WebSearchItem(**defaults)

    def test_empty_list(self):
        assert score.score_websearch_items([]) == []

    def test_single_item_gets_score(self):
        item = self._make_item()
        result = score.score_websearch_items([item])
        assert result[0].score > 0

    def test_engagement_subscore_is_zero(self):
        item = self._make_item()
        score.score_websearch_items([item])
        assert item.subs.engagement == 0

    def test_high_confidence_bonus(self):
        high = self._make_item(date_confidence="high")
        low = self._make_item(date_confidence="low")
        score.score_websearch_items([high])
        score.score_websearch_items([low])
        assert high.score > low.score

    def test_source_penalty_applied(self):
        """WebSearch items get a 15-point source penalty."""
        item = self._make_item(relevance=0.8, date_confidence="high")
        score.score_websearch_items([item])
        # Without penalty: 0.55*80 + 0.45*100 + 10 (high bonus) = 44+45+10 = 99
        # With penalty: 99 - 15 = 84
        assert item.score == 84

    def test_web_lower_than_reddit_with_spread(self):
        """With engagement spread, Reddit high-engagement beats web."""
        today = datetime.now(UTC).date().isoformat()
        web = self._make_item(relevance=0.8, date=today, date_confidence="high")
        # Multiple Reddit items so engagement normalization creates a range
        reddit_high = schema.RedditItem(
            id="r1",
            title="High",
            url="",
            subreddit="test",
            date=today,
            date_confidence="high",
            relevance=0.8,
            engagement=schema.Engagement(score=1000, num_comments=500, upvote_ratio=0.95),
        )
        reddit_low = schema.RedditItem(
            id="r2",
            title="Low",
            url="",
            subreddit="test",
            date=today,
            date_confidence="high",
            relevance=0.8,
            engagement=schema.Engagement(score=1, num_comments=0, upvote_ratio=0.5),
        )
        score.score_websearch_items([web])
        score.score_reddit_items([reddit_high, reddit_low])
        assert reddit_high.score > web.score


class TestSortItems:
    def test_sorts_by_score_descending(self):
        a = schema.RedditItem(
            id="a",
            title="A",
            url="",
            subreddit="",
            score=90,
        )
        b = schema.RedditItem(
            id="b",
            title="B",
            url="",
            subreddit="",
            score=50,
        )
        result = score.sort_items([b, a])
        assert result[0].id == "a"
        assert result[1].id == "b"

    def test_tiebreak_by_date(self):
        a = schema.RedditItem(
            id="a",
            title="A",
            url="",
            subreddit="",
            score=80,
            date="2026-02-15",
        )
        b = schema.RedditItem(
            id="b",
            title="B",
            url="",
            subreddit="",
            score=80,
            date="2026-02-10",
        )
        result = score.sort_items([b, a])
        assert result[0].id == "a"  # More recent first

    def test_tiebreak_by_source_priority(self):
        reddit = schema.RedditItem(
            id="r",
            title="Same",
            url="",
            subreddit="",
            score=80,
            date="2026-02-15",
        )
        x = schema.XItem(
            id="x",
            text="Same",
            url="",
            author_handle="",
            score=80,
            date="2026-02-15",
        )
        result = score.sort_items([x, reddit])
        assert isinstance(result[0], schema.RedditItem)  # Reddit > X

    def test_empty_list(self):
        assert score.sort_items([]) == []

    def test_none_date_handled(self):
        a = schema.RedditItem(
            id="a",
            title="A",
            url="",
            subreddit="",
            score=80,
            date=None,
        )
        b = schema.RedditItem(
            id="b",
            title="B",
            url="",
            subreddit="",
            score=80,
            date="2026-02-15",
        )
        result = score.sort_items([a, b])
        assert result[0].id == "b"  # Dated item first
