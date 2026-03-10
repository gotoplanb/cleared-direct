# Test Guide: Day VFR to Ocala

**Difficulty:** 1 — Student Pilot
**Route:** KGNV → WALDO → KOCF
**Altitude:** 3,500 MSL
**Conditions:** Clear skies, visibility 10+, winds calm

---

## How to Use This Guide

1. Start the scenario and select **Student** difficulty
2. Follow the flight phases below
3. At each ATC event, enter the response in the comms drawer
4. Check the **Expected Quality** column to verify the game scored correctly
5. Coaching text should appear only on poor/incorrect responses

---

## Flight Flow

### Phase: Preflight → Taxi → Departure

Click through preflight and taxi cutscenes, then advance to departure.

### Event 1: Takeoff Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Phase change to departure |
| **ATC Says** | "November 4 Uniform Tango, runway 28, cleared for takeoff." |
| **Keywords** | `cleared`, `takeoff`, `runway`, `28` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Cleared for takeoff runway 28, November 4 Uniform Tango" | Best | Yes | No |
| "Cleared takeoff 28" | Best | Yes | No |
| "Roger, rolling" | Poor | No | Yes — "Read back the runway and clearance…" |

### Event 2: Radar Contact + Altimeter

| Field | Value |
|-------|-------|
| **Trigger** | Altitude crossing 3,500 ft |
| **ATC Says** | "November 4 Uniform Tango, radar contact. Ocala altimeter 30.12." |
| **Keywords** | `30.12` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "30.12, November 4 Uniform Tango" | Best | Yes | No |
| "Roger" | Poor | No | Yes — "read it back so they know you've set it correctly" |

### Event 3: Position Report (Difficulty Pool — always fires at Student level)

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint WALDO |
| **ATC Says** | "November 4 Uniform Tango, say altitude." |
| **Keywords** | `3500` or `three thousand five hundred` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "3,500, November 4 Uniform Tango" | Best | Yes | No |
| "Level at three thousand five hundred" | Best | Yes | No |
| "Um, I'm up here" | Poor | No | Yes — "respond with your current altitude" |

### Event 4: Frequency Change / Traffic

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint KOCF |
| **ATC Says** | "November 4 Uniform Tango, Ocala traffic 12 o'clock, 5 miles. Change to advisory frequency approved. Good day." |
| **Keywords** | `traffic`, `advisory`, `frequency` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Traffic in sight, switching to advisory frequency, good day" | Best | Yes | No |
| "Looking for traffic, advisory frequency, thanks" | Best | Yes | No |
| "Roger" | Poor | No | Yes — "Acknowledge traffic calls and frequency changes" |

### Phase: Approach → Landed

Advance through approach and landing cutscenes to complete the flight.

---

## Playwright Test Script

```
1. Navigate to homepage
2. Click "BEGIN FLIGHT" on "Day VFR to Ocala" card (select Student difficulty)
3. Skip preflight cutscene → advance to Taxi → advance to Departure
4. Wait for Event 1 (takeoff clearance) — enter "Cleared for takeoff runway 28"
5. Verify: correct=true, quality=best
6. Advance to Enroute, skip cutscene
7. Wait for Event 2 (altimeter at 3500) — enter "30.12"
8. Verify: correct=true
9. Wait for Event 3 (position report at WALDO) — enter "3500"
10. Verify: correct=true
11. Wait for Event 4 (frequency change at KOCF) — enter "Traffic in sight, advisory frequency"
12. Verify: correct=true
13. Advance to Approach → Landed
14. Verify session ended
```
