from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.auth.models import HouseMembership
from app.domains.auth.schemas import VisibilityScope
from app.domains.buildings.models import OwnedBuilding
from app.domains.buildings.schemas import (
    BuildingRegistryCreate,
    BuildingRegistryItem,
    BuildingRegistryUpdate,
    BuildingUpkeepLine,
    BuildingUpkeepSummary,
)
from app.domains.rules.schemas import RulesDataset, RulesRef


class BuildingRegistryError(ValueError):
    pass


class BuildingRegistryPermissionError(PermissionError):
    pass


@dataclass(frozen=True)
class OwnedBuildingRecord:
    id: int
    owner_denizen_id: int
    building_definition_id: str
    count: int
    house_id: int | None = None
    display_name: str | None = None


class BuildingRegistryService:
    def build_visibility_scope_from_db(
        self,
        db: Session,
        denizen_id: int,
    ) -> VisibilityScope:
        house_ids = [
            row.house_id
            for row in db.scalars(
                select(HouseMembership).where(
                    HouseMembership.denizen_id == denizen_id,
                    HouseMembership.can_view_house.is_(True),
                )
            )
        ]
        visible_denizen_ids = {denizen_id}
        if house_ids:
            visible_denizen_ids.update(
                db.scalars(
                    select(HouseMembership.denizen_id).where(
                        HouseMembership.house_id.in_(house_ids)
                    )
                )
            )

        return VisibilityScope(
            denizen_id=denizen_id,
            visible_denizen_ids=sorted(visible_denizen_ids),
            visible_house_ids=sorted(set(house_ids)),
        )

    def list_visible(
        self,
        buildings: list[OwnedBuildingRecord],
        visibility_scope: VisibilityScope,
    ) -> list[BuildingRegistryItem]:
        visible_house_ids = set(visibility_scope.visible_house_ids)
        visible_buildings = [
            building
            for building in buildings
            if building.owner_denizen_id == visibility_scope.denizen_id
            or (building.house_id is not None and building.house_id in visible_house_ids)
        ]

        return [
            BuildingRegistryItem(
                id=building.id,
                owner_denizen_id=building.owner_denizen_id,
                house_id=building.house_id,
                building_definition_id=building.building_definition_id,
                display_name=building.display_name,
                count=building.count,
            )
            for building in visible_buildings
        ]

    def list_visible_from_db(
        self,
        db: Session,
        visibility_scope: VisibilityScope,
    ) -> list[BuildingRegistryItem]:
        records = db.scalars(select(OwnedBuilding).order_by(OwnedBuilding.id)).all()
        return [
            self._item_from_model(record)
            for record in records
            if self._is_visible(record, visibility_scope)
        ]

    def get_visible_from_db(
        self,
        db: Session,
        building_id: int,
        visibility_scope: VisibilityScope,
    ) -> BuildingRegistryItem | None:
        record = db.get(OwnedBuilding, building_id)
        if record is None or not self._is_visible(record, visibility_scope):
            return None
        return self._item_from_model(record)

    def create_in_db(
        self,
        db: Session,
        payload: BuildingRegistryCreate,
        visibility_scope: VisibilityScope,
        rules: RulesDataset,
    ) -> BuildingRegistryItem:
        self.validate_building_definition_id(payload.building_definition_id, rules)
        self.validate_create_permission(payload, visibility_scope)
        record = OwnedBuilding(
            owner_denizen_id=payload.owner_denizen_id,
            house_id=payload.house_id,
            building_definition_id=payload.building_definition_id,
            display_name=payload.display_name,
            count=payload.count,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._item_from_model(record)

    def update_visible_in_db(
        self,
        db: Session,
        building_id: int,
        payload: BuildingRegistryUpdate,
        visibility_scope: VisibilityScope,
        rules: RulesDataset,
    ) -> BuildingRegistryItem | None:
        record = db.get(OwnedBuilding, building_id)
        if record is None or not self._is_visible(record, visibility_scope):
            return None

        changes = payload.model_dump(exclude_unset=True)
        building_definition_id = changes.get("building_definition_id")
        if building_definition_id is not None:
            self.validate_building_definition_id(building_definition_id, rules)

        for key, value in changes.items():
            setattr(record, key, value)

        db.commit()
        db.refresh(record)
        return self._item_from_model(record)

    def delete_visible_from_db(
        self,
        db: Session,
        building_id: int,
        visibility_scope: VisibilityScope,
    ) -> bool:
        record = db.get(OwnedBuilding, building_id)
        if record is None or not self._is_visible(record, visibility_scope):
            return False

        db.delete(record)
        db.commit()
        return True

    def aggregate_counts_by_owner(
        self,
        buildings: list[BuildingRegistryItem],
    ) -> dict[int, dict[str, int]]:
        totals: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for building in buildings:
            totals[building.owner_denizen_id][building.building_definition_id] += building.count

        return {owner_id: dict(building_totals) for owner_id, building_totals in totals.items()}

    def validate_create_permission(
        self,
        payload: BuildingRegistryCreate,
        visibility_scope: VisibilityScope,
    ) -> None:
        if payload.house_id is None:
            if payload.owner_denizen_id == visibility_scope.denizen_id:
                return
            raise BuildingRegistryPermissionError(
                "Cannot create personal building records for another denizen"
            )

        if payload.house_id in set(
            visibility_scope.visible_house_ids
        ) and payload.owner_denizen_id in set(visibility_scope.visible_denizen_ids):
            return

        raise BuildingRegistryPermissionError(
            "Cannot create building records outside the caller's visible house scope"
        )

    def validate_building_definition_id(
        self,
        building_definition_id: str,
        rules: RulesDataset,
    ) -> None:
        known_building_keys = {building.key for building in rules.building_definitions}
        if building_definition_id not in known_building_keys:
            raise BuildingRegistryError(f"Unknown building definition id: {building_definition_id}")

    def validate_building_definitions(
        self,
        buildings: list[OwnedBuildingRecord] | list[BuildingRegistryItem],
        rules: RulesDataset,
    ) -> None:
        known_building_keys = {building.key for building in rules.building_definitions}
        unknown_keys = sorted(
            {
                building.building_definition_id
                for building in buildings
                if building.building_definition_id not in known_building_keys
            }
        )
        if unknown_keys:
            raise BuildingRegistryError(
                "Unknown building definition ids: " + ", ".join(unknown_keys)
            )

    def calculate_upkeep(
        self,
        buildings: list[BuildingRegistryItem],
        rules: RulesDataset,
    ) -> BuildingUpkeepSummary:
        self.validate_building_definitions(buildings, rules)
        building_rules = {building.key: building for building in rules.building_definitions}
        lines: list[BuildingUpkeepLine] = []
        totals: dict[tuple[str, str], float] = defaultdict(float)

        for building in buildings:
            rule = building_rules[building.building_definition_id]
            line_upkeep = [
                RulesRef(
                    item_type=upkeep.item_type,
                    item_key=upkeep.item_key,
                    amount=upkeep.amount * building.count,
                )
                for upkeep in rule.upkeep
            ]
            for upkeep in line_upkeep:
                totals[(upkeep.item_type, upkeep.item_key)] += upkeep.amount
            lines.append(
                BuildingUpkeepLine(
                    building_registry_id=building.id,
                    building_definition_id=building.building_definition_id,
                    count=building.count,
                    upkeep=line_upkeep,
                )
            )

        return BuildingUpkeepSummary(
            lines=lines,
            totals=[
                RulesRef(item_type=item_type, item_key=item_key, amount=amount)
                for (item_type, item_key), amount in sorted(totals.items())
            ],
        )

    def _item_from_model(self, record: OwnedBuilding) -> BuildingRegistryItem:
        return BuildingRegistryItem(
            id=record.id,
            owner_denizen_id=record.owner_denizen_id,
            house_id=record.house_id,
            building_definition_id=record.building_definition_id,
            display_name=record.display_name,
            count=record.count,
        )

    def _is_visible(
        self,
        record: OwnedBuilding,
        visibility_scope: VisibilityScope,
    ) -> bool:
        return record.owner_denizen_id == visibility_scope.denizen_id or (
            record.house_id is not None
            and record.house_id in set(visibility_scope.visible_house_ids)
        )


def get_building_registry_service() -> BuildingRegistryService:
    return BuildingRegistryService()
