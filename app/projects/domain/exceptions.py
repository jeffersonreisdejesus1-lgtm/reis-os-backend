from app.projects.domain.enums import ProjectStatus


class ProjectDomainError(Exception):
    """Base exception for project domain rule violations."""


class InvalidProjectTransitionError(ProjectDomainError):
    def __init__(self, current: ProjectStatus, target: ProjectStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid project transition: {current.value} -> {target.value}."
        )
