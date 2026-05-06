from dataclasses import dataclass, field
from typing import Literal, Optional

AuditLabel = Literal["supported", "weak", "unsupported", "contradictory", "speculative"]

@dataclass
class Document:
    doc_id: str
    source: str
    title: str
    url: str
    content: str
    published_at: str = ""

@dataclass
class Citation:
    doc_id: str
    title: str
    url: str
    snippet: str

@dataclass
class ReasoningStep:
    step_id: int
    text: str
    label: str                          # inference | observation | conclusion
    citations: list[Citation] = field(default_factory=list)
    audit_label: AuditLabel = "unsupported"
    audit_explanation: str = ""

@dataclass
class ReasoningTrace:
    question: str
    answer: str
    confidence: float
    risk_flags: list[str]
    steps: list[ReasoningStep]

@dataclass
class AuditScore:
    grounding_score: float              # 0–1: fraction of steps that are supported/weak
    evidence_coverage: float            # 0–1: fraction of steps with ≥1 citation
    contradiction_count: int
    answer_alignment: float             # 0–1: Claude self-scores
    overall: float                      # weighted composite
