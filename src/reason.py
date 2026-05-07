"""
reason.py
Two-pass local pipeline (no external LLM APIs):
    Pass 1: build a deterministic extractive reasoning trace from retrieved chunks
    Pass 2: audit each reasoning step with corroboration/relevance/contradiction heuristics
"""
import math
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
CORROBORATE_THRESHOLD = 0.32


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 2}


def _token_list(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 2]


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


def _idf_from_chunks(chunks: list[Chunk]) -> dict[str, float]:
    n_docs = max(len(chunks), 1)
    df: dict[str, int] = {}
    for c in chunks:
        seen = set(_token_list(c.text))
        for t in seen:
            df[t] = df.get(t, 0) + 1
    return {t: math.log((1 + n_docs) / (1 + freq)) + 1.0 for t, freq in df.items()}


def _weighted_f1(a_tokens: set[str], b_tokens: set[str], idf: dict[str, float]) -> float:
    if not a_tokens or not b_tokens:
        return 0.0
    inter = a_tokens & b_tokens
    if not inter:
        return 0.0
    inter_w = sum(idf.get(t, 1.0) for t in inter)
    a_w = sum(idf.get(t, 1.0) for t in a_tokens)
    b_w = sum(idf.get(t, 1.0) for t in b_tokens)
    precision = inter_w / max(b_w, 1e-9)
    recall = inter_w / max(a_w, 1e-9)
    return 2 * precision * recall / max(precision + recall, 1e-9)


def _question_sentence_score(question: str, sentence: str, idf: dict[str, float]) -> float:
    q_tokens = _tokenize(question)
    s_tokens = _tokenize(sentence)
    token_f1 = _weighted_f1(q_tokens, s_tokens, idf)
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
    idf = _idf_from_chunks(chunks)
    candidates: list[tuple[float, Chunk, str]] = []
    for chunk in chunks:
        for sentence in _sentences(chunk.text):
            score = _question_sentence_score(question, sentence, idf)
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
            rel, chunk, sent = cand
            redundancy = max(_sentence_similarity(sent, s[2]) for s in selected)
            source_bonus = 0.06 if chunk.source not in {s[1].source for s in selected} else 0.0
            mmr = lambda_relevance * rel - (1 - lambda_relevance) * redundancy + source_bonus
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
    chosen_sources = {chunk.source for _, chunk, _ in chosen}
    unique_sources = len(chosen_sources)
    diversity = unique_sources / max(len(chosen), 1)

    corroboration = 0.0
    if len(chosen) >= 2:
        pair_sims = []
        for i in range(len(chosen)):
            for j in range(i + 1, len(chosen)):
                pair_sims.append(_sentence_similarity(chosen[i][2], chosen[j][2]))
        corroboration = sum(pair_sims) / max(len(pair_sims), 1)

    confidence = min(0.92, max(0.2, 0.5 * mean_score + 0.3 * diversity + 0.2 * corroboration))

    risk_flags: list[str] = []
    if len(strong) == 0:
        risk_flags.append("low_evidence")
    if confidence < 0.5:
        risk_flags.append("low_confidence")
    if len(chosen) > 1 and unique_sources == 1:
        risk_flags.append("single_source")
    if corroboration < 0.12 and len(chosen) > 1:
        risk_flags.append("low_corroboration")
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
    idf = _idf_from_chunks(chunks)
    evidence_sents: list[str] = []
    evidence_meta: list[tuple[str, str]] = []  # (source, sentence)
    for c in chunks:
        sents = _sentences(c.text)
        evidence_sents.extend(sents)
        evidence_meta.extend([(c.source, s) for s in sents])

    support_strengths: list[float] = []
    independent_supports: list[float] = []
    question_relevance_scores: list[float] = []
    corroboration_scores: list[float] = []

    for step in trace.steps:
        best_overlap = 0.0
        best_independent = 0.0
        source_scores: dict[str, float] = {}
        contradiction_hit = False
        primary_source_key = step.citations[0].doc_id.split("_")[0].lower() if step.citations else ""

        for source, s in evidence_meta:
            sim = _sentence_similarity(step.text, s)
            if sim > best_overlap:
                best_overlap = sim
            source_scores[source] = max(source_scores.get(source, 0.0), sim)
            if not source.lower().startswith(primary_source_key):
                best_independent = max(best_independent, sim)
            if sim >= 0.45 and (_has_negation(step.text) ^ _has_negation(s)):
                contradiction_hit = True

        corroborating_sources = sum(1 for v in source_scores.values() if v >= CORROBORATE_THRESHOLD)
        corroboration = min(1.0, corroborating_sources / 2.0)

        question_overlap = _question_sentence_score(trace.question, step.text, idf)
        support_strengths.append(best_overlap)
        independent_supports.append(best_independent)
        question_relevance_scores.append(question_overlap)
        corroboration_scores.append(corroboration)

        if contradiction_hit:
            step.audit_label = "contradictory"
            step.audit_explanation = "Potential contradiction detected against retrieved evidence with opposite polarity."
        elif best_overlap >= 0.45 and question_overlap >= STRONG_SENTENCE_SCORE and corroborating_sources >= 2:
            step.audit_label = "supported"
            step.audit_explanation = "Strong evidence overlap, strong relevance, and corroboration from multiple sources."
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
    direct_coverage = sum(min(v / 0.45, 1.0) for v in support_strengths) / max(n, 1)
    independent_coverage = sum(min(v / 0.4, 1.0) for v in independent_supports) / max(n, 1)
    coverage = 0.5 * direct_coverage + 0.5 * independent_coverage
    question_relevance = sum(question_relevance_scores) / max(n, 1)
    corroboration = sum(corroboration_scores) / max(n, 1)
    contradictions = sum(1 for s in trace.steps if s.audit_label == "contradictory")
    # Calibrate alignment by both evidence quality and generation confidence.
    answer_alignment = min(grounding, question_relevance, corroboration + 0.2, trace.confidence)
    raw_overall = (
        grounding * 0.3
        + coverage * 0.15
        + independent_coverage * 0.15
        + question_relevance * 0.2
        + corroboration * 0.1
        + answer_alignment * 0.1
    )
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
