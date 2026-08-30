from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.action_proposals.api.schemas import (
    ActionProposalApproveRequest,
    ActionProposalCreateRequest,
    ActionProposalResponse,
)
from app.action_proposals.application.service import (
    approve_action_proposal,
    create_action_proposal,
    execute_action_proposal,
    get_action_proposal,
)
from app.auth.api.dependencies import CurrentUser
from app.shared.database.session import get_db_session

router = APIRouter(prefix="/action-proposals", tags=["action-proposals"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=ActionProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    payload: ActionProposalCreateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> ActionProposalResponse:
    proposal = await create_action_proposal(session, **payload.model_dump())
    return ActionProposalResponse.model_validate(proposal)


@router.post("/{proposal_id}/approve", response_model=ActionProposalResponse)
async def approve(
    proposal_id: UUID,
    payload: ActionProposalApproveRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> ActionProposalResponse:
    proposal = await approve_action_proposal(
        session, proposal_id=proposal_id, approved_by=payload.approved_by
    )
    return ActionProposalResponse.model_validate(proposal)


@router.post("/{proposal_id}/execute", response_model=ActionProposalResponse)
async def execute(
    proposal_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> ActionProposalResponse:
    proposal = await execute_action_proposal(session, proposal_id=proposal_id)
    return ActionProposalResponse.model_validate(proposal)


@router.get("/{proposal_id}", response_model=ActionProposalResponse)
async def get(
    proposal_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> ActionProposalResponse:
    proposal = await get_action_proposal(session, proposal_id=proposal_id)
    return ActionProposalResponse.model_validate(proposal)
