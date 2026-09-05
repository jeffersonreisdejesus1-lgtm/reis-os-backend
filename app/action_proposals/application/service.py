from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.action_proposals.domain.enums import ActionProposalStatus, ExecutionStatus
from app.action_proposals.infrastructure.models import ActionProposalModel
from app.shared.errors.exceptions import AppError


async def create_action_proposal(
    session: AsyncSession,
    *,
    action_type: str,
    target: str,
    payload: dict[str, Any],
    requested_by: str,
) -> ActionProposalModel:
    proposal = ActionProposalModel(
        action_type=action_type.strip(),
        target=target.strip(),
        payload=payload,
        requested_by=requested_by.strip(),
        status=ActionProposalStatus.PENDING,
    )
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)
    return proposal


async def get_action_proposal(
    session: AsyncSession, *, proposal_id: UUID
) -> ActionProposalModel:
    proposal = await session.get(ActionProposalModel, proposal_id)
    if proposal is None:
        raise AppError(
            "Action proposal not found.",
            code="action_proposal_not_found",
            status_code=404,
        )
    return proposal


async def approve_action_proposal(
    session: AsyncSession, *, proposal_id: UUID, approved_by: str
) -> ActionProposalModel:
    proposal = await session.scalar(
        select(ActionProposalModel)
        .where(ActionProposalModel.id == proposal_id)
        .with_for_update()
    )
    if proposal is None:
        raise AppError(
            "Action proposal not found.",
            code="action_proposal_not_found",
            status_code=404,
        )
    if proposal.status != ActionProposalStatus.PENDING:
        raise AppError(
            "Only pending action proposals can be approved.",
            code="action_proposal_not_pending",
            status_code=409,
        )

    proposal.status = ActionProposalStatus.APPROVED
    proposal.approved_by = approved_by.strip()
    proposal.approved_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(proposal)
    return proposal


async def execute_action_proposal(
    session: AsyncSession, *, proposal_id: UUID
) -> ActionProposalModel:
    proposal = await session.scalar(
        select(ActionProposalModel)
        .where(ActionProposalModel.id == proposal_id)
        .with_for_update()
    )
    if proposal is None:
        raise AppError(
            "Action proposal not found.",
            code="action_proposal_not_found",
            status_code=404,
        )
    if proposal.executed_at is not None:
        raise AppError(
            "Action proposal has already been executed.",
            code="action_proposal_already_executed",
            status_code=409,
        )
    if proposal.status != ActionProposalStatus.APPROVED:
        raise AppError(
            "Action proposal must be approved before execution.",
            code="action_proposal_not_approved",
            status_code=409,
        )

    proposal.execution_status = ExecutionStatus.SIMULATED
    proposal.executed_at = datetime.now(UTC)
    proposal.execution_result = {
        "simulated": True,
        "message": "Execution simulated; no external action was performed.",
    }
    await session.commit()
    await session.refresh(proposal)
    return proposal
