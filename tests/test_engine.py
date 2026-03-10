"""Tests for the scenario engine — tick loop, state advancement, event triggers."""

import pytest

from apps.flights import engine
from apps.flights.models import (
    EventQueueItem,
    EventStatus,
    EventTriggerType,
    FlightPhase,
    FlightSession,
)


# ── Initialization ───────────────────────────────────────


class TestInitializeSession:
    def test_sets_preflight_phase(self, initialized_session):
        assert initialized_session.phase == FlightPhase.PREFLIGHT

    def test_builds_flight_state(self, initialized_session):
        state = initialized_session.flight_state
        assert state["indicated_airspeed"] == 0
        assert state["altitude"] == 0
        assert state["engine"]["fuel_gals_remaining"] == 60

    def test_populates_waypoints(self, initialized_session):
        nav = initialized_session.flight_state["nav"]
        assert nav["waypoints"] == ["KGNV", "MERIT", "DRBIE", "KOJM"]
        assert nav["next_waypoint"] == "KGNV"

    def test_creates_baseline_events(self, initialized_session):
        events = initialized_session.event_queue.all()
        baseline = [e for e in events if e.trigger_type == EventTriggerType.PHASE_CHANGE]
        assert len(baseline) >= 1

    def test_creates_difficulty_pool_events(self, initialized_session):
        """Difficulty 2 session should include level 2 pool events (weight=1.0)."""
        events = initialized_session.event_queue.filter(event_type="environmental_change")
        assert events.count() == 1

    def test_all_events_pending(self, initialized_session):
        for event in initialized_session.event_queue.all():
            assert event.status == EventStatus.PENDING

    def test_resets_tick_count(self, initialized_session):
        assert initialized_session.tick_count == 0


# ── Phase Transitions ────────────────────────────────────


class TestPhaseTransitions:
    def test_taxi_sets_engine_rpm(self, initialized_session):
        engine.transition_phase(initialized_session, FlightPhase.TAXI)
        assert initialized_session.flight_state["engine"]["rpm"] == 1000
        assert initialized_session.flight_state["indicated_airspeed"] == 0

    def test_departure_sets_takeoff_state(self, initialized_session):
        engine.transition_phase(initialized_session, FlightPhase.DEPARTURE)
        state = initialized_session.flight_state
        assert state["engine"]["rpm"] == 2400
        assert state["indicated_airspeed"] == 80
        assert state["autopilot"]["engaged"] is False

    def test_enroute_sets_cruise(self, enroute_session):
        state = enroute_session.flight_state
        assert state["altitude"] == 6000
        assert state["heading"] == 280
        assert state["autopilot"]["engaged"] is True
        assert "HDG" in state["autopilot"]["modes"]
        assert "ALT" in state["autopilot"]["modes"]
        assert state["autopilot"]["selected_altitude"] == 6000

    def test_enroute_advances_waypoint(self, enroute_session):
        nav = enroute_session.flight_state["nav"]
        assert nav["next_waypoint"] == "MERIT"
        assert nav["distance_to_next"] == 30.0

    def test_approach_sets_descent_altitude(self, enroute_session):
        engine.transition_phase(enroute_session, FlightPhase.APPROACH)
        state = enroute_session.flight_state
        assert state["autopilot"]["selected_altitude"] == 3000

    def test_landed_stops_aircraft(self, enroute_session):
        engine.transition_phase(enroute_session, FlightPhase.LANDED)
        state = enroute_session.flight_state
        assert state["indicated_airspeed"] == 0
        assert state["altitude"] == 0
        assert state["autopilot"]["engaged"] is False
        assert enroute_session.ended_at is not None

    def test_failed_sets_ended_at(self, enroute_session):
        engine.transition_phase(enroute_session, FlightPhase.FAILED)
        assert enroute_session.ended_at is not None

    def test_logs_phase_transition(self, initialized_session):
        engine.transition_phase(initialized_session, FlightPhase.TAXI)
        log = initialized_session.event_log
        transition_logs = [e for e in log if "phase_transition" in e]
        assert len(transition_logs) >= 1
        assert transition_logs[-1]["phase_transition"]["to"] == FlightPhase.TAXI


# ── Tick & State Advancement ─────────────────────────────


