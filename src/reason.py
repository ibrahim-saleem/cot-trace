"""
reason.py
Two-pass local pipeline (no external LLM APIs):
    Pass 1: build a deterministic extractive reasoning trace from retrieved chunks
    Pass 2: audit each reasoning step with support/relevance/contradiction heuristics
"""
import re
from src.schemas import (
    Citation, ReasoningStep, ReasoningTrace, AuditScore
)
from src.retrieve import Chunk

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are", "was", "were",
    "be", "by", "that", "this", "it", "as", "at", "from", "about", "into", "than", "then", "so", "if",
    "what", "which", "who", "when", "where", "why", "how", "tell", "summarize", "list", "published",
}

NEGATION_TOKENS = {"not", "no", "never", "none", "without", "cannot", "can't", "won't"}

MIN_SENTENCE_SCORE = 0.06
STRONG_SENTENCE_SCORE = 0.16
MIN_TOP_SCORE_FOR_ANSWER = 0.14
TOP_STEPS = 3


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 2}


def _bigrams(tokens: set[str]) -> set[str]:
    ordered = sorted(tokens)
    return {f"{ordered[i]}_{ordered[i+1]}" for i in range(len(ordered) - 1)}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 30]


def _f1_overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    precision = inter / max(len(b), 1)
    recall = inter / max(len(a), 1)
    return 2 * precision * recall / max(precision + recall, 1e-9)


def _question_sentence_score(question: str, sentence: str) -> float:
    q_tokens = _tokenize(question)
    s_tokens = _tokenize(sentence)
    token_f1 = _f1_overlap(q_tokens, s_tokens)
    bg_f1 = _f1_overlap(_bigrams(q_tokens), _bigrams(s_tokens))

    has_q_num = bool(re.search(r"\d", question))
    has_s_num = bool(re.search(r"\d", sentence))
    numeric_bonus = 0.08 if has_q_num and has_s_num else 0.0

    return min(1.0, token_f1 * 0.75 + bg_f1 * 0.17 + numeric_bonus)


def _sentence_similarity(a: str, b: str) -> float:
    return _f1_overlap(_tokenize(a), _tokenize(b))


def _has_negation(text: str) -> bool:
    tokens = set(re.findall(r"[a-z']+", text.lower()))
    return any(t in NEGATION_TOKENS for t in tokens)


def _build_candidates(question: str, chunks: list[Chunk]) -> list[tuple[float, Chunk, str]]:
    candidates: list[tuple[float, Chunk, str]] = []
    for chunk in chunks:
        for sentence in _sentences(chunk.text):
            score = _question_sentence_score(question, sentence)
            if score >= MIN_SENTENCE_SCORE:
                candidates.append((score, chunk, sentence))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates


def _select_diverse(candidates: list[tuple[float, Chunk, str]], k: int = TOP_STEPS) -> list[tuple[float, Chunk, str]]:
    if not candidates:
        return []

    selected: list[tuple[float, Chunk, str]] = [candidates[0]]
    pool = candidates[1:]
    lambda_relevance = 0.75

    while len(selected) < k and pool:
        best_idx = 0
        best_score = -1e9
        for i, cand in enumerate(pool):
            rel, _, sent = cand
            redundancy = max(_sentence_similarity(sent, s[2]) for s in selected)
            mmr = lambda_relevance * rel - (1 - lambda_relevance) * redundancy
            if mmr > best_score:
                best_score = mmr
                best_idx = i
        selected.append(pool.pop(best_idx))

    return selected


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
    unique_sources = len({chunk.source for _, chunk, _ in chosen})
    diversity = unique_sources / max(len(chosen), 1)
    confidence = min(0.92, max(0.25, 0.65 * mean_score + 0.35 * diversity))

    risk_flags: list[str] = []
    if len(strong) == 0:
        risk_flags.append("low_evidence")
    if confidence < 0.5:
        risk_flags.append("low_confidence")
    if len(chosen) > 1 and unique_sources == 1:
        risk_flags.append("single_source")
    if not risk_flags:
        risk_flags = ["none"]

    answer = "Based on retrieved evidence:\n" + "\n".join(lines)
    return answer, risk_flags, confidence


def generate_trace(question: str, chunks: list[Chunk]) -> ReasoningTrace:
    ranked = _build_candidates(question, chunks)
    if not ranked or ranked[0][0] < MIN_TOP_SCORE_FOR_ANSWER:
        top = []
    else:
        top = _select_diverse(ranked, k=TOP_STEPS)

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
    evidence_sents: list[str] = []
    for c in chunks:
        evidence_sents.extend(_sentences(c.text))

    support_strengths: list[float] = []
    question_relevance_scores: list[float] = []

    for step in trace.steps:
        best_overlap = 0.0
        contradiction_hit = False

        for s in evidence_sents:
            sim = _sentence_similarity(step.text, s)
            if sim > best_overlap:
                best_overlap = sim
            if sim >= 0.45 and (_has_negation(step.text) ^ _has_negation(s)):
                contradiction_hit = True

        question_overlap = _question_sentence_score(trace.question, step.text)
        support_strengths.append(best_overlap)
        question_relevance_scores.append(question_overlap)

        if contradiction_hit:
            step.audit_label = "contradictory"
            step.audit_explanation = "Potential contradiction detected against retrieved evidence with opposite polarity."
        elif best_overlap >= 0.45 and question_overlap >= STRONG_SENTENCE_SCORE:
            step.audit_label = "supported"
            step.audit_explanation = "Strong evidence overlap and strong relevance to the question."
        elif best_overlap >= 0.3 and question_overlap >= MIN_SENTENCE_SCORE:
            step.audit_label = "weak"
            step.audit_explanation = "Partially supported by evidence, but relevance or strength is limited."
        elif step.citations:
            step.audit_label = "speculative"
            step.audit_explanation = "Citations exist, but evidence overlap or question relevance is weak."
        else:
            step.audit_label = "unsupported"
            step.audit_explanation = "No clear supporting evidence found in retrieved chunks."

    label_weights = {"supported": 1.0, "weak": 0.5, "unsupported": 0.0, "contradictory": 0.0, "speculative": 0.2}
    n = len(trace.steps)
    grounding = sum(label_weights.get(s.audit_label, 0) for s in trace.steps) / max(n, 1)
    # Coverage reflects evidence strength, not only citation presence.
    coverage = sum(min(v / 0.45, 1.0) for v in support_strengths) / max(n, 1)
    question_relevance = sum(question_relevance_scores) / max(n, 1)
    contradictions = sum(1 for s in trace.steps if s.audit_label == "contradictory")
    # Calibrate alignment by both evidence quality and generation confidence.
    answer_alignment = min(grounding, question_relevance, trace.confidence)
    raw_overall = grounding * 0.4 + coverage * 0.2 + question_relevance * 0.25 + answer_alignment * 0.15
    contradiction_penalty = min(0.3, contradictions * 0.12)
    overall = round(max(0.0, raw_overall - contradiction_penalty), 3)

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
