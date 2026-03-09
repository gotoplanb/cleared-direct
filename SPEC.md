# IFR Trainer — Project Specification

## Overview

A web-based instrument flying proficiency game for general aviation pilots. The target user is a private pilot working toward or maintaining an instrument rating. The game focuses entirely on the cognitive skills that erode without practice: radio communications, ATC interaction, instrument scan, checklist discipline, and aeronautical decision making (ADM) under pressure.

This is not a visual flight simulator. There is no terrain, no out-the-window view, no photorealistic cockpit. The experience is a Garmin glass panel aesthetic — dark background, SVG instrument displays — combined with a scenario-driven game loop that feels like a game, not a training tool.

---

## Design Philosophy

- **Plausible state machine, not physics simulation.** Aircraft state advances convincingly. Instruments respond logically to autopilot inputs and events. No aerodynamic modeling required.
- **In-flight coaching, not post-flight grading.** When a player makes a poor decision or incorrect readback, the game pauses, explains why, and lets them try again. Corrections happen in the moment.
- **Every flight tells a story.** Difficulty controls how much the universe conspires against you — from a routine by-the-book flight to compounding emergencies. The debrief reconstructs what happened.
- **Game feel matters.** Animated title screen, cutscenes between phases, atmospheric audio, retro-adjacent aesthetic. This should feel like booting up a game, not launching a training module.

---

## Tech Stack

- **Backend:** Django
- **Frontend:** HTMX + Alpine.js
- **Instruments:** SVG panels updated via HTMX polling
- **Animations/Cutscenes:** CSS + JS, programmatic SVG/Canvas, no video files
- **ATC Audio:** Pre-generated MP3s for scripted calls, variable slots filled server-side
- **AI Integration:** Claude API for dynamic ATC responses, in-flight coaching explanations, and scenario generation assistance
- **Admin/Content:** Django admin for scenario and event management
- **Scenario Authoring:** YAML/JSON fixtures loaded via Django management commands

---

## Aircraft

Single engine generic GA IFR aircraft to start. Performance profile loosely based on a Cirrus SR22T class airplane:

- Cruise: ~185 KTAS at 8,000–12,000 ft
- Climb: ~1,000 FPM
- Descent: ~500–1,000 FPM typical, up to 1,500 FPM
- Avionics: Garmin G3X PFD, GTN 750 nav/comm, GFC 700 autopilot

Multi-engine (Baron-class) and turboprop (Pilatus PC-12-class) as future additions. All aircraft are config-driven so adding them later is straightforward.

---

## Difficulty Levels

Difficulty controls the **probability weights on disruption events** layered on top of a baseline flight. It is not a separate mode — it is the same flight engine with the chaos dial turned up.

| Level | Name | Description |
|---|---|---|
| 1 | Student Pilot | By the book. One minor correction from ATC. Friendly controller. Good weather. No surprises. Learn the interface and baseline flow. |
| 2 | Private Pilot | A few curveballs. Traffic, a vector change, winds shifted, one minor abnormal. Workload is real but nothing is trying to kill you. |
| 3 | Instrument Proficiency | The IFR gauntlet. Holds, missed approaches, partial panel, comm issues, convective weather reroute, terse ATC. Full IMC. Trust your scan. |
| 4 | Checkride Hell | Everything compounds. Vacuum failure mid-approach, engine roughness in a hold, frequency change at the worst moment. ADM under real pressure. |

---

## Data Models

### `AircraftType`
- `name` — display name
- `slug` — identifier
- `cruise_ktas`, `climb_fpm`, `descent_fpm`
- `performance_notes` — freetext for scenario engine reference

### `ScenarioTemplate`
- `title`, `description`
- `aircraft_type` FK
- `departure_icao`, `destination_icao`
- `route` — JSON array of waypoints/fixes
- `baseline_events` — ordered JSON event definitions
- `difficulty_event_pools` — JSON mapping difficulty level to additional event sets with probability weights
- `briefing_text` — shown in pre-flight cutscene

### `FlightSession`
- `scenario_template` FK
- `aircraft_type` FK
- `difficulty` — integer 1–4
- `phase` — enum: preflight, taxi, departure, enroute, approach, missed, holding, landed, failed
- `started_at`, `ended_at`
- `flight_state` — JSON (current instrument readings, see below)
- `event_log` — JSON array of everything that happened in sequence

