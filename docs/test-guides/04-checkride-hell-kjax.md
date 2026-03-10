# Test Guide: Checkride Hell into Jacksonville

**Difficulty:** 4 — Checkride Hell
**Route:** KGNV → HERMY → WLKRT → ADERR → KJAX
**Altitude:** 8,000 MSL
**Conditions:** Night IMC — 800 overcast, vis 2 at departure; 400 overcast, vis 1 fog at destination

---

## How to Use This Guide

1. Start the scenario and select **Checkride** difficulty
2. ALL difficulty pools (2, 3, 4) are active
3. This scenario throws everything: non-standard hold, partial panel, comm failure, go-around, low fuel
4. Events fire both by waypoint/altitude triggers and time-based triggers
5. Multiple events may queue rapidly — the game pauses for each one requiring a response

---

## Flight Flow

### Phase: Preflight → Taxi → Departure

### Event 1: Takeoff Clearance (with expected altitude)

| Field | Value |
|-------|-------|
| **Trigger** | Phase change to departure |
| **ATC Says** | "Runway 28, cleared for takeoff. Fly heading 050, climb and maintain 4,000. Expect 8,000 ten minutes after departure." |
| **Keywords** | `cleared`, `takeoff`, `28`, `heading`, `050`, `4000`, `8000` |

**Note:** This clearance includes an *expected altitude* — critical for lost-comm procedures.

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Cleared takeoff 28, heading 050, climb maintain 4000, expect 8000" | Best | Yes |
| "Cleared 28, 050, 4000, expect 8000" | Best | Yes |
| "Cleared takeoff 28" | Acceptable | Yes |
| "Roger" | Poor | No |

### Event 2: Climb + Frequency Change

| Field | Value |
|-------|-------|
| **Trigger** | Altitude crossing 4,000 ft |
| **ATC Says** | "Climb and maintain 8,000. Contact Jacksonville Center on 128.35." |
| **Keywords** | `climb`, `maintain`, `8000`, `128.35` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Climb maintain 8000, Center 128.35" | Best | Yes |

### Event 3 (Pool 2, 70% chance): Icing Advisory

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint HERMY |
| **Type** | Environmental — informational, no response needed |
| **Narration** | "PIREP — moderate rime icing between 6,000 and 10,000…" |

Verify this displays as a narration overlay. No player response required.

### Event 4 (Pool 3, always fires): Unreliable Airspeed

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 15) |
| **Type** | Multiple choice decision |

| Option | Quality | Correct? |
|--------|---------|----------|
| "Turn on pitot heat, set known power setting, cross-check GPS groundspeed" | **Best** | Yes |
| "Trust the airspeed indicator, it'll recover" | **Dangerous** | No |
| "Declare emergency and request lower altitude" | Acceptable | Yes |
| "Pitch for best glide attitude by feel" | Poor | No |

**Coaching:** "With unreliable airspeed: (1) pitot heat ON, (2) set known power, (3) cross-check GPS groundspeed…"

### Event 5 (Pool 4, always fires): Vacuum Failure — Partial Panel

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 20) |
| **Type** | Multiple choice decision |

| Option | Quality | Correct? |
|--------|---------|----------|
| "Transition to partial panel: airspeed, turn coordinator, altimeter. Use GPS track for heading." | **Best** | Yes |
| "Trust the attitude indicator, it might recover" | **Dangerous** | No |
| "Declare emergency, request vectors to nearest VFR" | Acceptable | Yes |
| "Engage autopilot — it might still work" | Poor | No |

**Coaching:** "Vacuum failure = no AI, no HI. Scan: airspeed (pitch), turn coordinator (bank), altimeter (trend). GPS track replaces HI…"

### Event 6: Non-Standard Holding Instructions

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint WLKRT |
| **ATC Says** | "Hold southwest of WLKRT on the 225 radial, right turns. Expect further clearance at 2245. Maintain 8,000." |
| **Keywords** | `hold`, `southwest`, `WLKRT`, `225`, `right`, `2245`, `8000` |

**This is the hardest readback in the game.** Non-standard hold (right turns) requires all elements.

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Hold southwest WLKRT, 225 radial, right turns, EFC 2245, maintain 8000" | Best | Yes |
| "Hold WLKRT right turns 225 2245 8000" | Best | Yes |
| "Hold WLKRT" | Poor | No |

