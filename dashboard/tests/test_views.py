from django.urls import reverse


def test_home_page_returns_success(client):
    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 200
    assert b"Carta Arcanum" in response.content
    assert b"Sign in" in response.content


def test_health_page_returns_json(client):
    response = client.get(reverse("dashboard:health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Carta Arcanum"}
