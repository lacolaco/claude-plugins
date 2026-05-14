"""Tests for `_strip_inline_markdown`: per-paragraph text normalization.

The function strips markdown markers, URLs, and several engine-specific
oddities (inline `.`, leading `!` sigils, decorative dash runs). Each rule
is covered by a parametrized block so a regression is pinpointable.
"""
from __future__ import annotations

import pytest


class TestMarkdownStripping:
    @pytest.mark.parametrize(
        "src,expected",
        [
            ("![alt](http://example.com/img.png)", ""),
            ("[label](http://example.com)", "label"),
            ("**bold**", "bold"),
            ("*italic*", "italic"),
            ("`code`", "code"),
            ("# title", "title"),
            ("> quote text", "quote text"),
        ],
    )
    def test_markers_removed(self, say_response, src, expected):
        assert say_response._strip_inline_markdown(src) == expected


class TestUrlStripping:
    @pytest.mark.parametrize(
        "src,expected",
        [
            ("see https://example.com for more", "see for more"),
            ("https://example.com/path?a=1", ""),
            ("text https://example.com。 next", "text。 next"),
            ("text https://example.com、 next", "text、 next"),
            ("(draft) https://example.com。 next", "(draft)。 next"),
        ],
    )
    def test_url_removed(self, say_response, src, expected):
        assert say_response._strip_inline_markdown(src) == expected

    def test_url_ending_with_terminal_punct_preserves_punct(self, say_response):
        result = say_response._strip_inline_markdown("foo https://x.test/p。")
        assert result.endswith("。")


class TestInlinePeriod:
    @pytest.mark.parametrize(
        "src,expected",
        [
            ("say.sh", "say sh"),
            ("src/foo.tsx", "src/foo tsx"),
            ("version 0.7.3", "version 0 7 3"),
            ("127.0.0.1", "127 0 0 1"),
        ],
    )
    def test_inline_period_becomes_space(self, say_response, src, expected):
        assert say_response._strip_inline_markdown(src) == expected

    @pytest.mark.parametrize(
        "src",
        [
            "Done.",
            "Hello world.",
            "Mr. Smith arrived.",
        ],
    )
    def test_period_followed_by_whitespace_or_eol_preserved(
        self, say_response, src
    ):
        assert say_response._strip_inline_markdown(src) == src


class TestLeadingBangSigil:
    @pytest.mark.parametrize(
        "src,expected",
        [
            ("MR !107 done", "MR 107 done"),
            ("see !42", "see 42"),
            ("!Important note", "Important note"),
        ],
    )
    def test_leading_bang_stripped(self, say_response, src, expected):
        assert say_response._strip_inline_markdown(src) == expected

    @pytest.mark.parametrize(
        "src",
        [
            "Done!",
            "Wow! Great work",
            "Mid!Word",
        ],
    )
    def test_word_internal_bang_preserved(self, say_response, src):
        assert say_response._strip_inline_markdown(src) == src


class TestDashRuns:
    def test_long_dash_run_collapsed_to_space(self, say_response):
        result = say_response._strip_inline_markdown("Insight ―――― here")
        assert "――" not in result
        assert "Insight" in result and "here" in result

    @pytest.mark.parametrize("src", ["text — more", "text – more"])
    def test_single_dash_preserved(self, say_response, src):
        assert say_response._strip_inline_markdown(src) == src
