"""
rag_engine.py
-------------
Minimal RAG engine that:
  1. Embeds chunks with sentence-transformers (local, open-source).
  2. Stores vectors in a simple NumPy array (no external vector DB needed).
  3. Retrieves the top-k most relevant chunks for a user query.
  4. Builds a prompt and calls a local LLM via Ollama's HTTP API.

Everything runs locally — no API keys required.
"""

import json
import textwrap
import urllib.request
import urllib.error
from typing import List, Tuple

import numpy as np

# ---------- optional sentence-transformers import ----------
_EMBEDDER = None

def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(
                "sentence-transformers is required.  "
                "Install with:  pip install sentence-transformers"
            )
    return _EMBEDDER


# ------------------------------------------------------------------ #
#  Embedding helpers                                                   #
# ------------------------------------------------------------------ #

def embed_texts(texts: List[str]) -> np.ndarray:
    """Return L2-normalised embeddings (N x D) for a list of texts."""
    model = _get_embedder()
    vecs = model.encode(texts, normalize_embeddings=True)
    return np.asarray(vecs, dtype=np.float32)


def embed_query(query: str) -> np.ndarray:
    """Return a single normalised query vector (1 x D)."""
    return embed_texts([query])


# ------------------------------------------------------------------ #
#  In-memory vector store                                              #
# ------------------------------------------------------------------ #

class SimpleVectorStore:
    """NumPy-backed vector store — no external DB required."""

    def __init__(self):
        self.texts: List[str] = []
        self.vectors: np.ndarray | None = None

    def add(self, chunks: List[str]) -> None:
        """Embed and store a list of text chunks."""
        vecs = embed_texts(chunks)
        self.texts.extend(chunks)
        if self.vectors is None:
            self.vectors = vecs
        else:
            self.vectors = np.vstack([self.vectors, vecs])

    def search(self, query: str, top_k: int = 3) -> List[Tuple[float, str]]:
        """Return the top-k most similar chunks (cosine similarity)."""
        if self.vectors is None or len(self.texts) == 0:
            return []
        q = embed_query(query)                       # (1, D)
        scores = (self.vectors @ q.T).squeeze()      # (N,)
        idxs = np.argsort(-scores)[:top_k]
        return [(float(scores[i]), self.texts[i]) for i in idxs]


# ------------------------------------------------------------------ #
#  Prompt builder                                                      #
# ------------------------------------------------------------------ #

def build_prompt(query: str, context_chunks: List[str]) -> str:
    """Format retrieved chunks + user query into a RAG prompt."""
    context_block = "\n---\n".join(context_chunks)
    return textwrap.dedent(f"""\
        You are a helpful data-analysis assistant.
        Answer the user's question using ONLY the context below.
        If the context does not contain enough information, say so.

        ### Context (retrieved from the dataset)
        {context_block}

        ### Question
        {query}

        ### Answer""")


# ------------------------------------------------------------------ #
#  LLM caller — talks to a local Ollama instance                      #
# ------------------------------------------------------------------ #

def call_ollama(
    prompt: str,
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
) -> str:
    """
    Send *prompt* to a local Ollama server and return the response.

    Requires Ollama running locally (https://ollama.com).
    Pull a model first:  ollama pull llama3
    """
    url = f"{base_url}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
            return body.get("response", "")
    except urllib.error.URLError as exc:
        return (
            f"[Ollama unreachable] Could not connect to {base_url}. "
            f"Make sure Ollama is running.  Error: {exc}"
        )


# ------------------------------------------------------------------ #
#  High-level RAG entry point (called from C#)                        #
# ------------------------------------------------------------------ #

def ask(
    query: str,
    context_text: str,
    ollama_model: str = "llama3",
) -> str:
    """
    End-to-end RAG:
      1. Split the context text into chunks.
      2. Embed & store.
      3. Retrieve top-3 chunks for the query.
      4. Build a prompt and call Ollama.

    *context_text* is typically the string returned by
    data_processor.summarize_by_column() or filter_rows().
    """
    # -- chunk the context (split on double newline or every ~500 chars) --
    raw_chunks = [c.strip() for c in context_text.split("\n\n") if c.strip()]
    if not raw_chunks:
        raw_chunks = [
            context_text[i : i + 500]
            for i in range(0, len(context_text), 500)
        ]

    store = SimpleVectorStore()
    store.add(raw_chunks)

    results = store.search(query, top_k=3)
    retrieved = [text for _, text in results]

    prompt = build_prompt(query, retrieved)
    answer = call_ollama(prompt, model=ollama_model)
    return answer


# ------------------------------------------------------------------ #
#  Office Auditor — specialised prompt + entry point                   #
# ------------------------------------------------------------------ #

def build_auditor_prompt(query: str, context_chunks: List[str]) -> str:
    """
    Build a prompt with the Office Auditor system instructions.
    The LLM is told to act as a productivity analyst and use the
    Pandas-calculated metrics to answer workforce questions.
    """
    context_block = "\n---\n".join(context_chunks)
    return textwrap.dedent(f"""\
        You are an expert Office Productivity Auditor.
        You have been given pre-calculated productivity metrics derived from
        real employee timesheets and task logs using Pandas.

        Your job is to answer the user's question using ONLY the data below.
        When answering, you MUST:
        1. Identify the least performing team member (lowest tasks/hour ratio).
        2. Identify the most time-allotted individual for the month (highest total hours).
        3. Comment on trends in team productivity (spread, outliers, workload balance).
        4. Support every claim with the specific numbers from the data.
        5. If the data does not contain enough information to answer, say so.

        ### Productivity Data (calculated via Pandas)
        {context_block}

        ### User Question
        {query}

        ### Auditor Analysis""")


def ask_auditor(
    query: str,
    context_text: str,
    ollama_model: str = "llama3",
) -> str:
    """
    Office Auditor RAG pipeline.

    Same chunking + retrieval flow as ``ask()``, but uses the auditor
    system prompt that instructs the LLM to identify top/bottom
    performers and productivity trends.

    *context_text* is the Markdown string returned by
    ``analysis_engine.build_audit_context()``.
    """
    raw_chunks = [c.strip() for c in context_text.split("\n\n") if c.strip()]
    if not raw_chunks:
        raw_chunks = [
            context_text[i : i + 500]
            for i in range(0, len(context_text), 500)
        ]

    store = SimpleVectorStore()
    store.add(raw_chunks)

    results = store.search(query, top_k=5)
    retrieved = [text for _, text in results]

    prompt = build_auditor_prompt(query, retrieved)
    answer = call_ollama(prompt, model=ollama_model)
    return answer
