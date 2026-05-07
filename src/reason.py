"""
reason.py
Two-pass local pipeline (no external LLM APIs):
    Pass 1: build an extractive reasoning trace from retrieved chunks
    Pass 2: audit each reasoning step against the same chunks
"""
import re
from src.schemas import (
    Citation, ReasoningStep, ReasoningTrace, AuditScore
)
from src.retrieve import Chunk

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are", "was", "were",
    "be", "by", "that", "this", "it", "as", "at", "from", "about", "into", "than", "then", "so", "if",
}

MIN_SENTENCE_SCORE = 0.08
STRONG_SENTENCE_SCORE = 0.16


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 2}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 30]


def _overlap_score(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), 1)


def _build_extractive_answer(top: list[tuple[float, Chunk, str]]) -> tuple[str, list[str], float]:
    if not top:
        return (
            "I do not have enough evidence in the cached sources to answer this reliably.",
            ["insufficient_evidence"],
            0.2,
        )

    strong = [item for item in top if item[0] >= STRONG_SENTENCE_SCORE]
    chosen = (strong or top)[:2]

    lines = []
    for _, chunk, sentence in chosen:
        src = chunk.source or "source"
        lines.append(f'- "{sentence}" ({src})')

    mean_score = sum(score for score, _, _ in chosen) / max(len(chosen), 1)
    confidence = min(0.9, max(0.35, mean_score))
    risk_flags = ["none"] if len(strong) >= 1 else ["low_evidence"]
    answer = "Based on retrieved evidence:\n" + "\n".join(lines)
    return answer, risk_flags, confidence


def generate_trace(question: str, chunks: list[Chunk]) -> ReasoningTrace:
    ranked: list[tuple[float, Chunk, str]] = []

    for c in chunks:
        for s in _sentences(c.text):
            score = _overlap_score(s, question)
            if score >= MIN_SENTENCE_SCORE:
                ranked.append((score, c, s))

    ranked.sort(key=lambda x: x[0], reverse=True)
    top = ranked[:3] if ranked else []

    steps: list[ReasoningStep] = []
    for idx, (score, chunk, sentence) in enumerate(top, start=1):
        label = "observation" if idx == 1 else "inference"
        steps.append(ReasoningStep(
            step_id=idx,
            text=sentence,
            label=label,
            citations=[Citation(
                doc_id=chunk.doc_id,
                title=chunk.title,
                url=chunk.url,
                snippet=sentence[:220],
            )],
        ))

    answer, risk_flags, confidence = _build_extractive_answer(top)

    return ReasoningTrace(
        question=question,
        answer=answer,
        confidence=confidence,
        risk_flags=risk_flags,
        steps=steps,
    )


def audit_trace(trace: ReasoningTrace, chunks: list[Chunk]) -> tuple[ReasoningTrace, AuditScore]:
    for step in trace.steps:
        best_overlap = 0.0
        for c in chunks:
            best_overlap = max(best_overlap, _overlap_score(step.text, c.text))

        if best_overlap >= 0.35:
            step.audit_label = "supported"
            step.audit_explanation = "High lexical overlap with retrieved evidence."
        elif best_overlap >= 0.2:
            step.audit_label = "weak"
            step.audit_explanation = "Partial overlap with evidence; claim may be over-generalized."
        elif step.citations:
            step.audit_label = "speculative"
            step.audit_explanation = "Citation exists, but content overlap is weak."
        else:
            step.audit_label = "unsupported"
            step.audit_explanation = "No clear supporting evidence found in retrieved chunks."

    label_weights = {"supported": 1.0, "weak": 0.5, "unsupported": 0.0, "contradictory": 0.0, "speculative": 0.2}
    n = len(trace.steps)
    grounding = sum(label_weights.get(s.audit_label, 0) for s in trace.steps) / max(n, 1)
    coverage = sum(1 for s in trace.steps if s.citations) / max(n, 1)
    contradictions = sum(1 for s in trace.steps if s.audit_label == "contradictory")
    answer_alignment = min(1.0, grounding * 0.8 + coverage * 0.2)
    overall = round((grounding * 0.4 + coverage * 0.3 + answer_alignment * 0.3), 3)

    score = AuditScore(
        grounding_score=round(grounding, 3),
        evidence_coverage=round(coverage, 3),
        contradiction_count=contradictions,
        answer_alignment=answer_alignment,
        overall=overall,
    )
    return trace, score


def run_pipeline_safe(question: str, chunks: list[Chunk]) -> tuple[ReasoningTrace, AuditScore]:
    """Always return a result, even if the main local pipeline fails."""
    try:
        trace = generate_trace(question, chunks)
        return audit_trace(trace, chunks)
    except Exception:
        fallback_text = "I could not run full reasoning, so this is a best-effort evidence summary."
        citation = None
        if chunks:
            c = chunks[0]
            snippet = (c.text or "")[:220]
            fallback_text = snippet or fallback_text
            citation = Citation(
                doc_id=c.doc_id,
                title=c.title,
                url=c.url,
                snippet=snippet,
            )

        step = ReasoningStep(
            step_id=1,
            text=fallback_text,
            label="observation",
            citations=[citation] if citation else [],
            audit_label="weak",
            audit_explanation="Fallback mode: returned best available local evidence.",
        )
        trace = ReasoningTrace(
            question=question,
            answer=fallback_text,
            confidence=0.4,
            risk_flags=["fallback_mode"],
            steps=[step],
        )
        score = AuditScore(
            grounding_score=0.5,
            evidence_coverage=1.0 if citation else 0.0,
            contradiction_count=0,
            answer_alignment=0.5,
            overall=0.5,
        )
        return trace, score
