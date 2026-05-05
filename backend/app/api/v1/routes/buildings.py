from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.schemas import VisibilityScope
from app.domains.buildings.schemas import (
    BuildingRegistryCreate,
    BuildingRegistryItem,
    BuildingRegistrySummary,
    BuildingRegistryUpdate,
    BuildingUpkeepSummary,
)
from app.domains.buildings.service import (
    BuildingRegistryError,
    OwnedBuildingRecord,
    get_building_registry_service,
)
from app.domains.rules.service import get_rules_service

router = APIRouter()


def get_demo_scope() -> VisibilityScope:
    return VisibilityScope(
        user_id=1,
        visible_user_ids=[1, 2, 3],
        visible_house_ids=[10],
    )


def get_demo_buildings() -> list[OwnedBuildingRecord]:
    return [
        OwnedBuildingRecord(
            id=1,
            owner_user_id=1,
            building_definition_id="farm",
            display_name="North Farm",
            count=2,
        ),
        OwnedBuildingRecord(
            id=2,
            owner_user_id=2,
            house_id=10,
            building_definition_id="market",
            display_name="House Market",
            count=1,
        ),
        OwnedBuildingRecord(
            id=3,
            owner_user_id=4,
            house_id=20,
            building_definition_id="watchtower",
            display_name="Hidden Watchtower",
            count=1,
        ),
    ]


@router.get("", response_model=BuildingRegistrySummary)
def list_buildings() -> BuildingRegistrySummary:
    building_registry_service = get_building_registry_service()

    return BuildingRegistrySummary(
        items=building_registry_service.list_visible(get_demo_buildings(), get_demo_scope()),
        note="Demo data until authenticated database-backed registry endpoints are added.",
    )


@router.get("/upkeep-preview", response_model=BuildingUpkeepSummary)
def upkeep_preview() -> BuildingUpkeepSummary:
    building_registry_service = get_building_registry_service()
    rules = get_rules_service().load_current_rules()
    visible_buildings = building_registry_service.list_visible(
        get_demo_buildings(),
        get_demo_scope(),
    )
    return building_registry_service.calculate_upkeep(visible_buildings, rules)


@router.get("/db", response_model=BuildingRegistrySummary)
def list_db_buildings(
    user_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> BuildingRegistrySummary:
    building_registry_service = get_building_registry_service()
    scope = building_registry_service.build_visibility_scope_from_db(db, user_id)
    return BuildingRegistrySummary(
        items=building_registry_service.list_visible_from_db(db, scope),
        note="Temporary query-param auth until the full user auth system is built.",
    )


@router.post(
    "/db",
    response_model=BuildingRegistryItem,
    status_code=status.HTTP_201_CREATED,
)
def create_db_building(
    payload: BuildingRegistryCreate,
    db: Session = Depends(get_db),
) -> BuildingRegistryItem:
    building_registry_service = get_building_registry_service()
    rules = get_rules_service().load_current_rules()
    try:
        return building_registry_service.create_in_db(db, payload, rules)
    except BuildingRegistryError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get("/db/{building_id}", response_model=BuildingRegistryItem)
def get_db_building(
    building_id: int,
    user_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> BuildingRegistryItem:
    building_registry_service = get_building_registry_service()
    scope = building_registry_service.build_visibility_scope_from_db(db, user_id)
    building = building_registry_service.get_visible_from_db(db, building_id, scope)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    return building


@router.patch("/db/{building_id}", response_model=BuildingRegistryItem)
def update_db_building(
    building_id: int,
    payload: BuildingRegistryUpdate,
    user_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> BuildingRegistryItem:
    building_registry_service = get_building_registry_service()
    scope = building_registry_service.build_visibility_scope_from_db(db, user_id)
    rules = get_rules_service().load_current_rules()
    try:
        building = building_registry_service.update_visible_in_db(
            db,
            building_id,
            payload,
            scope,
            rules,
        )
    except BuildingRegistryError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    return building


@router.delete("/db/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_db_building(
    building_id: int,
    user_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> None:
    building_registry_service = get_building_registry_service()
    scope = building_registry_service.build_visibility_scope_from_db(db, user_id)
    if not building_registry_service.delete_visible_from_db(db, building_id, scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
