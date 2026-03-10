from django.db import models


class FlightPhase(models.TextChoices):
    PREFLIGHT = "preflight", "Pre-Flight"
    TAXI = "taxi", "Taxi"
    DEPARTURE = "departure", "Departure"
    ENROUTE = "enroute", "Enroute"
    APPROACH = "approach", "Approach"
    MISSED = "missed", "Missed Approach"
    HOLDING = "holding", "Holding"
    LANDED = "landed", "Landed"
    FAILED = "failed", "Failed"


class DifficultyLevel(models.IntegerChoices):
    STUDENT_PILOT = 1, "Student Pilot"
    PRIVATE_PILOT = 2, "Private Pilot"
    INSTRUMENT_PROFICIENCY = 3, "Instrument Proficiency"
    CHECKRIDE_HELL = 4, "Checkride Hell"


class EventTriggerType(models.TextChoices):
    TIME = "time", "Time"
    PHASE_CHANGE = "phase_change", "Phase Change"
    ALTITUDE_CROSSING = "altitude_crossing", "Altitude Crossing"
    WAYPOINT = "waypoint", "Waypoint"
    STATE_CONDITION = "state_condition", "State Condition"
    MANUAL = "manual", "Manual"


class EventType(models.TextChoices):
    ATC_INSTRUCTION = "atc_instruction", "ATC Instruction"
    ABNORMAL = "abnormal", "Abnormal"
    EMERGENCY = "emergency", "Emergency"
    ENVIRONMENTAL_CHANGE = "environmental_change", "Environmental Change"
    TRAFFIC = "traffic", "Traffic"
    ATC_QUERY = "atc_query", "ATC Query"


class EventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    AWAITING_RESPONSE = "awaiting_response", "Awaiting Response"
    RESOLVED = "resolved", "Resolved"
    EXPIRED = "expired", "Expired"


class ResponseType(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
    TEXT_INPUT = "text_input", "Text Input"
    CHECKLIST_ITEM = "checklist_item", "Checklist Item"


class ResponseQuality(models.TextChoices):
    BEST = "best", "Best"
    ACCEPTABLE = "acceptable", "Acceptable"
    POOR = "poor", "Poor"
    DANGEROUS = "dangerous", "Dangerous"


DEFAULT_FLIGHT_STATE = {
    "indicated_airspeed": 0,
    "altitude": 0,
    "vertical_speed": 0,
    "heading": 0,
    "bank_angle": 0,
    "pitch_angle": 0,
    "autopilot": {
        "engaged": False,
        "modes": [],
        "selected_heading": 0,
        "selected_altitude": 0,
        "selected_vs": 0,
    },
    "nav": {
        "active_frequency": "",
        "standby_frequency": "",
        "comm_active": "",
        "comm_standby": "121.5",
        "active_approach": "",
        "waypoints": [],
        "next_waypoint": "",
        "distance_to_next": 0,
    },
    "transponder": {
        "code": "1200",
        "mode": "ALT",
    },
    "engine": {
        "rpm": 0,
        "oil_pressure": "normal",
        "fuel_gals_remaining": 0,
        "status": "normal",
    },
    "environment": {
        "wind_direction": 0,
        "wind_knots": 0,
        "visibility": "VFR",
        "ceiling_ft": 10000,
        "icing": False,
    },
}


class FlightSession(models.Model):
    scenario_template = models.ForeignKey(
        "scenarios.ScenarioTemplate",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    aircraft_type = models.ForeignKey(
        "aircraft.AircraftType",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    difficulty = models.IntegerField(choices=DifficultyLevel.choices)
    phase = models.CharField(
        max_length=20,
        choices=FlightPhase.choices,
        default=FlightPhase.PREFLIGHT,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    flight_state = models.JSONField(default=dict)
    event_log = models.JSONField(
        default=list,
        help_text="Chronological log of everything that happened",
    )
    tick_count = models.PositiveIntegerField(default=0)
    paused = models.BooleanField(default=False)
    language = models.CharField(max_length=5, default="en")

    class Meta:
        db_table = "ifr_flight_session"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Flight {self.id}: {self.scenario_template.title} (Difficulty {self.difficulty})"

    def save(self, *args, **kwargs):
        if not self.flight_state:
            self.flight_state = DEFAULT_FLIGHT_STATE.copy()
        super().save(*args, **kwargs)


class EventQueueItem(models.Model):
    session = models.ForeignKey(
        FlightSession,
        on_delete=models.CASCADE,
        related_name="event_queue",
    )
    order = models.PositiveIntegerField()
    trigger_type = models.CharField(max_length=20, choices=EventTriggerType.choices)
    trigger_value = models.JSONField(
        help_text="Condition spec for when this event fires",
    )
    event_type = models.CharField(max_length=25, choices=EventType.choices)
    payload = models.JSONField(help_text="Event content per Event Payload Schema")
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PENDING,
    )
    fired_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ifr_event_queue_item"
        ordering = ["order"]

    def __str__(self):
        return f"Event {self.order}: {self.event_type} ({self.status})"


class PlayerAction(models.Model):
    session = models.ForeignKey(
        FlightSession,
        on_delete=models.CASCADE,
        related_name="player_actions",
    )
    event = models.ForeignKey(
        EventQueueItem,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    presented_at = models.DateTimeField(auto_now_add=True)
    response_type = models.CharField(max_length=20, choices=ResponseType.choices)
    options_presented = models.JSONField(
        default=list,
        help_text="For multiple choice events",
    )
    response_given = models.TextField(blank=True)
    correct = models.BooleanField(null=True)
    quality = models.CharField(
        max_length=10,
        choices=ResponseQuality.choices,
        blank=True,
    )
    coaching_shown = models.BooleanField(default=False)
    coaching_text = models.TextField(blank=True)
    response_time_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "ifr_player_action"
        ordering = ["presented_at"]

    def __str__(self):
        return f"Action on Event {self.event.order}: {self.quality or 'pending'}"
