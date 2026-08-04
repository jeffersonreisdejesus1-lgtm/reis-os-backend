from app.shared.errors.exceptions import AppError
from app.workspaces.domain.enums import WorkspaceStatus


def archive_workspace(current: WorkspaceStatus) -> WorkspaceStatus:
    if current == WorkspaceStatus.ARCHIVED:
        raise AppError(
            "Workspace is already archived.",
            code="invalid_workspace_transition",
            status_code=409,
        )
    return WorkspaceStatus.ARCHIVED
