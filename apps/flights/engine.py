"""
Scenario engine — tick-based flight state machine.

Each tick:
1. Advance flight state based on autopilot modes and aircraft performance
2. Check event queue for triggered items
3. Fire triggered events
4. If an event requires player response, pause advancement
5. Log everything
"""

import copy
import random
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.aircraft.models import AircraftType

from .models import (
    EventQueueItem,
    EventStatus,
    EventTriggerType,
    FlightPhase,
    FlightSession,
)

# Tick interval in seconds (matches HTMX polling rate)
TICK_INTERVAL = 3

# Standard rate turn: 3 degrees per second
STANDARD_RATE_TURN = 3.0


def initialize_session(session: FlightSession) -> None:
    """Set up a new flight session from its scenario template.

    Populates initial flight state, builds the event queue from
    baseline events + difficulty pool picks.
    """
    template = session.scenario_template
    aircraft = session.aircraft_type

    # Build initial flight state from template
    state = copy.deepcopy(session.flight_state)
    state["indicated_airspeed"] = 0
    state["altitude"] = 0
    state["heading"] = 0
    state["nav"]["waypoints"] = list(template.route)
    state["nav"]["next_waypoint"] = template.route[0] if template.route else ""
    state["engine"]["fuel_gals_remaining"] = 60  # default full tanks
    state["engine"]["rpm"] = 0
    state["engine"]["status"] = "normal"

    # Apply environment from scenario if present
    if "environment" in (template.baseline_events[0].get("payload", {}) if template.baseline_events else {}):
        pass  # will be set by events

    session.flight_state = state
    session.phase = FlightPhase.PREFLIGHT
    session.event_log = []
    session.tick_count = 0
    session.save()

    # Build event queue: baseline events always included
    order = 0
    for event_def in template.baseline_events:
        trigger_type, trigger_value = _parse_trigger(event_def.get("trigger", ""))
        EventQueueItem.objects.create(
            session=session,
            order=order,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            event_type=event_def.get("type", "atc_instruction"),
            payload=event_def.get("payload", {}),
            status=EventStatus.PENDING,
        )
        order += 1

    # Add difficulty pool events based on probability weights
    difficulty_pools = template.difficulty_event_pools or {}
    for level in range(1, session.difficulty + 1):
        pool = difficulty_pools.get(str(level), [])
        for item in pool:
            weight = item.get("weight", 0.5)
            if random.random() < weight:
                trigger_type, trigger_value = _parse_trigger(
                    item.get("trigger", item.get("payload", {}).get("trigger", ""))
                )
                EventQueueItem.objects.create(
                    session=session,
                    order=order,
                    trigger_type=trigger_type,
                    trigger_value=trigger_value or {"type": "manual"},
                    event_type=item.get("type", "abnormal"),
                    payload=item.get("payload", {}),
                    status=EventStatus.PENDING,
                )
                order += 1


def _parse_trigger(trigger_str: str) -> tuple[str, dict]:
    """Parse a trigger string like 'phase_change:departure' into type and value."""
    if not trigger_str:
        return EventTriggerType.MANUAL, {"type": "manual"}

    if ":" in trigger_str:
        parts = trigger_str.split(":", 1)
        trigger_type = parts[0]
        trigger_val = parts[1]
    else:
        trigger_type = trigger_str
        trigger_val = ""

    type_map = {
        "phase_change": EventTriggerType.PHASE_CHANGE,
        "altitude_crossing": EventTriggerType.ALTITUDE_CROSSING,
        "waypoint": EventTriggerType.WAYPOINT,
        "time": EventTriggerType.TIME,
        "state_condition": EventTriggerType.STATE_CONDITION,
        "manual": EventTriggerType.MANUAL,
    }
    resolved_type = type_map.get(trigger_type, EventTriggerType.MANUAL)

    return resolved_type, {"type": trigger_type, "value": trigger_val}


def tick(session: FlightSession) -> dict[str, Any]:
    """Execute one game tick. Returns tick result with any fired events."""
    if session.paused or session.phase in (FlightPhase.LANDED, FlightPhase.FAILED):
        return {"paused": True, "events": []}

    # Check if waiting for player response
    awaiting = session.event_queue.filter(status=EventStatus.AWAITING_RESPONSE).first()
    if awaiting:
        return {
            "paused": True,
            "awaiting_event": _serialize_event(awaiting),
            "events": [],
        }

    session.tick_count += 1

    # 1. Advance flight state
    _advance_state(session)

    # 2. Check and fire events
    fired_events = _check_event_triggers(session)

    # 3. Log tick
    log_entry = {
        "tick": session.tick_count,
        "timestamp": timezone.now().isoformat(),
        "phase": session.phase,
        "altitude": session.flight_state.get("altitude", 0),
        "airspeed": session.flight_state.get("indicated_airspeed", 0),
        "heading": session.flight_state.get("heading", 0),
        "events_fired": [e.id for e in fired_events],
    }
    event_log = session.event_log or []
    event_log.append(log_entry)
    session.event_log = event_log
    session.save()

    return {
        "paused": False,
        "tick": session.tick_count,
        "phase": session.phase,
        "flight_state": session.flight_state,
        "events": [_serialize_event(e) for e in fired_events],
    }


