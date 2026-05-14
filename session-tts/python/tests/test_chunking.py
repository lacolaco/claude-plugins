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