### Event 7: Approach Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 35) |
| **ATC Says** | "Cleared ILS runway 7 left approach. Descend and maintain 3,000. Contact Jacksonville tower on 118.3 at JOTLY." |
| **Keywords** | `cleared`, `ILS`, `7`, `left`, `3000`, `118.3` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Cleared ILS 7 left, descend maintain 3000, tower 118.3 at JOTLY" | Best | Yes |

### Event 8 (Pool 3, 80% chance): Communication Failure

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 40) |
| **Type** | Multiple choice decision |

| Option | Quality | Correct? |
|--------|---------|----------|
| "Squawk 7600, fly the approach as cleared, land" | **Best** | Yes |
| "Try every frequency including 121.5, circle the airport" | Poor | No |
| "Squawk 7600, fly the approach, go missed if no light gun signal" | Acceptable | Yes |
| "Turn around and go back to Gainesville" | Poor | No |

**Coaching:** "Lost comms (91.185): squawk 7600. You've been cleared — fly the approach and land."

### Event 9: Go-Around

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 50) |
| **ATC Says** | "Go around! Traffic on the runway. Climb heading 070, maintain 2,000. Contact approach on 124.0." |
| **Keywords** | `going around`, `heading`, `070`, `2000`, `124.0` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Going around, heading 070, 2000, approach 124.0" | Best | Yes |
| "Roger" | Poor | No |

### Event 10 (Pool 4, 90% chance): Low Fuel Warning

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 55) |
| **Type** | Multiple choice decision |

| Option | Quality | Correct? |
|--------|---------|----------|
| "Declare minimum fuel to ATC, request priority handling, brief the approach" | **Best** | Yes |
| "Don't say anything, just fly the approach quickly" | **Dangerous** | No |
| "Declare emergency, request straight-in vectors" | Acceptable | Yes |
| "Divert to a closer airport" | Acceptable | Yes |

**Coaching:** "With 30 minutes of fuel, declare MINIMUM FUEL immediately…"

### Event 11: Second Approach Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 60) |
| **ATC Says** | "Cleared ILS runway 7 left approach. Report established on the localizer." |
| **Keywords** | `cleared`, `ILS`, `7`, `left`, `report`, `established`, `localizer` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Cleared ILS 7 left, report established on the localizer" | Best | Yes |

### Phase: Approach → Landed

---

## Playwright Test Script

```
1. Navigate to homepage
2. Click "BEGIN FLIGHT" on "Checkride Hell into Jacksonville" (Checkride difficulty)
3. Skip cutscenes → advance to Departure
4. Event 1: Enter "Cleared takeoff 28 heading 050 climb maintain 4000 expect 8000"
5. Advance to Enroute
6. Event 2 (at 4000): Enter "Climb maintain 8000 Center 128.35"
7. [If icing advisory fires at HERMY]: Verify narration, no response
8. Event 4 (tick 15): Select "Turn on pitot heat, set known power setting, cross-check GPS groundspeed"
9. Event 5 (tick 20): Select "Transition to partial panel: airspeed, turn coordinator, altimeter. Use GPS track for heading reference."
10. Event 6 (at WLKRT): Enter "Hold southwest WLKRT 225 radial right turns EFC 2245 maintain 8000"
11. Event 7 (tick 35): Enter "Cleared ILS 7 left descend maintain 3000 tower 118.3 at JOTLY"
12. [If comm failure fires at tick 40]: Select "Squawk 7600, fly the approach as cleared, land"
13. Event 9 (tick 50): Enter "Going around heading 070 maintain 2000 approach 124.0"
14. [If low fuel fires at tick 55]: Select "Declare minimum fuel to ATC, request priority handling, brief the approach"
15. Event 11 (tick 60): Enter "Cleared ILS 7 left report established on the localizer"
16. Advance to Approach → Landed
17. Verify session ended
```

---

## Summary of Difficulty Scaling

| Event | Student (1) | Private (2) | IFR Prof (3) | Checkride (4) |
|-------|:-----------:|:-----------:|:------------:|:-------------:|
| Basic ATC comms | ✓ | ✓ | ✓ | ✓ |
| Frequency changes | ✓ | ✓ | ✓ | ✓ |
| Approach clearance | — | ✓ | ✓ | ✓ |
| Holding pattern | — | — | ✓ | ✓ (non-standard) |
| Missed approach | — | — | ✓ | ✓ |
| Environmental events | — | 50% | 60% | 70% |
| Decision point (abnormal) | — | — | 90%+ | 100% |
| Emergency (system failure) | — | — | 90% | 100% |
| Go-around | — | — | — | ✓ |
| Lost comms | — | — | — | 80% |
| Fuel emergency | — | — | — | 90% |