def _advance_state(session: FlightSession) -> None:
    """Advance flight state based on autopilot modes and aircraft config."""
    state = session.flight_state
    aircraft = session.aircraft_type
    dt = TICK_INTERVAL  # seconds per tick

    # Only advance if we're actually flying
    if session.phase in (FlightPhase.PREFLIGHT, FlightPhase.TAXI):
        return

    ap = state.get("autopilot", {})
    modes = ap.get("modes", []) if ap.get("engaged") else []
    current_alt = state.get("altitude", 0)
    current_hdg = state.get("heading", 0)
    current_ias = state.get("indicated_airspeed", 0)

    # Heading
    if "HDG" in modes or "NAV" in modes:
        target_hdg = ap.get("selected_heading", current_hdg)
        hdg_diff = _heading_difference(current_hdg, target_hdg)
        if abs(hdg_diff) > 0.5:
            turn_rate = min(abs(hdg_diff) / dt, STANDARD_RATE_TURN)
            direction = 1 if hdg_diff > 0 else -1
            new_hdg = (current_hdg + direction * turn_rate * dt) % 360
            state["heading"] = round(new_hdg, 1)
            state["bank_angle"] = round(direction * min(abs(hdg_diff), 25), 1)
        else:
            state["heading"] = target_hdg
            state["bank_angle"] = 0

    # Altitude
    if "ALT" in modes:
        target_alt = ap.get("selected_altitude", current_alt)
        if abs(current_alt - target_alt) < 50:
            state["altitude"] = target_alt
            state["vertical_speed"] = 0
            state["pitch_angle"] = 2
        else:
            # Climb or descend to target
            if current_alt < target_alt:
                vs = min(aircraft.climb_fpm, (target_alt - current_alt) * 60 / dt)
                alt_change = vs * dt / 60
                state["altitude"] = round(min(current_alt + alt_change, target_alt))
                state["vertical_speed"] = round(vs)
                state["pitch_angle"] = 5
            else:
                vs = min(aircraft.descent_fpm, (current_alt - target_alt) * 60 / dt)
                alt_change = vs * dt / 60
                state["altitude"] = round(max(current_alt - alt_change, target_alt))
                state["vertical_speed"] = round(-vs)
                state["pitch_angle"] = -2

    elif "VS" in modes:
        selected_vs = ap.get("selected_vs", 0)
        alt_change = selected_vs * dt / 60
        state["altitude"] = round(current_alt + alt_change)
        state["vertical_speed"] = selected_vs
        if selected_vs > 0:
            state["pitch_angle"] = 5
        elif selected_vs < 0:
            state["pitch_angle"] = -2
        else:
            state["pitch_angle"] = 2

    # Airspeed - simplified: converge toward cruise speed when airborne
    target_ias = aircraft.cruise_ktas
    if abs(current_ias - target_ias) > 2:
        accel = 5 if current_ias < target_ias else -3  # knots per tick
        state["indicated_airspeed"] = round(
            current_ias + accel * dt / TICK_INTERVAL, 1
        )
    else:
        state["indicated_airspeed"] = target_ias

    # Distance to next waypoint - decrement based on groundspeed
    nav = state.get("nav", {})
    dist = nav.get("distance_to_next", 0)
    if dist > 0:
        gs_nm_per_sec = current_ias / 3600  # rough NM/s (ignoring wind for now)
        new_dist = max(0, dist - gs_nm_per_sec * dt)
        nav["distance_to_next"] = round(new_dist, 1)

        # Waypoint reached
        if new_dist == 0:
            waypoints = nav.get("waypoints", [])
            current_wp = nav.get("next_waypoint", "")
            if current_wp in waypoints:
                idx = waypoints.index(current_wp)
                if idx + 1 < len(waypoints):
                    nav["next_waypoint"] = waypoints[idx + 1]
                    nav["distance_to_next"] = 30.0  # placeholder distance

    # Fuel burn - roughly 15 gal/hr for SR22T class
    fuel = state.get("engine", {}).get("fuel_gals_remaining", 0)
    fuel_burn_per_tick = 15.0 / 3600 * dt
    state["engine"]["fuel_gals_remaining"] = round(
        max(0, fuel - fuel_burn_per_tick), 1
    )

    session.flight_state = state


def _heading_difference(current: float, target: float) -> float:
    """Signed heading difference. Positive = turn right, negative = turn left."""
    diff = (target - current) % 360
    if diff > 180:
        diff -= 360
    return diff


