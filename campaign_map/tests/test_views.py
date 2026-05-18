import pytest
from django.urls import reverse

from campaign_map.models import CampaignMapVersion


def create_user(email="map@example.test"):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name="Map User",
    )


@pytest.mark.django_db
def test_map_page_requires_login(client):
    response = client.get(reverse("campaign_map:index"))

    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_map_page_shows_empty_state_without_imported_map(client):
    client.force_login(create_user())

    response = client.get(reverse("campaign_map:index"))

    assert response.status_code == 200
    assert b"Campaign Map" in response.content
    assert b"No campaign map has been imported yet." in response.content
    assert b"map-canvas" not in response.content


@pytest.mark.django_db
def test_map_page_renders_active_map_canvas(client):
    client.force_login(create_user())
    CampaignMapVersion.objects.create(
        key="known-world",
        name="Known World",
        version="2026-05-15",
        map_type=CampaignMapVersion.MapType.WORLD,
        image="campaign_maps/known-world/2026-05-15.jpg",
        image_width=5234,
        image_height=3072,
        playable_width=4096,
        source_path="maps/known-world/known-world-2026-05-15.jpg",
    )

    response = client.get(reverse("campaign_map:index"))

    assert response.status_code == 200
    assert b"Known World 2026-05-15" in response.content
    assert b"map-canvas" in response.content
    assert b"campaign_maps/known-world/2026-05-15.jpg" in response.content
    assert b"Fit" in response.content


@pytest.mark.django_db
def test_map_page_can_select_detail_map(client):
    client.force_login(create_user())
    CampaignMapVersion.objects.create(
        key="known-world",
        name="Known World",
        version="2026-05-15",
        map_type=CampaignMapVersion.MapType.WORLD,
        image="campaign_maps/known-world/2026-05-15.jpg",
        image_width=5234,
        image_height=3072,
        playable_width=4096,
        source_path="maps/known-world/known-world-2026-05-15.jpg",
    )
    CampaignMapVersion.objects.create(
        key="hellfire",
        name="Hellfire",
        version="2025-09-20",
        map_type=CampaignMapVersion.MapType.DETAIL,
        parent_key="known-world",
        image="campaign_maps/hellfire/2025-09-20.png",
        image_width=2000,
        image_height=1600,
        playable_width=2000,
        source_path="maps/known-world/details/hellfire-2025-09-20.png",
    )

    response = client.get(reverse("campaign_map:index"), {"map": "hellfire"})

    assert response.status_code == 200
    assert b"Hellfire 2025-09-20" in response.content
    assert b"campaign_maps/hellfire/2025-09-20.png" in response.content
    assert b"Known World" in response.content
