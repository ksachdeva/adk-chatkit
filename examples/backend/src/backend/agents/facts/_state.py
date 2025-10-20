from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Iterable, List
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class FactStatus(str, Enum):
    """Lifecycle states for collected facts."""

    PENDING = "pending"
    SAVED = "saved"
    DISCARDED = "discarded"


class Fact(BaseModel):
    """Represents a single fact gathered from the conversation."""

    text: str
    status: FactStatus = FactStatus.PENDING
    id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: str


class FactContext(BaseModel):
    facts: Dict[str, Fact] = Field(default_factory=dict)
    order: List[str] = Field(default_factory=list)

    async def create(self, *, text: str) -> Fact:
        """Create a pending fact and return it."""
        fact = Fact(text=text, created_at=_now_iso())
        self.facts[fact.id] = fact
        self.order.append(fact.id)
        return fact

    async def mark_saved(self, fact_id: str) -> Fact | None:
        """Mark the given fact as saved, returning the updated record."""
        fact = self.facts.get(fact_id)
        if fact is None:
            return None
        fact.status = FactStatus.SAVED
        return fact

    async def discard(self, fact_id: str) -> Fact | None:
        """Discard the fact and remove it from the active list."""
        fact = self.facts.get(fact_id)
        if fact is None:
            return None
        fact.status = FactStatus.DISCARDED
        return fact

    async def list_saved(self) -> List[Fact]:
        """Return saved facts in insertion order."""
        return [self.facts[fact_id] for fact_id in self.order if self.facts[fact_id].status == FactStatus.SAVED]

    async def get(self, fact_id: str) -> Fact | None:
        return self.facts.get(fact_id)

    async def iter_pending(self) -> Iterable[Fact]:
        return [fact for fact in self.facts.values() if fact.status == FactStatus.PENDING]
