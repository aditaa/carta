import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from campaign_map.models import CampaignMapVersion
from campaign_map.services import (
    CampaignMapImportError,
    image_dimensions,
    import_campaign_map,
    jpeg_dimensions,
)


def write_fake_jpeg(path, *, width=3, height=2):
    path.write_bytes(
        b"\xff\xd8"
        b"\xff\xe0\x00\x10"
        + (b"\x00" * 14)
        + b"\xff\xc0\x00\x11"
        + bytes([8])
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + bytes([3, 1, 0x11, 0, 2, 0x11, 0, 3, 0x11, 0])
        + b"\xff\xd9"
    )


def write_fake_png(path, *, width=3, height=2):
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )


def test_jpeg_dimensions_reads_size_without_pillow(tmp_path):
    image_path = tmp_path / "map.jpg"
    write_fake_jpeg(image_path, width=12, height=7)

    assert jpeg_dimensions(image_path) == (12, 7)


def test_image_dimensions_reads_png_size(tmp_path):
    image_path = tmp_path / "map.png"
    write_fake_png(image_path, width=20, height=11)

    assert image_dimensions(image_path) == (20, 11)


@pytest.mark.django_db
def test_import_campaign_map_creates_active_version(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    image_path = tmp_path / "known-world.jpg"
    write_fake_jpeg(image_path, width=100, height=60)

    result = import_campaign_map(
        image_path,
        version="2026-05-15",
        playable_width=80,
        notes="Opening campaign map.",
    )

    map_version = result.map_version
    assert result.created is True
    assert map_version.is_active is True
    assert map_version.image_width == 100
    assert map_version.image_height == 60
    assert map_version.playable_width == 80
    assert map_version.notes == "Opening campaign map."
    assert (settings.MEDIA_ROOT / map_version.image.name).exists()


@pytest.mark.django_db
def test_import_campaign_map_creates_detail_version(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    image_path = tmp_path / "hellfire.png"
    write_fake_png(image_path, width=100, height=60)

    result = import_campaign_map(
        image_path,
        key="hellfire",
        name="Hellfire",
        version="2025-09-20",
        map_type=CampaignMapVersion.MapType.DETAIL,
        parent_key="known-world",
    )

    map_version = result.map_version
    assert map_version.map_type == CampaignMapVersion.MapType.DETAIL
    assert map_version.parent_key == "known-world"
    assert map_version.playable_width == 100


@pytest.mark.django_db
def test_import_campaign_map_deactivates_previous_active_version(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"
    write_fake_jpeg(first_path)
    write_fake_jpeg(second_path)

    first = import_campaign_map(first_path, version="first").map_version
    second = import_campaign_map(second_path, version="second").map_version

    first.refresh_from_db()
    assert first.is_active is False
    assert second.is_active is True


@pytest.mark.django_db
def test_import_campaign_map_rejects_non_jpeg(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    image_path = tmp_path / "map.gif"
    image_path.write_bytes(b"not a supported image")

    with pytest.raises(CampaignMapImportError):
        import_campaign_map(image_path, version="bad")


@pytest.mark.django_db
def test_import_map_command_imports_file(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    image_path = tmp_path / "known-world.jpg"
    write_fake_jpeg(image_path, width=50, height=30)

    call_command(
        "import_map",
        image_path,
        "--map-version",
        "2026-05-15",
        "--playable-width",
        "40",
    )

    map_version = CampaignMapVersion.objects.get(key="known-world", version="2026-05-15")
    assert map_version.image_width == 50
    assert map_version.playable_width == 40


@pytest.mark.django_db
def test_import_map_command_requires_key_for_detail_map(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    world_path = tmp_path / "known-world.jpg"
    detail_path = tmp_path / "hellfire-detail.jpg"
    write_fake_jpeg(world_path, width=50, height=30)
    write_fake_jpeg(detail_path, width=25, height=15)

    world = import_campaign_map(world_path, version="2026-05-15").map_version

    with pytest.raises(CommandError, match="Detail map imports require --key"):
        call_command(
            "import_map",
            detail_path,
            "--map-version",
            "2026-05-16",
            "--map-type",
            "detail",
        )

    world.refresh_from_db()
    assert world.is_active is True
    assert CampaignMapVersion.objects.count() == 1
