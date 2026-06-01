from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class InputValue:
    item_id: str
    label: str
    value: int | float | str | None
    unit: str
    source: str
    trace: list[str] = field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "high"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FillPlanItem:
    item_id: str
    label: str
    sheet: str
    cell: str
    value: int | float | str | None
    source: str
    trace: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UnresolvedItem:
    item_id: str
    label: str
    reason: str
    candidates: list[str] = field(default_factory=list)

    def to_row(self) -> dict[str, str]:
        return {
            "item_id": self.item_id,
            "label": self.label,
            "reason": self.reason,
            "candidates": " | ".join(self.candidates),
        }


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    item_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditEvent:
    event: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

