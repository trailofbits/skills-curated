"""Tests for lib.dedupe module."""

from lib import dedupe, schema


class TestNormalizeText:
    def test_lowercase(self):
        assert dedupe.normalize_text("Hello World") == "hello world"

    def test_remove_punctuation(self):
        assert dedupe.normalize_text("hello, world!") == "hello world"

    def test_collapse_whitespace(self):
        assert dedupe.normalize_text("hello   world") == "hello world"

    def test_combined(self):
        assert dedupe.normalize_text("  Hello,  World!  ") == "hello world"

    def test_empty(self):
        assert dedupe.normalize_text("") == ""


class TestGetNgrams:
    def test_basic(self):
        ngrams = dedupe.get_ngrams("hello")
        # "hello" normalized -> "hello", 3-grams: hel, ell, llo
        assert "hel" in ngrams
        assert "ell" in ngrams
        assert "llo" in ngrams
        assert len(ngrams) == 3

    def test_short_text(self):
        ngrams = dedupe.get_ngrams("hi")
        assert ngrams == {"hi"}

    def test_single_char(self):
        ngrams = dedupe.get_ngrams("a")
        assert ngrams == {"a"}


class TestJaccardSimilarity:
    def test_identical_sets(self):
        s = {"a", "b", "c"}
        assert dedupe.jaccard_similarity(s, s) == 1.0

    def test_disjoint_sets(self):
        assert dedupe.jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        result = dedupe.jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert result == 2 / 4  # intersection=2, union=4

    def test_empty_sets(self):
        assert dedupe.jaccard_similarity(set(), set()) == 0.0

    def test_one_empty(self):
        assert dedupe.jaccard_similarity({"a"}, set()) == 0.0


class TestFindDuplicates:
    def _reddit(self, title, score=50):
        return schema.RedditItem(
            id="r1",
            title=title,
            url="",
            subreddit="test",
            score=score,
        )

    def test_exact_duplicates(self):
        items = [self._reddit("Best AI tools 2026"), self._reddit("Best AI tools 2026")]
        pairs = dedupe.find_duplicates(items)
        assert len(pairs) == 1
        assert pairs[0] == (0, 1)

    def test_near_duplicates(self):
        items = [
            self._reddit("Best AI tools for coding in 2026"),
            self._reddit("Best AI tools for coding 2026"),
        ]
        pairs = dedupe.find_duplicates(items, threshold=0.7)
        assert len(pairs) == 1

    def test_different_items(self):
        items = [
            self._reddit("Best AI tools for coding"),
            self._reddit("How to make sourdough bread"),
        ]
        pairs = dedupe.find_duplicates(items)
        assert len(pairs) == 0

    def test_empty_list(self):
        assert dedupe.find_duplicates([]) == []

    def test_single_item(self):
        assert dedupe.find_duplicates([self._reddit("test")]) == []


class TestDedupeItems:
    def _reddit(self, title, score=50):
        return schema.RedditItem(
            id="r1",
            title=title,
            url="",
            subreddit="test",
            score=score,
        )

    def test_keeps_higher_scored(self):
        items = [
            self._reddit("Best AI tools 2026", score=90),
            self._reddit("Best AI tools 2026", score=50),
        ]
        result = dedupe.dedupe_items(items)
        assert len(result) == 1
        assert result[0].score == 90

    def test_no_duplicates_unchanged(self):
        items = [
            self._reddit("Best AI tools", score=90),
            self._reddit("Sourdough bread recipe", score=80),
        ]
        result = dedupe.dedupe_items(items)
        assert len(result) == 2

    def test_empty_list(self):
        assert dedupe.dedupe_items([]) == []

    def test_single_item(self):
        items = [self._reddit("test")]
        assert dedupe.dedupe_items(items) == items

    def test_three_duplicates_keeps_one(self):
        items = [
            self._reddit("Best AI tools 2026", score=90),
            self._reddit("Best AI tools 2026", score=70),
            self._reddit("Best AI tools 2026", score=50),
        ]
        result = dedupe.dedupe_items(items)
        assert len(result) == 1
        assert result[0].score == 90

    def test_custom_threshold(self):
        items = [
            self._reddit("Best AI tools for coding in 2026"),
            self._reddit("Best AI tools for coding 2026"),
        ]
        # High threshold: not considered duplicates
        result_strict = dedupe.dedupe_items(items, threshold=0.99)
        assert len(result_strict) == 2

        # Low threshold: considered duplicates
        result_loose = dedupe.dedupe_items(items, threshold=0.5)
        assert len(result_loose) == 1


class TestDedupeX:
    def test_dedupes_x_items(self):
        items = [
            schema.XItem(
                id="1",
                text="Claude Code is amazing",
                url="",
                author_handle="a",
                score=90,
            ),
            schema.XItem(
                id="2",
                text="Claude Code is amazing!",
                url="",
                author_handle="b",
                score=50,
            ),
        ]
        result = dedupe.dedupe_x(items)
        assert len(result) == 1
        assert result[0].score == 90


class TestDedupeYoutube:
    def test_dedupes_youtube_items(self):
        items = [
            schema.YouTubeItem(
                id="v1",
                title="Claude Code Tutorial",
                url="",
                channel_name="TechChannel",
                score=90,
            ),
            schema.YouTubeItem(
                id="v2",
                title="Claude Code Tutorial",
                url="",
                channel_name="TechChannel",
                score=50,
            ),
        ]
        result = dedupe.dedupe_youtube(items)
        assert len(result) == 1
        assert result[0].score == 90