class TestTick:
    def test_tick_increments_counter(self, enroute_session):
        result = engine.tick(enroute_session)
        assert enroute_session.tick_count == 1
        assert result["tick"] == 1

    def test_tick_returns_flight_state(self, enroute_session):
        result = engine.tick(enroute_session)
        assert "flight_state" in result
        assert result["phase"] == FlightPhase.ENROUTE

    def test_paused_session_no_advance(self, enroute_session):
        enroute_session.paused = True
        enroute_session.save()
        result = engine.tick(enroute_session)
        assert result["paused"] is True
        assert enroute_session.tick_count == 0

    def test_landed_session_no_advance(self, enroute_session):
        enroute_session.phase = FlightPhase.LANDED
        enroute_session.save()
        result = engine.tick(enroute_session)
        assert result["paused"] is True

    def test_fuel_burns_during_enroute(self, enroute_session):
        # Set fuel to a value where 0.0125 gal/tick burn is visible after rounding
        enroute_session.flight_state["engine"]["fuel_gals_remaining"] = 50.05
        enroute_session.save()
        initial_fuel = enroute_session.flight_state["engine"]["fuel_gals_remaining"]
        engine.tick(enroute_session)
        new_fuel = enroute_session.flight_state["engine"]["fuel_gals_remaining"]
        assert new_fuel < initial_fuel

    def test_fuel_burns_during_departure(self, initialized_session):
        engine.transition_phase(initialized_session, FlightPhase.DEPARTURE)
        initialized_session.flight_state["engine"]["fuel_gals_remaining"] = 50.05
        initialized_session.save()
        initial_fuel = initialized_session.flight_state["engine"]["fuel_gals_remaining"]
        engine.tick(initialized_session)
        new_fuel = initialized_session.flight_state["engine"]["fuel_gals_remaining"]
        assert new_fuel < initial_fuel

    def test_waypoint_distance_decreases(self, enroute_session):
        initial_dist = enroute_session.flight_state["nav"]["distance_to_next"]
        engine.tick(enroute_session)
        new_dist = enroute_session.flight_state["nav"]["distance_to_next"]
        assert new_dist < initial_dist

    def test_preflight_no_state_advance(self, initialized_session):
        """Preflight phase should not advance altitude/airspeed."""
        initial_alt = initialized_session.flight_state["altitude"]
        engine.tick(initialized_session)
        assert initialized_session.flight_state["altitude"] == initial_alt


# ── Autopilot State Advancement ──────────────────────────


class TestAutopilot:
    def test_hdg_mode_turns_toward_target(self, enroute_session):
        state = enroute_session.flight_state
        state["autopilot"]["selected_heading"] = 290
        state["heading"] = 280
        enroute_session.flight_state = state
        engine.tick(enroute_session)
        assert enroute_session.flight_state["heading"] >= 280

    def test_alt_mode_climbs_to_target(self, enroute_session):
        state = enroute_session.flight_state
        state["altitude"] = 5000
        state["autopilot"]["selected_altitude"] = 6000
        enroute_session.flight_state = state
        engine.tick(enroute_session)
        assert enroute_session.flight_state["altitude"] > 5000

    def test_alt_mode_descends_to_target(self, enroute_session):
        state = enroute_session.flight_state
        state["altitude"] = 6000
        state["autopilot"]["selected_altitude"] = 3000
        enroute_session.flight_state = state
        engine.tick(enroute_session)
        assert enroute_session.flight_state["altitude"] < 6000

    def test_alt_mode_levels_off_at_target(self, enroute_session):
        state = enroute_session.flight_state
        state["altitude"] = 5990
        state["autopilot"]["selected_altitude"] = 6000
        enroute_session.flight_state = state
        engine.tick(enroute_session)
        assert enroute_session.flight_state["altitude"] == 6000
        assert enroute_session.flight_state["vertical_speed"] == 0

    def test_vs_mode_applies_vertical_speed(self, enroute_session):
        state = enroute_session.flight_state
        state["autopilot"]["modes"] = ["HDG", "VS"]
        state["autopilot"]["selected_vs"] = -500
        enroute_session.flight_state = state
        engine.tick(enroute_session)
        assert enroute_session.flight_state["altitude"] < 6000
        assert enroute_session.flight_state["vertical_speed"] == -500

    def test_airspeed_converges_to_cruise(self, enroute_session):
        state = enroute_session.flight_state
        state["indicated_airspeed"] = 100
        enroute_session.flight_state = state
        engine.tick(enroute_session)
        assert enroute_session.flight_state["indicated_airspeed"] > 100


# ── Event Triggers ───────────────────────────────────────


