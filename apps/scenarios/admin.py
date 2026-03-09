from django.contrib import admin

from .models import ScenarioTemplate


@admin.register(ScenarioTemplate)
class ScenarioTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "aircraft_type",
        "departure_icao",
        "destination_icao",
        "difficulty_baseline",
    ]
    list_filter = ["aircraft_type", "difficulty_baseline"]
    search_fields = ["title", "departure_icao", "destination_icao"]
