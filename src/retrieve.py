"""
retrieve.py
Chunk documents, build a TF-IDF index, return top-k chunks for a query.
No vector DB. No embeddings API call. Works offline. Fast enough for demo.
"""
import re
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from src.schemas import Document

CHUNK_SIZE = 400        # words per chunk
CHUNK_OVERLAP = 80      # word overlap between chunks
TOP_K = 6               # chunks returned per query


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    title: str
    url: str
    text: str


def _split_into_chunks(doc: Document) -> list[Chunk]:
    words = doc.content.split()
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for i, start in enumerate(range(0, len(words), step)):
        text = " ".join(words[start : start + CHUNK_SIZE])
        if len(text.strip()) < 60:
            continue
        chunks.append(Chunk(
            chunk_id=f"{doc.doc_id}_c{i:02d}",
            doc_id=doc.doc_id,
            source=doc.source,
            title=doc.title,
            url=doc.url,
            text=text,
        ))
    return chunks


class Retriever:
    def __init__(self, documents: list[Document]):
        self.chunks: list[Chunk] = []
        for doc in documents:
            self.chunks.extend(_split_into_chunks(doc))

        texts = [c.text for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_df=0.85,
            min_df=1,
            stop_words="english",
        )
        self.matrix = self.vectorizer.fit_transform(texts)

    def query(self, question: str, top_k: int = TOP_K) -> list[Chunk]:
        q_vec = self.vectorizer.transform([question])
        scores = cosine_similarity(q_vec, self.matrix).flatten()
        top_idx = np.argsort(scores)[::-1][:top_k]
        # only return chunks with non-zero similarity
        return [self.chunks[i] for i in top_idx if scores[i] > 0.01]