### `FlightState` (JSON schema embedded in session)
```json
{
  "indicated_airspeed": 165,
  "altitude": 6000,
  "vertical_speed": 0,
  "heading": 280,
  "bank_angle": 0,
  "pitch_angle": 2,
  "autopilot": {
    "engaged": true,
    "modes": ["HDG", "ALT"],
    "selected_heading": 280,
    "selected_altitude": 6000,
    "selected_vs": 0
  },
  "nav": {
    "active_frequency": "111.95",
    "standby_frequency": "109.10",
    "comm_active": "125.35",
    "comm_standby": "121.5",
    "active_approach": "ILS 28",
    "waypoints": ["KGNV", "MERIT", "KOJM"],
    "next_waypoint": "MERIT",
    "distance_to_next": 24.3
  },
  "transponder": {
    "code": "4521",
    "mode": "ALT"
  },
  "engine": {
    "rpm": 2400,
    "oil_pressure": "normal",
    "fuel_gals_remaining": 48,
    "status": "normal"
  },
  "environment": {
    "wind_direction": 270,
    "wind_knots": 12,
    "visibility": "IFR",
    "ceiling_ft": 800,
    "icing": false
  }
}
```

### `EventQueueItem`
- `session` FK
- `order` — integer for sequencing
- `trigger_type` — enum: time, phase_change, altitude_crossing, waypoint, state_condition, manual
- `trigger_value` — JSON condition spec
- `event_type` — enum: atc_instruction, abnormal, emergency, environmental_change, traffic, atc_query
- `payload` — JSON event content (see Event Payload spec below)
- `status` — enum: pending, active, awaiting_response, resolved, expired
- `fired_at`, `resolved_at`

### `PlayerAction`
- `session` FK
- `event` FK
- `presented_at`
- `response_type` — enum: multiple_choice, text_input, checklist_item
- `options_presented` — JSON (for multiple choice)
- `response_given`
- `correct` — boolean
- `quality` — enum: best, acceptable, poor, dangerous
- `coaching_shown` — boolean
- `coaching_text` — the explanation shown if poor/dangerous
- `response_time_seconds`

### `ATCAudioClip`
- `slug` — e.g. `cleared_ils_approach`
- `template_text` — e.g. `"{callsign}, cleared ILS runway {runway} approach, {altimeter_instruction}"`
- `audio_file` — path to pre-generated MP3
- `variable_slots` — JSON list of slot names

---

## Event Payload Schema

Each event type has a defined payload structure:

**ATC Instruction**
```json
{
  "audio_clip_slug": "descend_maintain",
  "atc_text": "November 4 Uniform Tango, descend and maintain 3,000, expect ILS 28 approach.",
  "variables": {"altitude": "3000", "approach": "ILS 28"},
  "required_response_type": "text_input",
  "correct_readback_keywords": ["descend", "maintain", "3000", "ILS", "28"],
  "acceptable_variants": [...],
  "coaching_if_wrong": "A correct readback includes the instruction and the value. ATC needs to hear you confirm the altitude you're descending to and which approach you're expecting."
}
```

**Abnormal/Emergency**
```json
{
  "title": "Oil Pressure Low",
  "narration": "Your oil pressure gauge has dropped into the yellow. You're 40 miles from your destination.",
  "checklist_id": "oil_pressure_low",
  "decision_points": [
    {
      "prompt": "What do you do first?",
      "options": [
        {"text": "Declare emergency and divert to nearest airport", "quality": "acceptable"},
        {"text": "Reduce power and begin diversion, monitor for further drops", "quality": "best"},
        {"text": "Continue to destination, it's only yellow", "quality": "poor"},
        {"text": "Ignore it, probably a gauge error", "quality": "dangerous"}
      ]
    }
  ]
}
```

---

## Scenario Engine

The scenario engine runs on a **tick** — a lightweight server-side update fired every few seconds via HTMX polling from the client hitting `/session/<id>/tick/`.

Each tick:
1. Advance flight state plausibly based on current autopilot modes and aircraft config
2. Check event queue for any items whose trigger condition is now met
3. Fire triggered events — set status to `active`, push to client
4. If an event requires player response, pause tick advancement until resolved
5. Log everything to `event_log`

The tick does **not** use real aerodynamics. It advances state with simple rules:
- If autopilot ALT hold engaged: altitude stays at selected altitude
- If autopilot VS mode: altitude changes at selected VS rate
- If autopilot HDG: heading tracks toward selected heading at standard rate
- If autopilot NAV: heading follows flight plan
- Engine abnormals are state flags that the scenario sets directly

---

## Frontend Layout

### Mobile-first, three swipeable panels

```
[PFD Panel] ←→ [GTN/FMS Panel] ←→ [Autopilot + Systems Panel]
```

**PFD Panel** (primary, default view)
- Attitude indicator (SVG, cyan sky / brown earth split)
- Airspeed tape (left)
- Altitude tape (right)
- Vertical speed indicator
- Heading indicator / HSI with course needle
- Autopilot mode annunciator strip across top

**GTN Panel**
- Active/standby comm frequencies
- Active/standby nav frequencies
- Flight plan waypoint list with distances
- Active approach displayed
- Nearest airports list (context-sensitive during abnormals)

**Systems Panel**
- Autopilot mode selector (HDG, NAV, APR, VS, ALT, LVL buttons)
- Engine instruments (RPM, oil pressure, fuel)
- Transponder
- Abnormal annunciations

