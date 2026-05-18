from django.db import models


class CampaignMapVersion(models.Model):
    class MapType(models.TextChoices):
        WORLD = "world", "World"
        DETAIL = "detail", "Detail"

    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=160)
    version = models.CharField(max_length=80)
    map_type = models.CharField(max_length=20, choices=MapType.choices, default=MapType.WORLD)
    parent_key = models.SlugField(max_length=120, blank=True)
    image = models.FileField(upload_to="campaign_maps/")
    image_width = models.PositiveIntegerField()
    image_height = models.PositiveIntegerField()
    playable_width = models.PositiveIntegerField()
    hex_size = models.DecimalField(max_digits=8, decimal_places=3, default=22)
    hex_origin_x = models.DecimalField(max_digits=8, decimal_places=3, default=7)
    hex_origin_y = models.DecimalField(max_digits=8, decimal_places=3, default=12)
    source_path = models.CharField(max_length=500)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    imported_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["map_type", "name", "-imported_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["key", "version"],
                name="unique_campaign_map_key_version",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.version}"
