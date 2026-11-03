"""Unit tests for the configurable system prompt."""
from langchain_core.prompts import ChatPromptTemplate

from core.rag_service import DEFAULT_SYSTEM_PROMPT, RAGService, build_system_prompt


def variables(system_prompt):
    """Template variables LangChain sees in a system + human prompt."""
    template = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    return set(template.input_variables)


class TestBuildSystemPrompt:
    """Tests for build_system_prompt."""

    def test_empty_uses_default(self):
        assert build_system_prompt(None) == DEFAULT_SYSTEM_PROMPT
        assert build_system_prompt("") == DEFAULT_SYSTEM_PROMPT
        assert build_system_prompt("   ") == DEFAULT_SYSTEM_PROMPT

    def test_default_has_context_and_language(self):
        assert variables(DEFAULT_SYSTEM_PROMPT) == {"context", "input"}
        assert "same language as the question" in DEFAULT_SYSTEM_PROMPT

    def test_custom_prompt_keeps_context(self):
        prompt = build_system_prompt("Be brief. Context: {context}")
        assert variables(prompt) == {"context", "input"}

    def test_missing_context_is_appended(self):
        prompt = build_system_prompt("Answer like a pirate.")
        assert prompt.startswith("Answer like a pirate.")
        assert variables(prompt) == {"context", "input"}

    def test_latex_braces_are_not_variables(self):
        prompt = build_system_prompt(r"Write formulas like \frac{a}{b} and x_{f}. Context: {context}")
        assert variables(prompt) == {"context", "input"}
        rendered = ChatPromptTemplate.from_messages([("system", prompt)]).format_messages(context="CTX")
        assert r"\frac{a}{b}" in rendered[0].content
        assert "CTX" in rendered[0].content


class TestRAGServicePrompt:
    """RAGService stores the prompt it will use."""

    def test_service_default_prompt(self):
        assert RAGService().system_prompt == DEFAULT_SYSTEM_PROMPT

    def test_service_custom_prompt(self):
        service = RAGService(system_prompt="Only facts. {context}")
        assert service.system_prompt == "Only facts. {context}"


class TestRAGServiceResponseCap:
    """RAGService caps the length of an answer (num_predict)."""

    def test_default_cap(self):
        assert RAGService().num_predict == 8192

    def test_custom_cap(self):
        assert RAGService(max_response_tokens=2048).num_predict == 2048

    def test_zero_or_negative_means_no_cap(self):
        assert RAGService(max_response_tokens=0).num_predict == -1
        assert RAGService(max_response_tokens=-5).num_predict == -1
