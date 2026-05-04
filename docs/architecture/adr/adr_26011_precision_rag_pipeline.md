# ADR 260502: Precision RAG Pipeline for Technical Knowledge Base

**Date:** 2026-05-02
**Status:** Proposed

## Context
The project is implementing a RAG (Retrieval-Augmented Generation) system to serve as a "Ground Truth" knowledge base for an SLM Mentor. The current implementation uses a naive RAG approach with `sentence-transformers/all-MiniLM-L6-v2`.

The knowledge base is expanding to include:
- 5-7 technical textbooks (~700 pages each).
- Numerous arXiv research papers.
- Total volume: 4,000+ pages of dense mathematical and architectural text.

In a "Skeptical Mastery" pedagogical framework, "near-miss" retrieval is dangerous. If the RAG system returns a chunk that is semantically similar but mathematically incorrect or contextually incomplete, the LLM may present it as truth, leading to "false mastery" for the student. To prevent the RAG from becoming "prompt trash," the system must prioritize **Precision (Faithfulness)** over **Recall (Broadness)**.

## Alternatives Considered

### Option 2: Hybrid Search (The Balanced Path)
Combining **BM25 (Keyword)** and **Vector (Semantic)** retrieval. 
- **Pros**: Fast, handles exact terminology (e.g., formulas) better than pure vector search.
- **Cons**: Still susceptible to "semantic noise" at the 4,000+ page scale; lacks the precision audit of a reranker.

### Option 3: Naive+Plus (The Lightweight Path)
Improving the existing naive RAG through **Recursive Character Splitting** and **Top-K tuning**.
- **Pros**: Extremely low latency, simple implementation.
- **Cons**: High risk of "Prompt Trash" due to poor chunk quality and lack of evidence verification.

## Decision
We will implement a multi-stage **Precision Engine** RAG pipeline instead of a naive vector search.

### 1. Embedding Upgrade
Replace `all-MiniLM-L6-v2` with a high-performance technical embedding model (e.g., BGE-large or Cohere v3). These models have a better understanding of technical nuance and mathematical relationships.

### 2. Parent-Document Retrieval (PDR)
To solve the "fragmentation problem" (where a small chunk lacks the context to be useful), we will implement a two-tier storage strategy:
- **Child Chunks**: Small, granular segments used for the initial vector search.
- **Parent Documents**: Larger sections (paragraphs or full pages) that contain the child chunks.
- **Mechanism**: The system searches for child chunks but retrieves and feeds the corresponding parent document to the LLM.

### 3. Two-Stage Retrieval (Cross-Encoder Reranking)
To eliminate semantic noise, we will decouple "Candidate Generation" from "Evidence Selection":
- **Stage 1 (Retrieval)**: A fast vector search retrieves the top-N (e.g., 20) candidates.
- **Stage 2 (Reranking)**: A computationally expensive but highly accurate **Cross-Encoder** reranker audits the 20 candidates and selects only the top-K (e.g., 5) most relevant chunks based on actual content relevance rather than vector distance.

## Consequences

### Positive
- **Extreme Fidelity**: Drastically reduces the probability of the LLM receiving irrelevant or misleading evidence.
- **Contextual Integrity**: Parent-Document Retrieval ensures that mathematical formulas and architectural descriptions are presented in their full context.
- **Pedagogical Alignment**: Supports "Skeptical Mastery" by providing binary, verifiable evidence from the textbooks.

### Negative
- **Increased Latency**: The reranking stage adds a measurable delay to the response time.
- **Higher Compute**: Cross-encoders are more resource-intensive than simple cosine similarity.
- **Implementation Complexity**: Requires a more complex indexing and retrieval logic than naive RAG.
