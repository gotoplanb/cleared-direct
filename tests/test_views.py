"""Tests for flight views — endpoints, response evaluation, session lifecycle."""

import json

import pytest
from django.test import Client

from apps.flights.models import (
    EventQueueItem,
    EventStatus,
    FlightPhase,
    FlightSession,
    ResponseQuality,
)
from apps.flights.views import _evaluate_response, _get_options, _get_response_type


# ── View Endpoints ───────────────────────────────────────


@pytest.fixture
def client():
    return Client()


class TestIndexView:
    def test_index_returns_200(self, client, scenario):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"CLEARED DIRECT" in resp.content


class TestStartSession:
    def test_creates_session(self, client, scenario):
        resp = client.post(
            "/session/start/",
            json.dumps({"scenario_id": scenario.id, "difficulty": 2}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["phase"] == FlightPhase.PREFLIGHT

    def test_invalid_scenario_404(self, client, db):
        resp = client.post(
            "/session/start/",
            json.dumps({"scenario_id": 9999}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestSessionDetail:
    def test_renders_session_page(self, client, initialized_session):
        resp = client.get(f"/session/{initialized_session.id}/")
        assert resp.status_code == 200
        assert b"Cleared Direct" in resp.content


class TestSessionTick:
    def test_tick_returns_json(self, client, enroute_session):
        resp = client.get(f"/session/{enroute_session.id}/tick/")
        assert resp.status_code == 200
        data = resp.json()
        assert "tick" in data
        assert "flight_state" in data


class TestSessionState:
    def test_state_returns_current(self, client, initialized_session):
        resp = client.get(f"/session/{initialized_session.id}/state/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["phase"] == FlightPhase.PREFLIGHT
        assert "flight_state" in data


class TestSessionPhase:
    def test_transitions_phase(self, client, initialized_session):
        resp = client.post(
            f"/session/{initialized_session.id}/phase/",
            json.dumps({"phase": "enroute"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["phase"] == FlightPhase.ENROUTE


class TestSessionAction:
    def test_submit_correct_readback(self, client, initialized_session):
        # Fire the departure event
        event = initialized_session.event_queue.filter(
            trigger_type="phase_change"
        ).first()
        event.status = EventStatus.AWAITING_RESPONSE
        event.save()

        resp = client.post(
            f"/session/{initialized_session.id}/action/",
            json.dumps({
                "event_id": event.id,
                "response": "Cleared for takeoff runway 28",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["correct"] is True
        assert data["event_resolved"] is True

    def test_submit_poor_readback(self, client, initialized_session):
        event = initialized_session.event_queue.filter(
            trigger_type="phase_change"
        ).first()
        event.status = EventStatus.AWAITING_RESPONSE
        event.save()

        resp = client.post(
            f"/session/{initialized_session.id}/action/",
            json.dumps({
                "event_id": event.id,
                "response": "roger",
            }),
            content_type="application/json",
        )
        data = resp.json()
        assert data["correct"] is False
        assert data["quality"] == ResponseQuality.POOR
        assert data["coaching"] != ""


# ── Response Evaluation ──────────────────────────────────


class TestEvaluateResponse:
    @pytest.fixture
    def readback_event(self, initialized_session):
        return initialized_session.event_queue.filter(
            trigger_type="phase_change"
        ).first()

    def test_full_readback_is_best(self, readback_event):
        quality, correct, coaching = _evaluate_response(
            readback_event, "Cleared for takeoff runway 28"
        )
        assert quality == ResponseQuality.BEST
        assert correct is True
        assert coaching == ""

    def test_partial_readback_is_acceptable(self, readback_event):
        quality, correct, coaching = _evaluate_response(
            readback_event, "Cleared for takeoff"
        )
        assert quality == ResponseQuality.ACCEPTABLE
        assert correct is True

    def test_bad_readback_is_poor(self, readback_event):
        quality, correct, coaching = _evaluate_response(readback_event, "ok")
        assert quality == ResponseQuality.POOR
        assert correct is False
        assert coaching != ""

    def test_decision_point_best_option(self, enroute_session):
        event = EventQueueItem.objects.create(
            session=enroute_session,
            order=50,
            trigger_type="manual",
            trigger_value={"type": "manual"},
            event_type="abnormal",
            payload={
                "decision_points": [
                    {
                        "prompt": "What do you do?",
                        "options": [
                            {"text": "Turn on pitot heat", "quality": "best"},
                            {"text": "Ignore it", "quality": "dangerous"},
                        ],
                    }
                ],
                "coaching_if_wrong": "Turn on pitot heat!",
            },
            status=EventStatus.AWAITING_RESPONSE,
        )
        quality, correct, coaching = _evaluate_response(event, "Turn on pitot heat")
        assert quality == "best"
        assert correct is True

    def test_decision_point_dangerous_option(self, enroute_session):
        event = EventQueueItem.objects.create(
            session=enroute_session,
            order=51,
            trigger_type="manual",
            trigger_value={"type": "manual"},
            event_type="abnormal",
            payload={
                "decision_points": [
                    {
                        "prompt": "What do you do?",
                        "options": [
                            {"text": "Turn on pitot heat", "quality": "best"},
                            {"text": "Ignore it", "quality": "dangerous"},
                        ],
                    }
                ],
                "coaching_if_wrong": "Turn on pitot heat!",
            },
            status=EventStatus.AWAITING_RESPONSE,
        )
        quality, correct, coaching = _evaluate_response(event, "Ignore it")
        assert quality == "dangerous"
        assert correct is False
        assert "pitot heat" in coaching.lower()

    def test_no_criteria_defaults_acceptable(self, enroute_session):
        event = EventQueueItem.objects.create(
            session=enroute_session,
            order=52,
            trigger_type="manual",
            trigger_value={"type": "manual"},
            event_type="atc_instruction",
            payload={"atc_text": "Something"},
            status=EventStatus.AWAITING_RESPONSE,
        )
        quality, correct, coaching = _evaluate_response(event, "anything")
        assert quality == ResponseQuality.ACCEPTABLE
        assert correct is True
