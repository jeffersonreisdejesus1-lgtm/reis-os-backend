from pathlib import Path

from app.main import COMMAND_UI, app


def test_b10_frontend_reuses_observar_lineage_with_current_contracts() -> None:
    html = Path(COMMAND_UI).read_text(encoding="utf-8")

    assert "REIS OS Command" in html
    assert "evolução da baseline OBSERVAR" in html
    assert "Situação atual" in html
    assert "OURO · estado e verdade operacional" in html
    assert "PRATA · inteligência e augmentação" in html
    assert "OCS / IA" in html
    assert "/auth/login" in html
    assert "/organizations" in html
    assert "/v1/command/cockpit" in html
    assert "/v1/command/modules/cupuwa-inspired" in html
    assert "/v1/command/ocs-inference/plan" in html
    assert "não invoca um modelo nem executa efeito material" in html


def test_b10_frontend_preserves_epistemic_labels_and_no_direct_state_write() -> None:
    html = Path(COMMAND_UI).read_text(encoding="utf-8")

    assert "FATO" in html
    assert "INFERÊNCIA" in html
    assert "AÇÃO PROPOSTA" in html
    assert "não cria autoridade" in html
    assert "não executa efeito material" in html or "nem executa efeito material" in html
    assert "canonical_state_write" in html


def test_b10_frontend_is_served_on_legacy_compatible_routes() -> None:
    routes = {
        route.path: set(getattr(route, "methods", set()) or set())
        for route in app.routes
        if hasattr(route, "path")
    }

    assert "/" in routes
    assert "/command-ui" in routes
    assert routes["/"] == {"GET"}
    assert routes["/command-ui"] == {"GET"}
