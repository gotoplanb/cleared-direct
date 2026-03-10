# Test Guide: IFR with Hold at Orlando

**Difficulty:** 3 — Instrument Proficiency
**Route:** KGNV → OCALA → DLAND → KORL
**Altitude:** 6,000 MSL
**Conditions:** 2,500 broken at departure, 1,200 overcast at destination

---

## How to Use This Guide

1. Start the scenario and select **IFR Prof** difficulty
2. This scenario includes a holding pattern, missed approach, and diversion decision
3. Difficulty pools 2 and 3 are active — pool events fire based on weight
4. Pool 2 (turbulence, weight 0.6) is environmental — no response required
5. Pool 3 (diversion decision, weight 1.0) always fires and requires a decision

---

## Flight Flow

### Phase: Preflight → Taxi → Departure

### Event 1: Takeoff Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Phase change to departure |
| **ATC Says** | "November 4 Uniform Tango, runway 28, cleared for takeoff. Fly heading 100, climb and maintain 4,000." |
| **Keywords** | `cleared`, `takeoff`, `28`, `heading`, `100`, `4000` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Cleared takeoff 28 heading 100 climb maintain 4000" | Best | Yes |
| "28 cleared" | Poor | No |

### Event 2: Climb + Frequency Change

| Field | Value |
|-------|-------|
| **Trigger** | Altitude crossing 4,000 ft |
| **ATC Says** | "Climb and maintain 6,000. Contact Jacksonville Center on 132.05." |
| **Keywords** | `climb`, `maintain`, `6000`, `132.05` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Climb maintain 6000, Center 132.05" | Best | Yes |
| "Up to 6" | Poor | No |

### Event 3 (Pool, 60% chance): Turbulence

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint OCALA |
| **Type** | Environmental change — no response needed |
| **Narration** | "Moderate turbulence encountered…" |

This event is informational. Verify it displays in the narration area but doesn't require a response.

### Event 4: Holding Instructions

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint DLAND |
| **ATC Says** | "Hold as published at DLAND. Expect further clearance at 1845. Maintain 6,000." |
| **Keywords** | `hold`, `DLAND`, `1845`, `6000` |

**This is the key training event.** Holding readbacks must include all elements.

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Hold as published DLAND, expect further clearance 1845, maintain 6000" | Best | Yes |
| "Hold DLAND 1845 6000" | Best | Yes |
| "Holding" | Poor | No |

### Event 5: Approach Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 30) |
| **ATC Says** | "Cleared ILS runway 7 approach. Descend and maintain 2,000. Contact Orlando tower on 118.7 at HARIS." |
| **Keywords** | `cleared`, `ILS`, `7`, `2000`, `118.7` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Cleared ILS 7, descend maintain 2000, tower 118.7 at HARIS" | Best | Yes |
| "Cleared approach" | Acceptable | Yes |

### Event 6: Missed Approach

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 45) |
| **ATC Says** | "Execute missed approach. Climb heading 070, climb and maintain 3,000. Contact approach on 124.8." |
| **Keywords** | `missed`, `approach`, `heading`, `070`, `3000`, `124.8` |

| Test Response | Expected Quality | Correct? |
|---------------|-----------------|----------|
| "Missed approach, heading 070, climb 3000, approach 124.8" | Best | Yes |
| "Going around" | Poor | No |

### Event 7 (Pool, always fires): Diversion Decision

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 50) |
| **ATC Says** | "Orlando weather now below minimums — 200 overcast, visibility half mile fog. Sanford VFR. Say intentions." |
| **Type** | Multiple choice decision |

| Option | Quality | Correct? |
|--------|---------|----------|
| "Divert to Sanford, request vectors to KSFB" | **Best** | Yes |
| "Request another ILS attempt at Orlando" | Poor | No |
| "Declare minimum fuel and request priority to nearest VFR" | Acceptable | Yes |
| "Continue to Orlando, the weather might improve" | **Dangerous** | No |

**Coaching if wrong:** "Never attempt an approach when the field is reported below minimums…"

### Event 8 (Pool, 90% chance): Door Seal Failure

| Field | Value |
|-------|-------|
| **Trigger** | Time-based (tick 25) |
| **Type** | Multiple choice decision |

| Option | Quality | Correct? |
|--------|---------|----------|
| "Slow down, secure the door, continue to destination" | **Best** | Yes |
| "Declare emergency and request immediate return" | Acceptable | Yes |
| "Ignore it, the door won't open in flight" | Poor | No |
| "Open the door fully to equalize pressure" | **Dangerous** | No |

---

## Playwright Test Script

```
1. Navigate to homepage
2. Click "BEGIN FLIGHT" on "IFR with Hold at Orlando" (IFR Prof difficulty)
3. Skip cutscenes → advance to Departure
4. Event 1: Enter "Cleared takeoff 28 heading 100 climb maintain 4000"
5. Advance to Enroute
6. Event 2 (at 4000): Enter "Climb maintain 6000 Center 132.05"
7. [If turbulence event fires at OCALA]: Verify narration displays, no response needed
8. Event 4 (at DLAND): Enter "Hold DLAND expect further clearance 1845 maintain 6000"
9. [If door seal event fires at tick 25]: Select "Slow down, secure the door, continue to destination"
10. Event 5 (tick 30): Enter "Cleared ILS 7 descend maintain 2000 tower 118.7"
11. Event 6 (tick 45): Enter "Missed approach heading 070 climb 3000 approach 124.8"
12. Event 7 (tick 50): Select "Divert to Sanford, request vectors to KSFB"
13. Verify: quality=best
14. Advance to Landed
```
