"""Domain contracts for COS v1 carousel projects."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class CarouselPhase(str, Enum):
    BRIEF = "BRIEF"
    THESIS = "THESIS"
    NARRATIVE = "NARRATIVE"
    CREATIVE_DIRECTION = "CREATIVE_DIRECTION"
    BRAND_BIND = "BRAND_BIND"
    SLIDE_BLUEPRINT = "SLIDE_BLUEPRINT"
    QA = "QA"
    DELIVERED = "DELIVERED"

@dataclass(frozen=True)
class CarouselIntent:
    topic: str
    objective: str = "build awareness"
    audience: str = "general"
    platform: str = "instagram"
    slide_count: int = 6
    tone: str = "clear, editorial and intelligent"

@dataclass
class CarouselProject:
    intent: CarouselIntent
    project_id: str
    phase: CarouselPhase = CarouselPhase.BRIEF
    thesis: str | None = None
    narrative_family: str | None = None
    creative_direction: dict[str, Any] | None = None
    slides: list[dict[str, Any]] = field(default_factory=list)
    qa: dict[str, Any] | None = None

    def advance(self, phase: CarouselPhase) -> None:
        self.phase = phase
