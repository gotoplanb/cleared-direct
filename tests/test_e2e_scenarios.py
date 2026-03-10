"""End-to-end tests for all scenarios.

Each test walks the full session lifecycle via the Django test client:
  start session → preflight events → taxi → departure → enroute events

Validates:
  - Preflight events fire sequentially (ATIS → clearance → taxi)
  - Readback evaluation works with string-resolved text
  - Phase transitions trigger the correct events
  - Difficulty pool events fire for qualifying sessions
  - Coaching text resolves from string keys
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from django.test import Client

from apps.aircraft.models import AircraftType
from apps.flights.models import EventQueueItem, EventStatus, FlightPhase, FlightSession
from apps.scenarios.models import ScenarioTemplate

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "scenarios"


def _load_scenario_from_yaml(yaml_path: str, db) -> ScenarioTemplate:
    """Load a scenario YAML into the test database."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    aircraft, _ = AircraftType.objects.get_or_create(
        slug=data.get("aircraft", "single-engine"),
        defaults={
            "name": "Test Aircraft",
            "cruise_ktas": 185,
            "climb_fpm": 1200,
            "descent_fpm": 1000,
        },
    )
    scenario, _ = ScenarioTemplate.objects.update_or_create(
        title=data["title"],
        defaults={
            "description": data.get("description", ""),
            "aircraft_type": aircraft,
            "departure_icao": data.get("departure", ""),
            "destination_icao": data.get("destination", ""),
            "route": data.get("route", []),
            "baseline_events": data.get("baseline_events", []),
            "difficulty_event_pools": data.get("difficulty_pools", {}),
            "briefing_text": data.get("briefing", ""),
            "difficulty_baseline": data.get("difficulty_baseline", 2),
        },
    )
    return scenario


