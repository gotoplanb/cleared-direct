"""Load a scenario from a YAML file into the database."""

import yaml
from django.core.management.base import BaseCommand, CommandError

from apps.aircraft.models import AircraftType
from apps.scenarios.models import ScenarioTemplate


class Command(BaseCommand):
    help = "Load a scenario template from a YAML file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to YAML scenario file")
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing scenario with same title instead of erroring",
        )

    def handle(self, *args, **options):
        filepath = options["file"]

        try:
            with open(filepath) as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {filepath}")
        except yaml.YAMLError as e:
            raise CommandError(f"Invalid YAML: {e}")

        # Resolve aircraft type
        aircraft_slug = data.get("aircraft", "single-engine")
        aircraft, created = AircraftType.objects.get_or_create(
            slug=aircraft_slug,
            defaults={
                "name": aircraft_slug.replace("-", " ").title(),
                "cruise_ktas": 185,
                "climb_fpm": 1000,
                "descent_fpm": 800,
            },
        )
        if created:
            self.stdout.write(f"  Created aircraft type: {aircraft.name}")

        # Build scenario
        title = data.get("title", "Untitled Scenario")
        defaults = {
            "description": data.get("description", ""),
            "aircraft_type": aircraft,
            "departure_icao": data.get("departure", ""),
            "destination_icao": data.get("destination", ""),
            "route": data.get("route", []),
            "baseline_events": data.get("baseline_events", []),
            "difficulty_event_pools": data.get("difficulty_pools", {}),
            "briefing_text": data.get("briefing", ""),
            "difficulty_baseline": data.get("difficulty_baseline", 2),
        }

        if options["update"]:
            scenario, created = ScenarioTemplate.objects.update_or_create(
                title=title, defaults=defaults
            )
            action = "Created" if created else "Updated"
        else:
            if ScenarioTemplate.objects.filter(title=title).exists():
                raise CommandError(
                    f'Scenario "{title}" already exists. Use --update to overwrite.'
                )
            scenario = ScenarioTemplate.objects.create(title=title, **defaults)
            action = "Created"

        self.stdout.write(
            self.style.SUCCESS(
                f'{action} scenario: "{scenario.title}" '
                f"({scenario.departure_icao} → {scenario.destination_icao})"
            )
        )
