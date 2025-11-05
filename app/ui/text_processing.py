"""Text processing utilities for the UI."""
import re
from typing import Tuple, List


def process_latex(text: str) -> str:
    """
    Convert standard LaTeX markers to KaTeX format.

    Args:
        text: Input text with LaTeX markers

    Returns:
        Text with KaTeX-compatible markers
    """
    # Convert \\[...\\] to $$...$$  (display math)
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    # Convert \\(...\\) to $...$ (inline math)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    return text


def extract_think_content(text: str) -> Tuple[str, List[str]]:
    """
    Extract <think> tags and return cleaned text + thinking sections.

    Args:
        text: Input text potentially containing <think> tags

    Returns:
        Tuple of (cleaned_text, list_of_think_sections)
    """
    think_pattern = r'<think>(.*?)</think>'
    think_matches = re.findall(think_pattern, text, re.DOTALL)
    cleaned_text = re.sub(think_pattern, '', text, flags=re.DOTALL)
    return cleaned_text.strip(), think_matches


def clean_response(text: str) -> str:
    """
    Clean and format response text.

    Applies LaTeX formatting and general text formatting.

    Args:
        text: Raw response text

    Returns:
        Cleaned and formatted text
    """
    # Apply LaTeX formatting
    text = process_latex(text)

    # Format bullet points
    text = re.sub(r'^\s*[\-\*]\s+', '• ', text, flags=re.MULTILINE)

    # Format headers
    text = re.sub(r'^(#+\s+.+)$', r'**\1**', text, flags=re.MULTILINE)

    return text.strip()
