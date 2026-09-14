from app.carousel_runtime import CarouselRuntime
from app.carousel_runtime.domain import CarouselIntent, CarouselPhase

def test_runtime_returns_complete_cos_manifest():
    result = CarouselRuntime().create(CarouselIntent(topic="uma IA que constrói"))
    project = result["project"]
    assert result["contract"] == "COS-v1"
    assert project["phase"] == CarouselPhase.DELIVERED.value
    assert len(project["slides"]) == 6
    assert project["qa"]["status"] == "PASS"

def test_runtime_is_deterministic_for_same_topic():
    intent = CarouselIntent(topic="sistemas de IA")
    assert CarouselRuntime().create(intent) == CarouselRuntime().create(intent)
