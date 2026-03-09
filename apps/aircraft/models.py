from django.db import models


class AircraftType(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    cruise_ktas = models.PositiveIntegerField(help_text="Cruise speed in KTAS")
    climb_fpm = models.PositiveIntegerField(help_text="Climb rate in FPM")
    descent_fpm = models.PositiveIntegerField(help_text="Descent rate in FPM")
    performance_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
