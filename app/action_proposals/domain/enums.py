from enum import StrEnum


class ActionProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"


class ActionExecutionStatus(StrEnum):
    SIMULATED_SUCCESS = "simulated_success"
