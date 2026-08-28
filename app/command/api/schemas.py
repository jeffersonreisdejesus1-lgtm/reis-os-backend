from pydantic import BaseModel


class CommandModeResponse(BaseModel):
    product: str = "REIS OS Command"
    milestone: str = "COMMAND v0.1 — OBSERVAR"
    mode: str = "observational_control_plane"
    private_enforcement: str = "requirement_not_yet_fully_validated"
    source_mutation_authority: str = "none"
    external_source_mutation: bool = False
    institutional_mutation: bool = False
    proposal_creation: bool = False
    external_action_invocation: bool = False
    enforcement: tuple[str, ...] = (
        "allowlist_only",
        "default_deny",
        "fail_closed",
    )
