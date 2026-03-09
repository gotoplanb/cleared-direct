from django.db import models


class ScenarioTemplate(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    aircraft_type = models.ForeignKey(
        "aircraft.AircraftType",
        on_delete=models.CASCADE,
        related_name="scenarios",
    )
    departure_icao = models.CharField(max_length=4)
    destination_icao = models.CharField(max_length=4)
    route = models.JSONField(
        default=list,
        help_text="Ordered list of waypoints/fixes",
    )
    baseline_events = models.JSONField(
        default=list,
        help_text="Ordered event definitions that always fire",
    )
    difficulty_event_pools = models.JSONField(
        default=dict,
        help_text="Mapping of difficulty level to event sets with probability weights",
    )
    briefing_text = models.TextField(
        help_text="Shown in pre-flight briefing cutscene",
    )
    difficulty_baseline = models.PositiveIntegerField(
        default=2,
        help_text="Minimum difficulty level for this scenario",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.departure_icao} → {self.destination_icao})"
