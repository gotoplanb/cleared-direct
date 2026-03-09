"""Load all scenario YAML files from the fixtures directory."""

from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load all scenario YAML files from fixtures/scenarios/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing scenarios instead of erroring on duplicates",
        )

    def handle(self, *args, **options):
        fixtures_dir = settings.BASE_DIR / "fixtures" / "scenarios"
        files = sorted(fixtures_dir.glob("*.yaml")) + sorted(fixtures_dir.glob("*.yml"))

        if not files:
            self.stdout.write(self.style.WARNING("No scenario files found in fixtures/scenarios/"))
            return

        loaded = 0
        for f in files:
            self.stdout.write(f"Loading {f.name}...")
            try:
                call_args = ["load_scenario", str(f)]
                if options["update"]:
                    call_args.append("--update")
                call_command(*call_args, stdout=self.stdout)
                loaded += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nLoaded {loaded}/{len(files)} scenarios"))
