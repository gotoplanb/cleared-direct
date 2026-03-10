import copy

import pytest

from apps.aircraft.models import AircraftType
from apps.flights.models import (
    DEFAULT_FLIGHT_STATE,
    EventQueueItem,
    EventStatus,
    EventTriggerType,
    FlightPhase,
    FlightSession,
)
from apps.scenarios.models import ScenarioTemplate


@pytest.fixture
def aircraft(db):
    return AircraftType.objects.create(
        name="Cirrus SR22T",
        slug="sr22t",
        cruise_ktas=185,
        climb_fpm=1200,
        descent_fpm=1000,
        performance_notes="Single-engine piston",
    )


@pytest.fixture
def scenario(db, aircraft):
    return ScenarioTemplate.objects.create(
        title="Test Night IFR",
        description="Test scenario",
        aircraft_type=aircraft,
        departure_icao="KGNV",
        destination_icao="KOJM",
        route=["KGNV", "MERIT", "DRBIE", "KOJM"],
        baseline_events=[
            {
                "trigger": "phase_change:departure",
                "type": "atc_instruction",
                "payload": {
                    "atc_text": "Cleared for takeoff runway 28.",
                    "required_response_type": "text_input",
                    "correct_readback_keywords": ["cleared", "takeoff", "28"],
                    "coaching_if_wrong": "Read back the clearance.",
                },
            },
            {
                "trigger": "altitude_crossing:3000",
                "type": "atc_instruction",
                "payload": {
                    "atc_text": "Contact departure 124.55.",
                    "required_response_type": "text_input",
                    "correct_readback_keywords": ["124.55", "departure"],
                },
            },
        ],
        difficulty_event_pools={
            "2": [
                {
                    "weight": 1.0,
                    "trigger": "waypoint:DRBIE",
                    "type": "environmental_change",
                    "payload": {"change": "ceiling_drop", "new_ceiling": 500},
                }
            ],
            "3": [
                {
                    "weight": 1.0,
                    "trigger": "waypoint:MERIT",
                    "type": "abnormal",
                    "payload": {
                        "title": "Pitot Heat Advisory",
                        "decision_points": [
                            {
                                "prompt": "What's your first action?",
                                "options": [
                                    {"text": "Turn on pitot heat", "quality": "best"},
                                    {"text": "Ignore it", "quality": "dangerous"},
                                ],
                            }
                        ],
                    },
                }
            ],
        },
        briefing_text="Test briefing.",
        difficulty_baseline=2,
    )


@pytest.fixture
def session(db, scenario, aircraft):
    return FlightSession.objects.create(
        scenario_template=scenario,
        aircraft_type=aircraft,
        difficulty=2,
    )


@pytest.fixture
def initialized_session(session):
    from apps.flights import engine

    engine.initialize_session(session)
    session.refresh_from_db()
    return session


@pytest.fixture
def enroute_session(initialized_session):
    from apps.flights import engine

    engine.transition_phase(initialized_session, FlightPhase.ENROUTE)
    initialized_session.refresh_from_db()
    return initialized_session
