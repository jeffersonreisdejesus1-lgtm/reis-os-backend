from enum import StrEnum


class ActionProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"


class ExecutionStatus(StrEnum):
    SIMULATED = "simulated"