class TestEventTriggers:
    def test_phase_change_trigger_fires(self, initialized_session):
        """Phase change to departure should fire the takeoff clearance event."""
        engine.transition_phase(initialized_session, FlightPhase.DEPARTURE)
        engine.tick(initialized_session)
        departure_events = initialized_session.event_queue.filter(
            trigger_type=EventTriggerType.PHASE_CHANGE,
            status__in=[EventStatus.ACTIVE, EventStatus.AWAITING_RESPONSE],
        )
        assert departure_events.count() >= 1

    def test_altitude_crossing_trigger_fires(self, enroute_session):
        """Setting altitude near 3000 should fire the altitude crossing event."""
        enroute_session.flight_state["altitude"] = 3050
        enroute_session.save()
        engine.tick(enroute_session)
        alt_events = enroute_session.event_queue.filter(
            trigger_type=EventTriggerType.ALTITUDE_CROSSING,
            status__in=[EventStatus.ACTIVE, EventStatus.AWAITING_RESPONSE],
        )
        assert alt_events.count() >= 1

    def test_time_trigger_fires_at_tick(self, enroute_session):
        """Create a time-based event and verify it fires at the right tick."""
        EventQueueItem.objects.create(
            session=enroute_session,
            order=99,
            trigger_type=EventTriggerType.TIME,
            trigger_value={"type": "time", "value": "2"},
            event_type="abnormal",
            payload={"title": "Test time event"},
            status=EventStatus.PENDING,
        )
        engine.tick(enroute_session)  # tick 1
        assert enroute_session.event_queue.filter(order=99, status=EventStatus.PENDING).exists()
        engine.tick(enroute_session)  # tick 2
        assert enroute_session.event_queue.filter(
            order=99, status=EventStatus.ACTIVE
        ).exists()

    def test_waypoint_trigger_fires_when_close(self, enroute_session):
        """Waypoint event should fire when distance < 5 NM."""
        EventQueueItem.objects.create(
            session=enroute_session,
            order=98,
            trigger_type=EventTriggerType.WAYPOINT,
            trigger_value={"type": "waypoint", "value": "MERIT"},
            event_type="atc_instruction",
            payload={"atc_text": "Test"},
            status=EventStatus.PENDING,
        )
        enroute_session.flight_state["nav"]["next_waypoint"] = "MERIT"
        enroute_session.flight_state["nav"]["distance_to_next"] = 3.0
        enroute_session.save()
        engine.tick(enroute_session)
        assert enroute_session.event_queue.filter(order=98, status=EventStatus.ACTIVE).exists()

    def test_manual_trigger_does_not_auto_fire(self, enroute_session):
        EventQueueItem.objects.create(
            session=enroute_session,
            order=97,
            trigger_type=EventTriggerType.MANUAL,
            trigger_value={"type": "manual"},
            event_type="abnormal",
            payload={"title": "Manual only"},
            status=EventStatus.PENDING,
        )
        engine.tick(enroute_session)
        assert enroute_session.event_queue.filter(order=97, status=EventStatus.PENDING).exists()

    def test_awaiting_response_pauses_ticks(self, enroute_session):
        """When an event is awaiting response, ticks should pause."""
        event = enroute_session.event_queue.first()
        event.status = EventStatus.AWAITING_RESPONSE
        event.save()
        result = engine.tick(enroute_session)
        assert result["paused"] is True
        assert "awaiting_event" in result


# ── Event Resolution ─────────────────────────────────────


class TestEventResolution:
    def test_resolve_event_sets_status(self, enroute_session):
        event = enroute_session.event_queue.first()
        event.status = EventStatus.AWAITING_RESPONSE
        event.save()
        engine.resolve_event(event, response="test", quality="best")
        event.refresh_from_db()
        assert event.status == EventStatus.RESOLVED
        assert event.resolved_at is not None


# ── Helper: _parse_trigger ───────────────────────────────


class TestParseTrigger:
    def test_empty_string_returns_manual(self):
        trigger_type, trigger_value = engine._parse_trigger("")
        assert trigger_type == EventTriggerType.MANUAL

    def test_phase_change_trigger(self):
        trigger_type, trigger_value = engine._parse_trigger("phase_change:departure")
        assert trigger_type == EventTriggerType.PHASE_CHANGE
        assert trigger_value["value"] == "departure"

    def test_altitude_crossing_trigger(self):
        trigger_type, trigger_value = engine._parse_trigger("altitude_crossing:3000")
        assert trigger_type == EventTriggerType.ALTITUDE_CROSSING
        assert trigger_value["value"] == "3000"

    def test_unknown_type_defaults_to_manual(self):
        trigger_type, _ = engine._parse_trigger("unknown_type:value")
        assert trigger_type == EventTriggerType.MANUAL


# ── Helper: _heading_difference ──────────────────────────


class TestHeadingDifference:
    def test_right_turn(self):
        assert engine._heading_difference(350, 10) == 20

    def test_left_turn(self):
        assert engine._heading_difference(10, 350) == -20

    def test_no_turn(self):
        assert engine._heading_difference(180, 180) == 0

    def test_half_turn(self):
        assert abs(engine._heading_difference(0, 180)) == 180
