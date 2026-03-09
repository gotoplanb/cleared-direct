from django.contrib import admin

from .models import AircraftType


@admin.register(AircraftType)
class AircraftTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "cruise_ktas", "climb_fpm", "descent_fpm"]
    prepopulated_fields = {"slug": ("name",)}
