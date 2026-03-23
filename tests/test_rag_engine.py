"""Tests for PythonScripts/rag_engine.py — unit tests that don't need Ollama."""

import pytest
import rag_engine


class TestBuildPrompt:
    def test_includes_query_and_context(self):
        prompt = rag_engine.build_prompt(
            "What is the revenue?",
            ["Chunk A: revenue is 100", "Chunk B: revenue is 200"],
        )
        assert "What is the revenue?" in prompt
        assert "Chunk A" in prompt
        assert "Chunk B" in prompt
        assert "Context" in prompt

    def test_empty_chunks(self):
        prompt = rag_engine.build_prompt("question?", [])
        assert "question?" in prompt


class TestEmbedding:
    """These tests require sentence-transformers to be installed."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_st(self):
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")

    def test_embed_texts_shape(self):
        vecs = rag_engine.embed_texts(["hello world", "foo bar"])
        assert vecs.shape[0] == 2
        assert vecs.shape[1] > 0  # embedding dimension

    def test_embed_query_shape(self):
        vec = rag_engine.embed_query("test query")
        assert vec.shape == (1, vec.shape[1])


class TestSimpleVectorStore:
    @pytest.fixture(autouse=True)
    def _skip_if_no_st(self):
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")

    def test_add_and_search(self):
        store = rag_engine.SimpleVectorStore()
        chunks = [
            "Revenue for Electronics is 8250",
            "Revenue for Audio is 1690",
            "The weather is sunny today",
        ]
        store.add(chunks)
        results = store.search("electronics revenue", top_k=2)
        assert len(results) == 2
        # The most relevant chunk should mention Electronics
        assert "Electronics" in results[0][1]

    def test_search_empty_store(self):
        store = rag_engine.SimpleVectorStore()
        results = store.search("anything")
        assert results == []


class TestCallOllama:
    def test_unreachable_ollama_returns_error_message(self):
        """When Ollama isn't running, we get a descriptive error, not a crash."""
        result = rag_engine.call_ollama(
            "test prompt",
            base_url="http://localhost:99999",
        )
        assert "unreachable" in result.lower() or "error" in result.lower()
