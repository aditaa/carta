from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils.text import slugify

from campaign_map.models import CampaignMapVersion


class CampaignMapImportError(ValueError):
    pass


@dataclass(frozen=True)
class CampaignMapImportResult:
    map_version: CampaignMapVersion
    created: bool


def active_map() -> CampaignMapVersion | None:
    return selected_map()


def active_maps() -> list[CampaignMapVersion]:
    return list(CampaignMapVersion.objects.filter(is_active=True))


def selected_map(key: str | None = None) -> CampaignMapVersion | None:
    maps = CampaignMapVersion.objects.filter(is_active=True)
    if key:
        match = maps.filter(key=key).order_by("-imported_at", "-id").first()
        if match is not None:
            return match
    return (
        maps.filter(map_type=CampaignMapVersion.MapType.WORLD)
        .order_by("-imported_at", "-id")
        .first()
        or maps.order_by("-imported_at", "-id").first()
    )


def import_campaign_map(
    map_path: Path,
    *,
    key: str = "known-world",
    name: str = "Known World",
    version: str,
    map_type: str = CampaignMapVersion.MapType.WORLD,
    parent_key: str = "",
    playable_width: int | None = None,
    hex_size: float = 22,
    hex_origin_x: float = 7,
    hex_origin_y: float = 12,
    notes: str = "",
    activate: bool = True,
) -> CampaignMapImportResult:
    map_path = map_path.resolve()
    if not map_path.exists():
        raise CampaignMapImportError(f"Map file does not exist: {map_path}")
    if not map_path.is_file():
        raise CampaignMapImportError(f"Map path is not a file: {map_path}")

    width, height = image_dimensions(map_path)
    playable_width = playable_width or width
    if playable_width <= 0 or playable_width > width:
        raise CampaignMapImportError(
            "Playable width must be greater than 0 and no wider than the image."
        )

    normalized_key = slugify(key)
    if not normalized_key:
        raise CampaignMapImportError("Map key must contain at least one slug-safe character.")
    normalized_parent_key = slugify(parent_key) if parent_key else ""
    if map_type not in CampaignMapVersion.MapType.values:
        raise CampaignMapImportError(f"Unsupported map type: {map_type}")

    storage_name = _copy_map_file(map_path, key=normalized_key, version=version)
    with transaction.atomic():
        if activate:
            CampaignMapVersion.objects.filter(key=normalized_key, is_active=True).update(
                is_active=False
            )
        map_version, created = CampaignMapVersion.objects.update_or_create(
            key=normalized_key,
            version=version,
            defaults={
                "name": name,
                "map_type": map_type,
                "parent_key": normalized_parent_key,
                "image": storage_name,
                "image_width": width,
                "image_height": height,
                "playable_width": playable_width,
                "hex_size": hex_size,
                "hex_origin_x": hex_origin_x,
                "hex_origin_y": hex_origin_y,
                "source_path": str(map_path),
                "notes": notes,
                "is_active": activate,
            },
        )
    return CampaignMapImportResult(map_version=map_version, created=created)


def image_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image_file:
        header = image_file.read(24)
    if header.startswith(b"\xff\xd8"):
        return jpeg_dimensions(path)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return png_dimensions(header)
    raise CampaignMapImportError("Map image must be a JPEG or PNG file.")


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image_file:
        if image_file.read(2) != b"\xff\xd8":
            raise CampaignMapImportError("Map image must be a JPEG file.")

        while True:
            marker_start = image_file.read(1)
            if not marker_start:
                break
            if marker_start != b"\xff":
                continue

            marker = image_file.read(1)
            while marker == b"\xff":
                marker = image_file.read(1)
            if marker in {b"\x01"} or b"\xd0" <= marker <= b"\xd9":
                continue

            length_bytes = image_file.read(2)
            if len(length_bytes) != 2:
                break
            segment_length = int.from_bytes(length_bytes, "big")
            if segment_length < 2:
                break

            if marker in {
                b"\xc0",
                b"\xc1",
                b"\xc2",
                b"\xc3",
                b"\xc5",
                b"\xc6",
                b"\xc7",
                b"\xc9",
                b"\xca",
                b"\xcb",
                b"\xcd",
                b"\xce",
                b"\xcf",
            }:
                segment = image_file.read(segment_length - 2)
                if len(segment) < 5:
                    break
                height = int.from_bytes(segment[1:3], "big")
                width = int.from_bytes(segment[3:5], "big")
                return width, height

            image_file.seek(segment_length - 2, 1)

    raise CampaignMapImportError("Could not read JPEG dimensions.")


def png_dimensions(header: bytes) -> tuple[int, int]:
    if len(header) < 24:
        raise CampaignMapImportError("Could not read PNG dimensions.")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width <= 0 or height <= 0:
        raise CampaignMapImportError("Could not read PNG dimensions.")
    return width, height


def _copy_map_file(map_path: Path, *, key: str, version: str) -> str:
    suffix = map_path.suffix.lower() or ".jpg"
    filename = f"{slugify(version) or 'map'}{suffix}"
    storage_name = f"campaign_maps/{key}/{filename}"
    if default_storage.exists(storage_name):
        default_storage.delete(storage_name)
    with map_path.open("rb") as source:
        return default_storage.save(storage_name, File(source))
