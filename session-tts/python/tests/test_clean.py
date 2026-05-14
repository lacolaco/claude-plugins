"""Tests for `clean()`: paragraph/list-aware Markdown-to-prose conversion."""
from __future__ import annotations


class TestParagraphHandling:
    def test_single_paragraph_passes_through(self, say_response):
        assert say_response.clean("今日は良い天気") == "今日は良い天気"

    def test_multi_line_paragraph_joined_with_space(self, say_response):
        # Two adjacent non-list lines stay as one prose paragraph; no 。
        # is inserted between them.
        result = say_response.clean("今日は良い天気\n散歩に行こう")
        assert result == "今日は良い天気 散歩に行こう"

    def test_blank_line_separates_paragraphs(self, say_response):
        result = say_response.clean("段落1\n\n段落2")
        assert result == "段落1\n\n段落2"


class TestListItems:
    def test_list_items_get_terminal_punctuation(self, say_response):
        result = say_response.clean("- A\n- B")
        assert result == "A。 B。"

    def test_list_item_with_existing_terminator_left_alone(self, say_response):
        result = say_response.clean("- Done.\n- 終了")
        # First item keeps its `.`, second gets `。`.
        assert "Done." in result
        assert result.endswith("終了。")

    def test_numbered_list(self, say_response):
        result = say_response.clean("1. first\n2. second")
        assert result == "first。 second。"


class TestIntroListBoundary:
    def test_non_list_intro_gets_clause_break_before_list(self, say_response):
        result = say_response.clean("変更内容\n  - A\n  - B")
        assert result == "変更内容。 A。 B。"

    def test_intro_already_terminated_no_double_punct(self, say_response):
        result = say_response.clean("変更内容。\n  - A")
        # No double 。
        assert "。。" not in result
        assert result.startswith("変更内容。")

    def test_intro_with_url_keeps_clause_break(self, say_response):
        # After URL stripping, the clause break inserted before the list
        # must still be present and adjacent to the preceding token.
        result = say_response.clean(
            "MR 108 (draft) https://example.com/foo\n  - first item"
        )
        assert "(draft)。" in result
        assert "(draft) 。" not in result  # no stray space


class TestHeadingFolding:
    def test_heading_folded_into_next_paragraph(self, say_response):
        result = say_response.clean("## 検証\n\n本文")
        # Heading + 。 prepended to next paragraph.
        assert result == "検証。本文"

    def test_lone_heading_emitted_as_fallback(self, say_response):
        result = say_response.clean("## 検証")
        assert result == "検証。"


class TestStrippedContent:
    def test_fenced_code_block_stripped(self, say_response):
        result = say_response.clean("text\n```\ncode\n```\nafter")
        assert "code" not in result

    def test_table_lines_stripped(self, say_response):
        result = say_response.clean(
            "本文1\n| col1 | col2 |\n|------|------|\n| a | b |\n本文2"
        )
        assert "col1" not in result and "col2" not in result
        assert "本文1" in result and "本文2" in result

    def test_blockquote_stripped(self, say_response):
        result = say_response.clean("> quoted line\nactual text")
        assert "quoted" not in result
        assert "actual text" in result

    def test_shell_prompt_stripped(self, say_response):
        result = say_response.clean("$ command output\nresult")
        assert "command output" not in result
        assert "result" in result
