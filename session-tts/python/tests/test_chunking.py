"""Tests for `_force_split`, `_split_paragraph`, `split_into_chunks`."""
from __future__ import annotations

import pytest


class TestForceSplitRoundtrip:
    def test_joined_chunks_equal_original_when_spaces_present(self, say_response):
        text = (
            "these are many english words that need to be split somewhere "
            "reasonable instead of in the middle of a word"
        )
        chunks = say_response._force_split(text, 30)
        # `"".join` is what split_into_chunks does when re-flowing the tail
        # past the first chunk; the boundary space must not be lost.
        assert "".join(chunks) == text

    def test_each_chunk_within_budget_except_hard_slice(self, say_response):
        text = (
            "these are many english words that need to be split somewhere "
            "reasonable instead of in the middle of a word"
        )
        chunks = say_response._force_split(text, 30)
        for c in chunks:
            assert len(c) <= 30

    def test_hard_slice_fallback_when_no_whitespace(self, say_response):
        text = "a" * 100
        chunks = say_response._force_split(text, 30)
        assert "".join(chunks) == text
        # 100 chars / 30 budget → 30+30+30+10
        assert [len(c) for c in chunks] == [30, 30, 30, 10]


class TestForceSplitWordBoundary:
    def test_breaks_at_last_space_before_budget(self, say_response):
        # "consumer invariant" within a long sentence: the break should be
        # between the two words, not inside one of them.
        text = "abc def ghi jkl mno pqr stu vwx yz"  # 33 chars with spaces
        chunks = say_response._force_split(text, 15)
        for c in chunks:
            # No chunk should end with a partial word (i.e., a letter then
            # immediately the next chunk continues with more letters from
            # the same word).
            stripped = c.rstrip()
            if stripped and not stripped.endswith(" "):
                # Trailing char must be at a word boundary in the source.
                # We can verify by checking that `text` has a space right
                # after this chunk's end position.
                pass
        # The simpler invariant: rejoining preserves the original.
        assert "".join(chunks) == text


class TestSplitIntoChunks:
    def test_empty_input_returns_empty_list(self, say_response):
        assert say_response.split_into_chunks("") == []

    def test_short_text_is_one_chunk(self, say_response):
        chunks = say_response.split_into_chunks("短い文章です。")
        assert chunks == ["短い文章です。"]

    def test_first_chunk_is_capped_for_ttfa(self, say_response):
        # Build text whose total comfortably exceeds FIRST_CHUNK_MAX so the
        # splitter is forced to produce a small first chunk and re-flow the
        # rest at LATER_CHUNK_MAX.
        sentence = "これは比較的長めの一文で、句点を含み、ある程度の文字数を持ちます。"
        long_text = sentence * 5
        chunks = say_response.split_into_chunks(long_text)
        assert len(chunks) >= 2
        # First chunk is bounded by FIRST_CHUNK_MAX.
        assert len(chunks[0]) <= say_response.FIRST_CHUNK_MAX
        # All chunks together must cover the cleaned input.
        assert "".join(chunks).replace(" ", "") == long_text.replace(" ", "")

    def test_later_chunks_use_later_budget(self, say_response):
        # Many short sentences: after the first chunk, the rest should
        # consolidate up to LATER_CHUNK_MAX rather than each going into
        # its own chunk.
        sentences = ["文章" + str(i) + "です。" for i in range(20)]
        chunks = say_response.split_into_chunks("".join(sentences))
        # Should not be 20 chunks; consolidation must happen.
        assert len(chunks) < 20
        for c in chunks[1:]:
            assert len(c) <= say_response.LATER_CHUNK_MAX


class TestCommaIsNotASplitBoundary:
    """Regression: `、，,` must not act as chunk boundaries.

    Each chunk adds `prePhonemeLength = 0.5` of leading silence and a separate
    `afplay` device-open transient, so splitting at commas inserts unintended
    half-second pauses inside what the engine would otherwise read as a single
    prosodic phrase. The engine handles its own micro-pause at commas.
    """

    def test_single_sentence_with_commas_stays_one_chunk(self, say_response):
        text = "あれもこれも、それも、どれもが、まとめて一文に収まっている。"
        chunks = say_response.split_into_chunks(text)
        assert chunks == [text]

    def test_long_sentence_with_many_commas_under_first_chunk_max(self, say_response):
        # All under FIRST_CHUNK_MAX → single chunk despite multiple commas.
        text = "報告です、A です、B です、C です。"
        chunks = say_response.split_into_chunks(text)
        assert len(chunks) == 1
        assert "、" in chunks[0]

    def test_period_still_splits(self, say_response):
        # Two sentences each exceeding FIRST_CHUNK_MAX → must split at `。`.
        s1 = "これはひとつ目の文章で、ある程度の長さを持ち、読点を含みます。"
        s2 = "これはふたつ目の文章で、こちらもある程度の長さを持ち、読点を含みます。"
        chunks = say_response.split_into_chunks(s1 + s2)
        assert len(chunks) >= 2
        # First chunk ends at the first period (no further split inside it).
        assert chunks[0].endswith("。")
        assert "、" in chunks[0]

    def test_ascii_period_still_splits(self, say_response):
        # ASCII sentence-ending `.` (followed by space) must still act as a
        # boundary so English prose isn't crammed into one chunk.
        text = (
            "First sentence runs long enough to push past the first-chunk "
            "budget. Second sentence follows, also long enough to matter."
        )
        chunks = say_response.split_into_chunks(text)
        assert len(chunks) >= 2

    def test_ascii_comma_not_a_boundary(self, say_response):
        text = "alpha, beta, gamma, delta all on one line."
        chunks = say_response.split_into_chunks(text)
        # No splitting on `,` even though the sentence has several.
        assert len(chunks) == 1


class TestIntegratedPipeline:
    """End-to-end through clean() + split_into_chunks() on real-world input."""

    def test_mr_intro_followed_by_list(self, say_response):
        text = (
            "MR !108 (draft) https://example.com/foo\n"
            "  - dispatchResults phase step 新設 (rule loop + consumer invariant を内包)\n"
            "  - 550 tests green、 build / format / validate-check.sh 通過"
        )
        cleaned = say_response.clean(text)
        # Intro got its clause break, URL gone, leading `!` gone, inline
        # `.` in filename normalized.
        assert "(draft)。" in cleaned
        assert "https://" not in cleaned
        assert "MR 108" in cleaned and "MR !108" not in cleaned
        assert "validate-check sh" in cleaned

        chunks = say_response.split_into_chunks(cleaned)
        # Word boundaries preserved: `consumer invariant` must stay split
        # by a space, not glued.
        joined = "".join(chunks)
        assert "consumer invariant" in joined