def _check_event_triggers(session: FlightSession) -> list[EventQueueItem]:
    """Check pending events and fire any whose trigger conditions are met."""
    pending = session.event_queue.filter(status=EventStatus.PENDING).order_by("order")
    fired = []

    for event in pending:
        if _trigger_met(session, event):
            event.status = EventStatus.ACTIVE
            event.fired_at = timezone.now()

            # If the event requires a player response, set to awaiting
            payload = event.payload or {}
            if (
                payload.get("required_response_type")
                or payload.get("decision_points")
                or payload.get("options")
            ):
                event.status = EventStatus.AWAITING_RESPONSE

            event.save()
            fired.append(event)

            # Log the event firing
            log_entry = {
                "tick": session.tick_count,
                "timestamp": timezone.now().isoformat(),
                "event_fired": {
                    "id": event.id,
                    "type": event.event_type,
                    "order": event.order,
                },
            }
            event_log = session.event_log or []
            event_log.append(log_entry)
            session.event_log = event_log

    return fired


def _trigger_met(session: FlightSession, event: EventQueueItem) -> bool:
    """Evaluate whether an event's trigger condition is met."""
    trigger = event.trigger_value or {}
    trigger_type = trigger.get("type", "")
    trigger_val = trigger.get("value", "")

    if event.trigger_type == EventTriggerType.PHASE_CHANGE:
        return session.phase == trigger_val

    if event.trigger_type == EventTriggerType.ALTITUDE_CROSSING:
        try:
            target_alt = int(trigger_val)
        except (ValueError, TypeError):
            return False
        current_alt = session.flight_state.get("altitude", 0)
        # Fire when crossing through the target altitude (within 200ft)
        return abs(current_alt - target_alt) < 200

    if event.trigger_type == EventTriggerType.WAYPOINT:
        nav = session.flight_state.get("nav", {})
        next_wp = nav.get("next_waypoint", "")
        dist = nav.get("distance_to_next", 999)
        # Fire when approaching the named waypoint
        return next_wp == trigger_val and dist < 5.0

    if event.trigger_type == EventTriggerType.TIME:
        try:
            tick_target = int(trigger_val)
        except (ValueError, TypeError):
            return False
        return session.tick_count >= tick_target

    if event.trigger_type == EventTriggerType.MANUAL:
        return False  # only fired programmatically

    return False


def transition_phase(session: FlightSession, new_phase: str) -> None:
    """Transition the flight to a new phase, applying state changes."""
    old_phase = session.phase
    session.phase = new_phase

    state = session.flight_state
    aircraft = session.aircraft_type

    if new_phase == FlightPhase.TAXI:
        state["engine"]["rpm"] = 1000
        state["indicated_airspeed"] = 0

    elif new_phase == FlightPhase.DEPARTURE:
        state["engine"]["rpm"] = 2400
        state["indicated_airspeed"] = 80
        state["altitude"] = 0
        state["autopilot"]["engaged"] = False

    elif new_phase == FlightPhase.ENROUTE:
        # Set cruise altitude from scenario briefing (default 6000)
        cruise_alt = 6000
        cruise_hdg = 280
        route = session.scenario_template.route or []
        state["indicated_airspeed"] = aircraft.cruise_ktas
        state["altitude"] = cruise_alt
        state["vertical_speed"] = 0
        state["heading"] = cruise_hdg
        state["autopilot"]["engaged"] = True
        state["autopilot"]["modes"] = ["HDG", "ALT"]
        state["autopilot"]["selected_altitude"] = cruise_alt
        state["autopilot"]["selected_heading"] = cruise_hdg
        state["engine"]["rpm"] = 2400
        # Set up waypoint navigation
        if route and len(route) > 1:
            nav = state.get("nav", {})
            nav["next_waypoint"] = route[1]
            nav["distance_to_next"] = 30.0
            state["nav"] = nav

    elif new_phase == FlightPhase.APPROACH:
        state["autopilot"]["modes"] = ["HDG", "ALT"]
        state["autopilot"]["selected_altitude"] = 3000

    elif new_phase == FlightPhase.LANDED:
        state["indicated_airspeed"] = 0
        state["altitude"] = 0
        state["vertical_speed"] = 0
        state["autopilot"]["engaged"] = False
        state["engine"]["rpm"] = 1000
        session.ended_at = timezone.now()

    elif new_phase == FlightPhase.FAILED:
        session.ended_at = timezone.now()

    session.flight_state = state

    # Log transition
    log_entry = {
        "tick": session.tick_count,
        "timestamp": timezone.now().isoformat(),
        "phase_transition": {"from": old_phase, "to": new_phase},
    }
    event_log = session.event_log or []
    event_log.append(log_entry)
    session.event_log = event_log

    session.save()


def resolve_event(
    event: EventQueueItem,
    response: str = "",
    quality: str = "",
) -> None:
    """Mark an event as resolved after player response."""
    event.status = EventStatus.RESOLVED
    event.resolved_at = timezone.now()
    event.save()


def _serialize_event(event: EventQueueItem) -> dict:
    """Serialize an event for the frontend."""
    return {
        "id": event.id,
        "order": event.order,
        "event_type": event.event_type,
        "status": event.status,
        "payload": event.payload,
        "fired_at": event.fired_at.isoformat() if event.fired_at else None,
    }
