"""Seed the database: flush ifr_ tables and reload all fixtures."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Flush ifr_ tables and reload all scenario fixtures"

    def handle(self, *args, **options):
        self.stdout.write("Flushing ifr_ tables...")
        call_command("flush_ifr", no_input=True, stdout=self.stdout)

        self.stdout.write("\nLoading scenarios...")
        call_command("load_all_scenarios", update=True, stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS("\nSeed complete"))