### Comms/Event Drawer
Pull-up drawer from bottom of screen. Appears when ATC calls or an event fires:
- ATC audio plays automatically
- Text transcript of call displayed
- Response input (text field or multiple choice buttons depending on difficulty/event type)
- Coaching text appears inline here if response is poor

### Checklist Overlay
Slides in from right when an abnormal triggers a checklist. Each item tappable to action. Scenario watches completion order.

---

## Cutscenes and Animation

All animations are programmatic — CSS + JS + SVG/Canvas. No video files. Dark background, atmospheric synth-style audio.

### Title Screen
- Animated aircraft silhouette (SVG, slow movement across screen)
- Game title with subtle glow/flicker effect
- Difficulty selection
- Retro/CRT aesthetic — optional scanline overlay

### Pre-Flight Briefing Cutscene
- Animated weather briefing panel
- Route depicted as simple moving line on a minimal chart
- Briefing text narrated or displayed: departure airport, destination, conditions, what to expect
- Sets tone and scenario context before the session starts

### Phase Transition Cutscenes
Short atmospheric beat between major flight phases:
- Departure → Enroute: altitude, heading, the world settling into cruise
- Enroute → Approach: descending, weather ahead, ATC getting busier
- Missed approach: dramatic, brief — conveys urgency before the scenario presents options

### Event Trigger Cutscenes
When a significant abnormal or emergency fires:
- Brief darkening, instrument flicker or warning light animation
- Sets up the situation before the decision point is presented

### Outcome Screens
- **Good outcome:** clean landing, brief debrief summary, XP/score
- **Poor decision made:** explanation screen mid-flight with try-again
- **Session complete:** flight log reconstruction — what happened, what you did, what the ideal line was

---

## ATC Audio System

### Pre-generated MP3 library
Common ATC calls are pre-generated with variable slots:
- Cleared for takeoff
- Frequency changes
- Altitude assignments (descend/climb and maintain)
- Vector instructions
- Approach clearances
- Go around / missed approach
- Hold instructions
- Traffic advisories

Variables (callsign, altitude, frequency, runway, fix) are filled server-side before the audio slug is resolved to the correct file. A naming convention like `descend_maintain_3000.mp3` or a parameterized lookup table maps combinations to files.

### Claude API for dynamic content
- Unusual or scenario-specific ATC calls not covered by the library
- Coaching explanations for incorrect responses
- Post-session debrief narrative
- Scenario generation from high-level description

---

## Content Authoring

Scenarios are authored as YAML and loaded via Django management command (`python manage.py load_scenario <file>`). Django admin used for reviewing, tweaking, and managing loaded content.

### Scenario YAML structure
```yaml
title: "Night IFR into KOJM"
description: "Routine IFR flight with deteriorating conditions on arrival"
aircraft: single_engine
departure: KGNV
destination: KOJM
route:
  - KGNV
  - MERIT
  - DRBIE
  - KOJM
difficulty_baseline: 2
briefing: >
  You're departing KGNV at 2100 local. Destination KOJM is reporting
  800 overcast, visibility 3 in mist. Winds 270 at 10.

baseline_events:
  - trigger: phase_change:departure
    type: atc_instruction
    payload:
      audio_clip: cleared_for_takeoff
      variables:
        runway: "28"

  - trigger: altitude_crossing:3000
    type: atc_instruction
    payload:
      audio_clip: contact_departure
      variables:
        frequency: "124.55"

difficulty_pools:
  2:
    - weight: 0.4
      type: environmental_change
      payload:
        change: ceiling_drop
        new_ceiling: 500
        trigger: waypoint:DRBIE

  3:
    - weight: 0.6
      type: abnormal
      payload:
        title: Pitot Heat Advisory
        ...

  4:
    - weight: 0.8
      type: emergency
      payload:
        title: Partial Panel - Vacuum Failure
        ...
```

---

## Build Order

Suggested sequence for Claude Code sessions:

1. **Django project scaffold** — apps, models, migrations, Django admin registration
2. **Scenario engine core** — tick loop, event queue, state advancement logic
3. **HTMX polling endpoints** — `/session/<id>/tick/`, `/session/<id>/state/`, `/session/<id>/action/`
4. **SVG instrument panels** — PFD (attitude, tapes, HSI), autopilot annunciator
5. **Frontend layout** — swipeable panels, comms drawer, checklist overlay, Alpine.js interactions
6. **Title screen and cutscene system** — animation framework, phase transitions
7. **ATC audio system** — MP3 library structure, variable slot resolution, playback
8. **Claude API integration** — coaching responses, dynamic ATC, debrief narrative
9. **Scenario YAML loader** — management command, first complete scenario end-to-end
10. **Content** — first full scenario set per difficulty level

---

## Out of Scope (for now)

- Multi-engine and turboprop aircraft types
- Multiplayer
- Real weather data integration (future: pull live METAR for departure/destination)
- ForeFlight or external app integration
- Persistent user accounts / logbook (future)
- Mobile app packaging (PWA wrapper is fine later)
