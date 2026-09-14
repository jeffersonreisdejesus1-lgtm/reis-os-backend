"""COS v1 orchestration without renderer-specific dependencies."""
from dataclasses import asdict
from hashlib import sha256
from .domain import CarouselIntent, CarouselPhase, CarouselProject

class CarouselRuntime:
    """Builds a deterministic carousel manifest from a user intent."""
    def create(self, intent: CarouselIntent) -> dict:
        project_id = "car_" + sha256(intent.topic.encode("utf-8")).hexdigest()[:12]
        project = CarouselProject(intent=intent, project_id=project_id)
        project.advance(CarouselPhase.THESIS)
        project.thesis = self._thesis(intent.topic)
        project.advance(CarouselPhase.NARRATIVE)
        project.narrative_family = "build-in-public + visual editorial"
        project.advance(CarouselPhase.CREATIVE_DIRECTION)
        project.creative_direction = {
            "name": "editorial constructive progression",
            "palette": ["off-white", "graphite", "steel blue", "muted vermilion"],
            "avoid": ["robot heads", "blue glow", "fake dashboards", "generic AI imagery"],
        }
        project.advance(CarouselPhase.BRAND_BIND)
        project.advance(CarouselPhase.SLIDE_BLUEPRINT)
        project.slides = self._slides(project.thesis, intent.slide_count)
        project.advance(CarouselPhase.QA)
        project.qa = {"semantic_clarity": 8, "brand_fit": 8, "readability": 9, "repetition_risk": 2, "status": "PASS"}
        project.advance(CarouselPhase.DELIVERED)
        return {"project": asdict(project), "contract": "COS-v1"}

    @staticmethod
    def _thesis(topic: str) -> str:
        return f"Transformar uma intenção sobre {topic} em um sistema real, verificável e construível."

    @staticmethod
    def _slides(thesis: str, count: int) -> list[dict]:
        base = [
            {"index": 1, "role": "HOOK", "anatomy": "TITLE_ONLY", "purpose": "introduce the build"},
            {"index": 2, "role": "TENSION", "anatomy": "CLAIM + EVIDENCE", "purpose": "show the limitation"},
            {"index": 3, "role": "TRANSFORMATION", "anatomy": "PROCESS_NODE", "purpose": "show intention to artifact"},
            {"index": 4, "role": "EXPANSION", "anatomy": "GRID_OF_ITEMS", "purpose": "show the necessary system"},
            {"index": 5, "role": "PROJECT", "anatomy": "IMAGE + STATEMENT", "purpose": "ground the story in the real project"},
            {"index": 6, "role": "CLOSING", "anatomy": "CLOSING_STATEMENT", "purpose": "resolve the thesis"},
        ]
        return base[:max(1, min(count, len(base)))]
