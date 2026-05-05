from fastapi import APIRouter, Depends

from app.domains.rules.schemas import RulesDataset
from app.domains.rules.service import RulesService, get_rules_service

router = APIRouter()


@router.get("/current", response_model=RulesDataset)
def get_current_rules(
    rules_service: RulesService = Depends(get_rules_service),
) -> RulesDataset:
    return rules_service.load_current_rules()
