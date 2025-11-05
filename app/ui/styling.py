"""Styling and CSS utilities for the UI."""
import os


def load_css() -> str:
    """
    Load CSS from static file.

    Returns:
        CSS content as string
    """
    css_path = os.path.join(os.path.dirname(__file__), "..", "static", "styles.css")

    try:
        with open(css_path, 'r') as f:
            css_content = f.read()
        return css_content
    except FileNotFoundError:
        # Fallback to minimal CSS if file not found
        return """
        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --text: #c9d1d9;
        }
        .stApp, .main {
            background-color: var(--bg) !important;
            color: var(--text) !important;
        }
        """


def render_math_script() -> str:
    """
    Get JavaScript for KaTeX math rendering.

    Returns:
        JavaScript code as string
    """
    return """<script>
function renderMath() {
    if (typeof renderMathInElement !== "undefined") {
        renderMathInElement(document.body, {
            delimiters: [
                {left: "$$", right: "$$", display: true},
                {left: "$", right: "$", display: false},
                {left: "\\\\(", right: "\\\\)", display: false},
                {left: "\\\\[", right: "\\\\]", display: true}
            ],
            throwOnError: false,
            trust: true
        });
    }
}
document.addEventListener("DOMContentLoaded", renderMath);
const observer = new MutationObserver(() => setTimeout(renderMath, 100));
observer.observe(document.body, { childList: true, subtree: true });
setInterval(renderMath, 800);
</script>"""


def get_html_head() -> str:
    """
    Get HTML head content with fonts and external libraries.

    Returns:
        HTML head content as string
    """
    return """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>"""
