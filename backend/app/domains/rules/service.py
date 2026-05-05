import json
from functools import lru_cache

from app.core.config import get_settings
from app.domains.rules.schemas import RulesDataset


class RulesService:
    def load_current_rules(self) -> RulesDataset:
        settings = get_settings()
        with settings.rules_file.open("r", encoding="utf-8") as rules_file:
            payload = json.load(rules_file)
        return RulesDataset.model_validate(payload)


@lru_cache
def get_rules_service() -> RulesService:
    return RulesService()
