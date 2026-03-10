"""Tests for model creation, defaults, and constraints."""

import pytest

from apps.aircraft.models import AircraftType
from apps.flights.models import (
    DEFAULT_FLIGHT_STATE,
    EventQueueItem,
    FlightPhase,
    FlightSession,
    PlayerAction,
    ResponseQuality,
)
from apps.scenarios.models import ScenarioTemplate


class TestAircraftType:
    def test_str(self, aircraft):
        assert str(aircraft) == "Cirrus SR22T"

    def test_slug_unique(self, aircraft, db):
        with pytest.raises(Exception):
            AircraftType.objects.create(
                name="Duplicate", slug="sr22t", cruise_ktas=100,
                climb_fpm=500, descent_fpm=500,
            )


class TestScenarioTemplate:
    def test_str(self, scenario):
        assert "KGNV" in str(scenario)
        assert "KOJM" in str(scenario)

    def test_route_is_list(self, scenario):
        assert isinstance(scenario.route, list)
        assert len(scenario.route) == 4


class TestFlightSession:
    def test_default_flight_state(self, session):
        """New session should get DEFAULT_FLIGHT_STATE."""
        assert "autopilot" in session.flight_state
        assert "nav" in session.flight_state
        assert "engine" in session.flight_state

    def test_default_phase(self, session):
        assert session.phase == FlightPhase.PREFLIGHT

    def test_str(self, session):
        assert "Flight" in str(session)
        assert "Difficulty" in str(session)


class TestEventQueueItem:
    def test_str(self, initialized_session):
        event = initialized_session.event_queue.first()
        assert "Event" in str(event)

    def test_default_status_is_pending(self, initialized_session):
        for event in initialized_session.event_queue.all():
            assert event.status == "pending"


class TestPlayerAction:
    def test_create_action(self, initialized_session):
        event = initialized_session.event_queue.first()
        action = PlayerAction.objects.create(
            session=initialized_session,
            event=event,
            response_type="text_input",
            response_given="test readback",
            correct=True,
            quality=ResponseQuality.BEST,
        )
        assert str(action) == f"Action on Event {event.order}: best"