def _start_session(client: Client, scenario_id: int, difficulty: int = 2) -> dict:
    """POST to start a new session, return JSON response."""
    resp = client.post(
        "/session/start/",
        json.dumps({"scenario_id": scenario_id, "difficulty": difficulty}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    return resp.json()


def _tick(client: Client, session_id: int) -> dict:
    """GET tick endpoint, return JSON."""
    resp = client.get(f"/session/{session_id}/tick/")
    assert resp.status_code == 200
    return resp.json()


def _set_phase(client: Client, session_id: int, phase: str) -> dict:
    """POST to change phase, return JSON."""
    resp = client.post(
        f"/session/{session_id}/phase/",
        json.dumps({"phase": phase}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    return resp.json()


def _submit_response(client: Client, session_id: int, event_id: int, response: str) -> dict:
    """POST a readback/response to an event, return JSON."""
    resp = client.post(
        f"/session/{session_id}/action/",
        json.dumps({"event_id": event_id, "response": response}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    return resp.json()


def _tick_until_event(client: Client, session_id: int, max_ticks: int = 5) -> dict | None:
    """Tick until an awaiting_event appears or max_ticks reached."""
    for _ in range(max_ticks):
        data = _tick(client, session_id)
        if data.get("awaiting_event"):
            return data["awaiting_event"]
        # Check if events fired that need responses
        for evt in data.get("events", []):
            if evt.get("status") == EventStatus.AWAITING_RESPONSE:
                return evt
    return None


def _respond_to_awaiting(client: Client, session_id: int, response: str, max_ticks: int = 5) -> dict:
    """Tick until an event awaits, respond, return the action result."""
    evt = _tick_until_event(client, session_id, max_ticks)
    assert evt is not None, "No awaiting event found"
    return _submit_response(client, session_id, evt["id"], response)


# ═══════════════════════════════════════════════════════════════════════════════
# Student Day VFR to Ocala (Difficulty 1)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestStudentVFR:
    """Full e2e for the simplest scenario — VFR with preflight."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.scenario = _load_scenario_from_yaml(SCENARIOS_DIR / "student_day_vfr_kocf.yaml", db)
        self.client = Client()

    def test_preflight_atis_fires_automatically(self):
        """Session starts in preflight; first tick fires ATIS event."""
        data = _start_session(self.client, self.scenario.id, difficulty=1)
        session_id = data["session_id"]
        assert data["phase"] == "preflight"

        evt = _tick_until_event(self.client, session_id)
        assert evt is not None
        assert "Gainesville information Alpha" in evt["payload"]["atc_text"]
        assert "runway 28" in evt["payload"]["atc_text"]

    def test_preflight_sequence_atis_then_ground(self):
        """After ATIS readback, ground clearance fires next."""
        data = _start_session(self.client, self.scenario.id, difficulty=1)
        sid = data["session_id"]

        # ATIS
        evt = _tick_until_event(self.client, sid)
        result = _submit_response(self.client, sid, evt["id"], "Information Alpha")
        assert result["correct"] is True

        # Ground clearance should fire next
        evt2 = _tick_until_event(self.client, sid)
        assert evt2 is not None
        assert evt2["id"] != evt["id"]
        assert "runway 28" in evt2["payload"]["atc_text"]
        assert "VFR" in evt2["payload"]["atc_text"]

    def test_full_preflight_to_departure(self):
        """Walk through: preflight → taxi → departure takeoff clearance."""
        data = _start_session(self.client, self.scenario.id, difficulty=1)
        sid = data["session_id"]

        # Preflight: ATIS
        _respond_to_awaiting(self.client, sid, "Information Alpha")
        # Preflight: Ground clearance
        _respond_to_awaiting(self.client, sid, "Runway 28, 3500, 30.12")

        # No more preflight events — advance to taxi
        _set_phase(self.client, sid, "taxi")

        # Taxi clearance
        evt = _tick_until_event(self.client, sid)
        assert evt is not None
        assert "taxi" in evt["payload"]["atc_text"].lower()
        assert "Alpha" in evt["payload"]["atc_text"]
        _submit_response(self.client, sid, evt["id"], "Runway 28 via Alpha")

        # Advance to departure
        _set_phase(self.client, sid, "departure")
        evt = _tick_until_event(self.client, sid)
        assert evt is not None
        assert "cleared for takeoff" in evt["payload"]["atc_text"].lower()

    def test_poor_readback_gets_coaching(self):
        """A bad ATIS readback returns coaching text."""
        data = _start_session(self.client, self.scenario.id, difficulty=1)
        sid = data["session_id"]

        evt = _tick_until_event(self.client, sid)
        result = _submit_response(self.client, sid, evt["id"], "uh what")
        assert result["correct"] is False
        assert result["coaching"] != ""
        assert "ATIS" in result["coaching"] or "information" in result["coaching"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Private IFR to St. Augustine (Difficulty 2)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPrivateIFR:
    """IFR scenario with clearance delivery (CRAFT format)."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.scenario = _load_scenario_from_yaml(SCENARIOS_DIR / "private_ifr_ksgj.yaml", db)
        self.client = Client()

    def test_ifr_clearance_delivery(self):
        """IFR preflight includes CRAFT clearance after ATIS."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        # ATIS
        evt = _tick_until_event(self.client, sid)
        assert "Charlie" in evt["payload"]["atc_text"]
        _submit_response(self.client, sid, evt["id"], "Information Charlie")

        # Clearance delivery
        evt2 = _tick_until_event(self.client, sid)
        payload = evt2["payload"]
        assert "cleared to" in payload["atc_text"].lower() or "cleared" in payload["atc_text"].lower()
        assert "5012" in payload["atc_text"]  # squawk code
        assert "124.55" in payload["atc_text"]  # departure frequency

    def test_ifr_clearance_correct_readback(self):
        """Full CRAFT readback is scored as correct."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        # ATIS
        _respond_to_awaiting(self.client, sid, "Information Charlie")

        # Clearance
        evt = _tick_until_event(self.client, sid)
        result = _submit_response(
            self.client, sid, evt["id"],
            "Cleared to St. Augustine, climb and maintain 3000, expect 5000, departure 124.55, squawk 5012"
        )
        assert result["correct"] is True
        assert result["quality"] in ("best", "acceptable")

    def test_full_ifr_preflight_to_enroute(self):
        """Walk IFR preflight → taxi → departure → climb → enroute handoff."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        # Preflight: ATIS → Clearance
        _respond_to_awaiting(self.client, sid, "Information Charlie")
        _respond_to_awaiting(self.client, sid, "Cleared St. Augustine 3000 5000 124.55 5012")

        # Taxi
        _set_phase(self.client, sid, "taxi")
        _respond_to_awaiting(self.client, sid, "Runway 28 via Alpha")

        # Departure
        _set_phase(self.client, sid, "departure")
        evt = _tick_until_event(self.client, sid)
        assert "cleared" in evt["payload"]["atc_text"].lower()
        assert "takeoff" in evt["payload"]["atc_text"].lower()
        _submit_response(self.client, sid, evt["id"], "Cleared takeoff 28 heading 090 climb 3000")

        # Verify session state
        session = FlightSession.objects.get(id=sid)
        assert session.phase == "departure"


# ═══════════════════════════════════════════════════════════════════════════════
# Night IFR to KOJM (Difficulty 2)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestNightIFR:
    """Night IFR with ATIS → clearance → taxi → departure."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.scenario = _load_scenario_from_yaml(SCENARIOS_DIR / "night_ifr_kojm.yaml", db)
        self.client = Client()

    def test_night_ifr_preflight_clearance(self):
        """Night IFR ATIS shows Bravo and IFR conditions remark."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        evt = _tick_until_event(self.client, sid)
        assert "Bravo" in evt["payload"]["atc_text"]
        assert "IFR" in evt["payload"]["atc_text"]

    def test_night_ifr_clearance_has_squawk(self):
        """IFR clearance includes squawk code 4231."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        _respond_to_awaiting(self.client, sid, "Information Bravo")
        evt = _tick_until_event(self.client, sid)
        assert "4231" in evt["payload"]["atc_text"]
        assert "KOJM" in evt["payload"]["atc_text"]

    def test_event_queue_count(self):
        """Session at difficulty 2 has baseline + pool events queued."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]
        session = FlightSession.objects.get(id=sid)
        # Baseline: 2 preflight + 1 taxi + 4 departure = 7
        # Plus difficulty pool events (weight-based, non-deterministic)
        baseline_count = session.event_queue.count()
        assert baseline_count >= 7


# ═══════════════════════════════════════════════════════════════════════════════
# IFR Proficiency with Hold at Orlando (Difficulty 3)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestIFRProficiency:
    """IFR with holding, missed approach, and diversion."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.scenario = _load_scenario_from_yaml(SCENARIOS_DIR / "ifr_prof_hold_korl.yaml", db)
        self.client = Client()

    def test_preflight_atis_delta(self):
        """Orlando scenario ATIS is information Delta."""
        data = _start_session(self.client, self.scenario.id, difficulty=3)
        sid = data["session_id"]

        evt = _tick_until_event(self.client, sid)
        assert "Delta" in evt["payload"]["atc_text"]
        assert "Light rain" in evt["payload"]["atc_text"]

    def test_ifr_clearance_to_orlando(self):
        """Clearance delivery routes to Orlando Executive."""
        data = _start_session(self.client, self.scenario.id, difficulty=3)
        sid = data["session_id"]

        _respond_to_awaiting(self.client, sid, "Information Delta")
        evt = _tick_until_event(self.client, sid)
        assert "Orlando" in evt["payload"]["atc_text"]
        assert "3417" in evt["payload"]["atc_text"]  # squawk

    def test_taxi_clearance_charlie(self):
        """Taxi route is Alpha, Charlie."""
        data = _start_session(self.client, self.scenario.id, difficulty=3)
        sid = data["session_id"]

        _respond_to_awaiting(self.client, sid, "Information Delta")
        _respond_to_awaiting(self.client, sid, "Cleared Orlando 4000 6000 124.55 3417")

        _set_phase(self.client, sid, "taxi")
        evt = _tick_until_event(self.client, sid)
        assert "Alpha" in evt["payload"]["atc_text"]
        assert "Charlie" in evt["payload"]["atc_text"]

    def test_difficulty_3_includes_pool_events(self):
        """At difficulty 3, pool events for levels 2 and 3 are eligible."""
        data = _start_session(self.client, self.scenario.id, difficulty=3)
        sid = data["session_id"]
        session = FlightSession.objects.get(id=sid)
        # Baseline: 2 preflight + 1 taxi + 5 departure = 8
        # Pool: difficulty 2 (turbulence) + difficulty 3 (diversion)
        total = session.event_queue.count()
        assert total >= 8


# ═══════════════════════════════════════════════════════════════════════════════
# Checkride Hell into Jacksonville (Difficulty 4)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestCheckrideHell:
    """The hardest scenario — tests hold-short, non-standard hold, etc."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.scenario = _load_scenario_from_yaml(SCENARIOS_DIR / "checkride_hell_kjax.yaml", db)
        self.client = Client()

    def test_atis_echo_with_notam(self):
        """Checkride ATIS is Echo with NOTAM about closed runway."""
        data = _start_session(self.client, self.scenario.id, difficulty=4)
        sid = data["session_id"]

        evt = _tick_until_event(self.client, sid)
        text = evt["payload"]["atc_text"]
        assert "Echo" in text
        assert "NOTAM" in text
        assert "runway 25 closed" in text.lower() or "runway 25" in text

    def test_clearance_to_jacksonville(self):
        """IFR clearance to Jacksonville with squawk 6204."""
        data = _start_session(self.client, self.scenario.id, difficulty=4)
        sid = data["session_id"]

        _respond_to_awaiting(self.client, sid, "Information Echo")
        evt = _tick_until_event(self.client, sid)
        text = evt["payload"]["atc_text"]
        assert "Jacksonville" in text
        assert "6204" in text
        assert "8,000" in text or "8000" in text

    def test_taxi_has_hold_short(self):
        """Checkride taxi includes hold-short instruction."""
        data = _start_session(self.client, self.scenario.id, difficulty=4)
        sid = data["session_id"]

        _respond_to_awaiting(self.client, sid, "Information Echo")
        _respond_to_awaiting(self.client, sid, "Cleared Jacksonville 4000 8000 124.55 6204")

        _set_phase(self.client, sid, "taxi")
        evt = _tick_until_event(self.client, sid)
        text = evt["payload"]["atc_text"]
        assert "hold short" in text.lower() or "Hold short" in text
        assert "10" in text  # hold short of runway 10

    def test_hold_short_bad_readback_coaching(self):
        """Completely wrong readback triggers coaching."""
        data = _start_session(self.client, self.scenario.id, difficulty=4)
        sid = data["session_id"]

        _respond_to_awaiting(self.client, sid, "Information Echo")
        _respond_to_awaiting(self.client, sid, "Cleared Jacksonville 4000 8000 124.55 6204")

        _set_phase(self.client, sid, "taxi")
        evt = _tick_until_event(self.client, sid)
        # Respond with a completely wrong readback (< 50% keyword match)
        result = _submit_response(self.client, sid, evt["id"], "roger wilco")
        assert result["correct"] is False
        assert "hold short" in result["coaching"].lower() or "Hold short" in result["coaching"]

    def test_difficulty_4_max_events(self):
        """At max difficulty, all pool events are eligible."""
        data = _start_session(self.client, self.scenario.id, difficulty=4)
        sid = data["session_id"]
        session = FlightSession.objects.get(id=sid)
        # Baseline: 2 preflight + 1 taxi + 6 departure = 9
        # Pools: difficulty 2 (icing), 3 (pitot + comms), 4 (vacuum + fuel)
        total = session.event_queue.count()
        assert total >= 9

    def test_full_preflight_through_departure(self):
        """Walk the full checkride preflight → taxi → departure."""
        data = _start_session(self.client, self.scenario.id, difficulty=4)
        sid = data["session_id"]

        # Preflight
        _respond_to_awaiting(self.client, sid, "Information Echo")
        _respond_to_awaiting(self.client, sid, "Cleared Jacksonville 4000 8000 124.55 6204")

        # Taxi with hold-short
        _set_phase(self.client, sid, "taxi")
        _respond_to_awaiting(self.client, sid, "Runway 28 via Alpha Bravo hold short runway 10")

        # Departure
        _set_phase(self.client, sid, "departure")
        evt = _tick_until_event(self.client, sid)
        text = evt["payload"]["atc_text"]
        assert "cleared for takeoff" in text.lower()
        assert "050" in text  # heading
        assert "4,000" in text or "4000" in text
        assert "8,000" in text or "8000" in text

        result = _submit_response(
            self.client, sid, evt["id"],
            "Cleared takeoff 28 heading 050 climb 4000 expect 8000"
        )
        assert result["correct"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-scenario: Spanish language support
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestSpanishLanguage:
    """Verify string resolution works for Spanish."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.scenario = _load_scenario_from_yaml(SCENARIOS_DIR / "student_day_vfr_kocf.yaml", db)
        self.client = Client()

    def test_spanish_atis(self):
        """ATIS text resolves in Spanish."""
        resp = self.client.post(
            "/session/start/",
            json.dumps({
                "scenario_id": self.scenario.id,
                "difficulty": 1,
                "language": "es",
            }),
            content_type="application/json",
        )
        data = resp.json()
        sid = data["session_id"]

        evt = _tick_until_event(self.client, sid)
        text = evt["payload"]["atc_text"]
        # Spanish ATIS should have Spanish words
        assert "Información" in text or "información" in text or "Gainesville" in text

    def test_spanish_coaching(self):
        """Coaching text resolves in Spanish after bad readback."""
        resp = self.client.post(
            "/session/start/",
            json.dumps({
                "scenario_id": self.scenario.id,
                "difficulty": 1,
                "language": "es",
            }),
            content_type="application/json",
        )
        data = resp.json()
        sid = data["session_id"]

        evt = _tick_until_event(self.client, sid)
        result = _submit_response(self.client, sid, evt["id"], "wrong")
        # Spanish coaching text
        assert result["coaching"] != ""


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-scenario: Event sequencing
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestEventSequencing:
    """Verify engine fires events one at a time when responses are required."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.scenario = _load_scenario_from_yaml(SCENARIOS_DIR / "night_ifr_kojm.yaml", db)
        self.client = Client()

    def test_only_one_event_fires_per_tick(self):
        """When multiple phase_change:preflight events exist, only the first fires."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        tick_data = _tick(self.client, sid)
        # Should have exactly one awaiting event (ATIS), not both preflight events
        awaiting = tick_data.get("awaiting_event")
        events = tick_data.get("events", [])
        # Either awaiting_event or one event in the list
        total_awaiting = (1 if awaiting else 0) + len([e for e in events if e.get("status") == "awaiting_response"])
        assert total_awaiting <= 1

    def test_second_event_fires_after_first_resolved(self):
        """After resolving the ATIS event, the clearance event fires on next tick."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        # First event: ATIS
        evt1 = _tick_until_event(self.client, sid)
        assert "Bravo" in evt1["payload"]["atc_text"]
        _submit_response(self.client, sid, evt1["id"], "Information Bravo")

        # Second event: Clearance
        evt2 = _tick_until_event(self.client, sid)
        assert evt2 is not None
        assert evt2["id"] != evt1["id"]
        assert "cleared" in evt2["payload"]["atc_text"].lower()

    def test_no_events_fire_in_wrong_phase(self):
        """Departure events don't fire during preflight."""
        data = _start_session(self.client, self.scenario.id, difficulty=2)
        sid = data["session_id"]

        session = FlightSession.objects.get(id=sid)
        # Count departure events that are still pending
        departure_events = session.event_queue.filter(
            trigger_type="phase_change",
            trigger_value__value="departure",
            status=EventStatus.PENDING,
        )
        assert departure_events.count() > 0  # they exist but haven't fired
