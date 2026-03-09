from django.contrib import admin

from .models import EventQueueItem, FlightSession, PlayerAction


class EventQueueInline(admin.TabularInline):
    model = EventQueueItem
    extra = 0
    fields = ["order", "trigger_type", "event_type", "status", "fired_at"]
    readonly_fields = ["fired_at"]


class PlayerActionInline(admin.TabularInline):
    model = PlayerAction
    extra = 0
    fields = ["event", "response_type", "response_given", "correct", "quality"]


@admin.register(FlightSession)
class FlightSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "scenario_template",
        "difficulty",
        "phase",
        "started_at",
        "ended_at",
    ]
    list_filter = ["difficulty", "phase"]
    inlines = [EventQueueInline, PlayerActionInline]


@admin.register(EventQueueItem)
class EventQueueItemAdmin(admin.ModelAdmin):
    list_display = ["session", "order", "trigger_type", "event_type", "status"]
    list_filter = ["event_type", "status"]


@admin.register(PlayerAction)
class PlayerActionAdmin(admin.ModelAdmin):
    list_display = ["session", "event", "response_type", "correct", "quality"]
    list_filter = ["quality", "correct"]
