from app.command.adapters.base import BaseReadAdapter
from app.command.domain.observation import SourceType


class NotionReadAdapter(BaseReadAdapter):
    expected_source_type = SourceType.NOTION
