# Import all ORM models so Alembic can discover their metadata.
from app.action_proposals.infrastructure.models import ActionProposalModel
from app.audit.infrastructure.models import AuditEventModel
from app.memberships.infrastructure.models import MembershipModel
from app.organizations.infrastructure.models import OrganizationModel
from app.projects.infrastructure.models import ProjectModel
from app.tasks.infrastructure.models import TaskModel
from app.users.infrastructure.models import UserModel
from app.workspaces.infrastructure.models import WorkspaceModel

__all__ = [
    "ActionProposalModel",
    "AuditEventModel",
    "MembershipModel",
    "OrganizationModel",
    "ProjectModel",
    "TaskModel",
    "UserModel",
    "WorkspaceModel",
]
