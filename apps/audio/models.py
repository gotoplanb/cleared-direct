from django.db import models


class ATCAudioClip(models.Model):
    slug = models.SlugField(unique=True, help_text="e.g. cleared_ils_approach")
    template_text = models.TextField(
        help_text='e.g. "{callsign}, cleared ILS runway {runway} approach"',
    )
    audio_file = models.FileField(
        upload_to="atc_audio/",
        blank=True,
        help_text="Pre-generated MP3 file",
    )
    variable_slots = models.JSONField(
        default=list,
        help_text="List of variable slot names in the template",
    )

    class Meta:
        ordering = ["slug"]
        verbose_name = "ATC Audio Clip"

    def __str__(self):
        return self.slug

    def render_text(self, variables: dict) -> str:
        """Fill variable slots into the template text."""
        text = self.template_text
        for key, value in variables.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text
