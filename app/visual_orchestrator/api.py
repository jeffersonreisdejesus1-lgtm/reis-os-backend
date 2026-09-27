from fastapi import FastAPI

from .core import NormativeUnit, VisualOrchestrator

app = FastAPI(title="Reis OS Visual Production Orchestrator", version="0.1.0")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "component": "visual-production-orchestrator",
        "material_provider_bound": False,
        "fail_closed": True,
    }


@app.get("/capabilities")
def capabilities() -> dict[str, object]:
    return {
        "context_resolution": True,
        "execution_contracts": True,
        "provider_boundary": True,
        "independent_readback_contract": True,
        "material_visual_effect": False,
    }


@app.post("/qualify")
def qualify() -> dict[str, object]:
    engine = VisualOrchestrator(
        rules=[
            NormativeUnit(
                unit_id="MASTER-IDENTITY-V1.1",
                source="DOCUMENTARY-MAPPING-SINGLE-GATE-001",
                scope="GLOBAL",
                authority="Jefferson Reis",
                temporal_status="VIGENTE",
                specificity=1,
                invariant="layer2_identity",
                materialization="single_final_prompt",
            )
        ]
    )
    contract = engine.contract(
        mission_id="VPO-END2END-20260926-001",
        brand="Jefferson Reis",
        language="Artificial Real",
        artifact_id="qualification",
        card_id="01",
        canonical_copy="QUALIFICATION",
        provider="UNBOUND",
    )
    return {
        "qualification": "PASS_PRE_MATERIAL",
        "contract_digest": contract.digest(),
        "material_effect": "HOLD_UNTIL_PROVIDER_BOUND",
    }
