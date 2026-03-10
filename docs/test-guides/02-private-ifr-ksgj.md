# Test Guide: IFR Cross-Country to St. Augustine

**Difficulty:** 2 — Private Pilot
**Route:** KGNV → OCALA → PALAT → KSGJ
**Altitude:** 5,000 MSL
**Conditions:** 3,000 broken, visibility 5 in haze

---

## How to Use This Guide

1. Start the scenario and select **Private** difficulty
2. Follow the flight phases below
3. Difficulty 2 pool events have a 50% chance of firing (weight 0.5)
4. Higher pool events won't fire at Private difficulty

---

## Flight Flow

### Phase: Preflight → Taxi → Departure

### Event 1: Takeoff Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Phase change to departure |
| **ATC Says** | "November 4 Uniform Tango, runway 28, cleared for takeoff. Fly heading 090, climb and maintain 3,000." |
| **Keywords** | `cleared`, `takeoff`, `28`, `heading`, `090`, `3000` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Cleared takeoff runway 28, heading 090, climb maintain 3,000" | Best | Yes | No |
| "Cleared takeoff 28, 090, 3000" | Best | Yes | No |
| "Cleared 28" | Acceptable | Yes | No |
| "Wilco" | Poor | No | Yes |

### Event 2: Climb to 5,000

| Field | Value |
|-------|-------|
| **Trigger** | Altitude crossing 3,000 ft |
| **ATC Says** | "November 4 Uniform Tango, climb and maintain 5,000." |
| **Keywords** | `climb`, `maintain`, `5000` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Climb and maintain 5,000, November 4 Uniform Tango" | Best | Yes | No |
| "Up to 5000" | Poor | No | Yes |

### Event 3: Frequency Change to Jacksonville Center

| Field | Value |
|-------|-------|
| **Trigger** | Altitude crossing 5,000 ft |
| **ATC Says** | "November 4 Uniform Tango, contact Jacksonville Center on 134.75." |
| **Keywords** | `134.75`, `Jacksonville`, `Center` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Contact Jacksonville Center 134.75, November 4 Uniform Tango" | Best | Yes | No |
| "134.75, good day" | Acceptable | Yes | No |
| "Switching" | Poor | No | Yes |

### Event 4 (Pool, 50% chance): Amended Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint OCALA |
| **ATC Says** | "Amendment to your route. After OCALA, proceed direct PALAT. Rest of route unchanged." |
| **Keywords** | `direct`, `PALAT`, `route`, `unchanged` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Direct PALAT, rest of route unchanged" | Best | Yes | No |
| "Roger direct PALAT" | Acceptable | Yes | No |

### Event 5: Descent for Approach

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint PALAT |
| **ATC Says** | "November 4 Uniform Tango, descend and maintain 2,000. Expect RNAV runway 31 approach at St. Augustine." |
| **Keywords** | `descend`, `maintain`, `2000`, `RNAV`, `31` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Descend maintain 2,000, expect RNAV 31, November 4 Uniform Tango" | Best | Yes | No |
| "Down to 2000" | Poor | No | Yes |

### Event 6: Approach Clearance

| Field | Value |
|-------|-------|
| **Trigger** | Waypoint KSGJ |
| **ATC Says** | "November 4 Uniform Tango, cleared RNAV runway 31 approach. Contact tower on 118.35 at CLUSH." |
| **Keywords** | `cleared`, `RNAV`, `31`, `118.35` |

| Test Response | Expected Quality | Correct? | Coaching? |
|---------------|-----------------|----------|-----------|
| "Cleared RNAV 31, tower 118.35 at CLUSH" | Best | Yes | No |
| "Cleared approach" | Acceptable | Yes | No |
| "Roger" | Poor | No | Yes |

### Phase: Approach → Landed

---

## Playwright Test Script

```
1. Navigate to homepage
2. Click "BEGIN FLIGHT" on "IFR Cross-Country to St. Augustine" (Private difficulty)
3. Skip cutscenes → advance to Departure
4. Event 1: Enter "Cleared takeoff 28 heading 090 climb maintain 3000"
5. Verify: correct=true, quality=best
6. Advance to Enroute
7. Event 2 (at 3000): Enter "Climb maintain 5000"
8. Event 3 (at 5000): Enter "Jacksonville Center 134.75"
9. [If Event 4 fires at OCALA]: Enter "Direct PALAT route unchanged"
10. Event 5 (at PALAT): Enter "Descend maintain 2000 expect RNAV 31"
11. Event 6 (at KSGJ): Enter "Cleared RNAV 31 tower 118.35"
12. Advance to Approach → Landed
13. Verify session ended
```
