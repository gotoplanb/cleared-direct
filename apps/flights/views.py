from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.aircraft.models import AircraftType
from apps.scenarios.models import ScenarioTemplate

from . import engine
from .models import (
    EventQueueItem,
    EventStatus,
    FlightSession,
    PlayerAction,
    ResponseQuality,
    ResponseType,
)
from .strings import resolve, resolve_payload, SUPPORTED_LANGUAGES


def index(request):
    """Landing page — scenario selection."""
    scenarios = ScenarioTemplate.objects.select_related("aircraft_type").all()
    return render(request, "flights/index.html", {
        "scenarios": scenarios,
        "languages": SUPPORTED_LANGUAGES,
    })


@csrf_exempt
@require_POST
def start_session(request):
    """Create a new flight session from a scenario template."""
    data = json.loads(request.body) if request.content_type == "application/json" else request.POST
    scenario_id = data.get("scenario_id")
    difficulty = int(data.get("difficulty", 2))
    language = data.get("language", "en")
    if language not in SUPPORTED_LANGUAGES:
        language = "en"

    scenario = get_object_or_404(ScenarioTemplate, id=scenario_id)

    session = FlightSession.objects.create(
        scenario_template=scenario,
        aircraft_type=scenario.aircraft_type,
        difficulty=difficulty,
        language=language,
    )
    engine.initialize_session(session)

    return JsonResponse({
        "session_id": session.id,
        "scenario": scenario.title,
        "difficulty": session.get_difficulty_display(),
        "phase": session.phase,
    })


@require_GET
def session_detail(request, session_id):
    """Main flight session page — renders the instrument panel."""
    session = get_object_or_404(
        FlightSession.objects.select_related("scenario_template", "aircraft_type"),
        id=session_id,
    )
    return render(request, "flights/session.html", {
        "session": session,
        "flight_state_json": json.dumps(session.flight_state),
        "language": session.language,
    })


@require_GET
def session_tick(request, session_id):
    """HTMX polling endpoint — advance the game one tick."""
    session = get_object_or_404(FlightSession, id=session_id)
    result = engine.tick(session)
    return JsonResponse(result)


@require_GET
def session_state(request, session_id):
    """Return current flight state as JSON (for instrument rendering)."""
    session = get_object_or_404(FlightSession, id=session_id)
    return JsonResponse({
        "phase": session.phase,
        "tick": session.tick_count,
        "paused": session.paused,
        "flight_state": session.flight_state,
    })


@csrf_exempt
@require_POST
def session_action(request, session_id):
    """Submit a player action in response to an event."""
    session = get_object_or_404(FlightSession, id=session_id)
    data = json.loads(request.body) if request.content_type == "application/json" else request.POST

    event_id = data.get("event_id")
    response_text = data.get("response", "")

    event = get_object_or_404(
        EventQueueItem,
        id=event_id,
        session=session,
        status=EventStatus.AWAITING_RESPONSE,
    )

    # Evaluate the response (resolve string keys for the session's language)
    lang = session.language or "en"
    resolved_payload = resolve_payload(event.payload or {}, lang=lang)
    quality, correct, coaching = _evaluate_response(event, response_text, resolved_payload)

    # Record the player action
    action = PlayerAction.objects.create(
        session=session,
        event=event,
        response_type=_get_response_type(event),
        options_presented=_get_options(event),
        response_given=response_text,
        correct=correct,
        quality=quality,
        coaching_shown=bool(coaching),
        coaching_text=coaching,
    )

    # Resolve the event
    engine.resolve_event(event, response=response_text, quality=quality)

    return JsonResponse({
        "correct": correct,
        "quality": quality,
        "coaching": coaching,
        "event_resolved": True,
    })


@csrf_exempt
@require_POST
def session_phase(request, session_id):
    """Transition the flight to a new phase."""
    session = get_object_or_404(FlightSession, id=session_id)
    data = json.loads(request.body) if request.content_type == "application/json" else request.POST

    new_phase = data.get("phase", "")
    engine.transition_phase(session, new_phase)

    return JsonResponse({
        "phase": session.phase,
        "flight_state": session.flight_state,
    })


def _evaluate_response(
    event: EventQueueItem, response: str, resolved_payload: dict | None = None
) -> tuple[str, bool, str]:
    """Evaluate a player's response against the event payload.

    Returns (quality, correct, coaching_text).
    resolved_payload has string keys already resolved to text.
    """
    payload = resolved_payload or event.payload or {}

    # ATC readback evaluation
    if payload.get("correct_readback_keywords"):
        keywords = payload["correct_readback_keywords"]
        response_lower = response.lower()
        matched = sum(1 for kw in keywords if kw.lower() in response_lower)
        ratio = matched / len(keywords) if keywords else 0

        if ratio >= 0.8:
            return ResponseQuality.BEST, True, ""
        elif ratio >= 0.5:
            return ResponseQuality.ACCEPTABLE, True, ""
        else:
            coaching = payload.get("coaching_if_wrong", "Review your readback — make sure to include all key elements.")
            return ResponseQuality.POOR, False, coaching

    # Multiple choice evaluation
    if payload.get("decision_points"):
        for dp in payload["decision_points"]:
            options = dp.get("options", [])
            for opt in options:
                if opt.get("text", "").lower() == response.lower():
                    q = opt.get("quality", "acceptable")
                    correct = q in ("best", "acceptable")
                    coaching = ""
                    if q in ("poor", "dangerous"):
                        coaching = payload.get("coaching_if_wrong", "Consider the consequences of that decision.")
                    return q, correct, coaching

    # Default: acceptable
    return ResponseQuality.ACCEPTABLE, True, ""


def _get_response_type(event: EventQueueItem) -> str:
    payload = event.payload or {}
    if payload.get("required_response_type"):
        return payload["required_response_type"]
    if payload.get("decision_points"):
        return ResponseType.MULTIPLE_CHOICE
    return ResponseType.TEXT_INPUT


def _get_options(event: EventQueueItem) -> list:
    payload = event.payload or {}
    for dp in payload.get("decision_points", []):
        return [opt.get("text", "") for opt in dp.get("options", [])]
    return []
