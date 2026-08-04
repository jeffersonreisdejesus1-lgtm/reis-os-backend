from enum import StrEnum


class WorkspaceType(StrEnum):
    ATELIER = "atelier"
    DEPARTMENT = "department"
    PROJECT_SPACE = "project_space"
    PERSONAL = "personal"


class WorkspaceStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
