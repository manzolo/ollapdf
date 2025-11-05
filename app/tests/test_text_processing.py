"""Unit tests for UI text processing utilities."""
import pytest
from ui.text_processing import process_latex, extract_think_content, clean_response


class TestProcessLatex:
    """Tests for LaTeX processing."""

    def test_process_display_math(self):
        """Test conversion of display math markers."""
        input_text = r"Here is some math: \[x^2 + y^2 = z^2\] and more text."
        expected = r"Here is some math: $$x^2 + y^2 = z^2$$ and more text."
        assert process_latex(input_text) == expected

    def test_process_inline_math(self):
        """Test conversion of inline math markers."""
        input_text = r"The equation \(E = mc^2\) is famous."
        expected = r"The equation $E = mc^2$ is famous."
        assert process_latex(input_text) == expected

    def test_process_mixed_math(self):
        """Test conversion of both display and inline math."""
        input_text = r"Inline \(a + b\) and display \[x = y\] math."
        expected = r"Inline $a + b$ and display $$x = y$$ math."
        assert process_latex(input_text) == expected

    def test_no_latex(self):
        """Test text without LaTeX markers."""
        input_text = "Just plain text with no math."
        assert process_latex(input_text) == input_text


class TestExtractThinkContent:
    """Tests for think tag extraction."""

    def test_extract_single_think(self):
        """Test extraction of single think tag."""
        input_text = "Answer: 42 <think>Let me think about this...</think>"
        cleaned, thinks = extract_think_content(input_text)
        assert cleaned == "Answer: 42"
        assert len(thinks) == 1
        assert thinks[0] == "Let me think about this..."

    def test_extract_multiple_thinks(self):
        """Test extraction of multiple think tags."""
        input_text = "<think>First thought</think> Answer <think>Second thought</think>"
        cleaned, thinks = extract_think_content(input_text)
        assert cleaned == "Answer"
        assert len(thinks) == 2
        assert thinks[0] == "First thought"
        assert thinks[1] == "Second thought"

    def test_no_think_tags(self):
        """Test text without think tags."""
        input_text = "Just a regular answer."
        cleaned, thinks = extract_think_content(input_text)
        assert cleaned == input_text
        assert len(thinks) == 0

    def test_multiline_think(self):
        """Test extraction of multiline think content."""
        input_text = """Answer: <think>
        First line of thinking
        Second line of thinking
        </think> Done."""
        cleaned, thinks = extract_think_content(input_text)
        assert "Answer:" in cleaned
        assert "Done." in cleaned
        assert len(thinks) == 1


class TestCleanResponse:
    """Tests for response cleaning."""

    def test_clean_bullets(self):
        """Test bullet point formatting."""
        input_text = "List:\n- Item 1\n* Item 2"
        result = clean_response(input_text)
        assert "• Item 1" in result
        assert "• Item 2" in result

    def test_clean_with_latex(self):
        """Test cleaning includes LaTeX processing."""
        input_text = r"Math: \(x = 5\)"
        result = clean_response(input_text)
        assert r"$x = 5$" in result

    def test_clean_strips_whitespace(self):
        """Test whitespace stripping."""
        input_text = "  \n  Text with spaces  \n  "
        result = clean_response(input_text)
        assert result == "Text with spaces"
