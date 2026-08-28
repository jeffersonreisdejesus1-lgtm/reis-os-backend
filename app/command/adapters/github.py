from app.command.adapters.base import BaseReadAdapter
from app.command.domain.observation import SourceType


class GitHubReadAdapter(BaseReadAdapter):
    expected_source_type = SourceType.GITHUB
