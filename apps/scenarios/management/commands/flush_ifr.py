"""Flush only ifr_ prefixed tables (safe for shared database)."""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


IFR_TABLES = [
    "ifr_player_action",
    "ifr_event_queue_item",
    "ifr_flight_session",
    "ifr_scenario_template",
    "ifr_atc_audio_clip",
    "ifr_aircraft_type",
]


class Command(BaseCommand):
    help = "Flush all ifr_ prefixed tables (safe for shared database)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            action="store_true",
            dest="no_input",
            help="Skip confirmation prompt",
        )
        parser.add_argument(
            "--sessions-only",
            action="store_true",
            help="Only flush session data, keep scenarios and aircraft",
        )

    def handle(self, *args, **options):
        if options["sessions_only"]:
            tables = [
                "ifr_player_action",
                "ifr_event_queue_item",
                "ifr_flight_session",
            ]
            label = "session"
        else:
            tables = IFR_TABLES
            label = "all ifr_"

        if not options["no_input"]:
            self.stdout.write(
                self.style.WARNING(f"This will DELETE all data from {label} tables:")
            )
            for t in tables:
                self.stdout.write(f"  - {t}")
            confirm = input("\nAre you sure? [y/N] ")
            if confirm.lower() != "y":
                self.stdout.write("Cancelled.")
                return

        with connection.cursor() as cursor:
            # Truncate in order (respecting FK constraints)
            cursor.execute(
                f"TRUNCATE {', '.join(tables)} CASCADE;"
            )

        self.stdout.write(self.style.SUCCESS(f"Flushed {len(tables)} tables"))
