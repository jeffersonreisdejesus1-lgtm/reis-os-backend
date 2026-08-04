from app.tasks.domain.enums import TaskStatus


class TaskDomainError(Exception):
    """Base exception for task domain rule violations."""


class InvalidTaskTransitionError(TaskDomainError):
    def __init__(self, current: TaskStatus, target: TaskStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Invalid task transition: {current.value} -> {target.value}.")
