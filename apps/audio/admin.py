from django.contrib import admin

from .models import ATCAudioClip


@admin.register(ATCAudioClip)
class ATCAudioClipAdmin(admin.ModelAdmin):
    list_display = ["slug", "template_text", "variable_slots"]
    search_fields = ["slug", "template_text"]
