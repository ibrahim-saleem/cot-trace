"""
reason.py
Two-pass Groq pipeline:
  Pass 1: generate structured reasoning trace from retrieved chunks
  Pass 2: audit each reasoning step against the same chunks
"""
import json
import re
import os
from pathlib import Path
from groq import Groq
from src.schemas import (
    Citation, ReasoningStep, ReasoningTrace, AuditScore
)
from src.retrieve import Chunk

MODEL = "llama-3.3-70b-versatile"

REASONING_PROMPT = (Path(__file__).parent.parent / "prompts" / "reasoning_prompt.md").read_text()
AUDIT_PROMPT     = (Path(__file__).parent.parent / "prompts" / "audit_prompt.md").read_text()


def _format_passages(chunks: list[Chunk]) -> str:
    parts = []
    for c in chunks:
        parts.append(
            f"[doc_id: {c.doc_id}]\n"
            f"Source: {c.source}\n"
            f"Title: {c.title}\n"
            f"URL: {c.url}\n"
            f"---\n{c.text}\n"
        )
    return "\n\n".join(parts)


def _safe_parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def _build_trace(data: dict) -> ReasoningTrace:
    steps = []
    for s in data.get("steps", []):
        citations = [
            Citation(
                doc_id=c.get("doc_id", ""),
                title=c.get("title", ""),
                url=c.get("url", ""),
                snippet=c.get("snippet", ""),
            )
            for c in s.get("citations", [])
        ]
        steps.append(ReasoningStep(
            step_id=s["step_id"],
            text=s["text"],
            label=s.get("label", "inference"),
            citations=citations,
        ))
    return ReasoningTrace(
        question=data["question"],
        answer=data["answer"],
        confidence=float(data.get("confidence", 0.5)),
        risk_flags=data.get("risk_flags", []),
        steps=steps,
    )


def get_client():
    return Groq(api_key=os.environ["ANTHROPIC_API_KEY"])


def generate_trace(client: Groq, question: str, chunks: list[Chunk]) -> ReasoningTrace:
    passages = _format_passages(chunks)
    prompt = REASONING_PROMPT.replace("{passages}", passages).replace("{question}", question)

    msg = client.chat.completions.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.choices[0].message.content
    data = _safe_parse_json(raw)
    return _build_trace(data)


def audit_trace(client: Groq, trace: ReasoningTrace, chunks: list[Chunk]) -> tuple[ReasoningTrace, AuditScore]:
    passages = _format_passages(chunks)
    trace_json = json.dumps({
        "answer": trace.answer,
        "steps": [
            {
                "step_id": s.step_id,
                "text": s.text,
                "label": s.label,
                "citations": [c.__dict__ for c in s.citations],
            }
            for s in trace.steps
        ],
    }, indent=2)

    prompt = AUDIT_PROMPT.replace("{passages}", passages).replace("{trace}", trace_json)
    msg = client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.choices[0].message.content
    data = _safe_parse_json(raw)

    audit_map = {a["step_id"]: a for a in data.get("step_audits", [])}
    for step in trace.steps:
        audit = audit_map.get(step.step_id, {})
        step.audit_label = audit.get("audit_label", "unsupported")
        step.audit_explanation = audit.get("audit_explanation", "")

    label_weights = {"supported": 1.0, "weak": 0.5, "unsupported": 0.0, "contradictory": 0.0, "speculative": 0.2}
    n = len(trace.steps)
    grounding = sum(label_weights.get(s.audit_label, 0) for s in trace.steps) / max(n, 1)
    coverage  = sum(1 for s in trace.steps if s.citations) / max(n, 1)
    contradictions = sum(1 for s in trace.steps if s.audit_label == "contradictory")
    answer_alignment = float(data.get("answer_alignment", 0.5))
    overall = round((grounding * 0.4 + coverage * 0.3 + answer_alignment * 0.3), 3)

    score = AuditScore(
        grounding_score=round(grounding, 3),
        evidence_coverage=round(coverage, 3),
        contradiction_count=contradictions,
        answer_alignment=answer_alignment,
        overall=overall,
    )
    return trace, score