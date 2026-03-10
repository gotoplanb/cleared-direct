# Audio Recording Guide

All strings live in `fixtures/strings/en.yaml`. This doc lists what needs to be recorded and how.

## File Naming Convention

```
static/audio/en/atc/cleared_takeoff_simple.mp3
static/audio/en/narration/vacuum_failure.mp3
```

Key maps to path: `atc.cleared_takeoff_simple` → `audio/en/atc/cleared_takeoff_simple.mp3`

---

## ATC Transmissions (17 clips)

Record in a firm, professional ATC cadence. Emphasize numbers clearly. Read {variables} as their most common value from the scenarios.

| # | Key | Script | Notes |
|---|-----|--------|-------|
| 1 | `atc.cleared_takeoff_simple` | "November 4 Uniform Tango, runway 28, cleared for takeoff." | VFR only |
| 2 | `atc.cleared_takeoff_hdg_alt` | "November 4 Uniform Tango, runway 28, cleared for takeoff. Fly heading 280, climb and maintain 3,000." | Record multiple: hdg 090/100/050/280, alt 3000/4000 |
| 3 | `atc.cleared_takeoff_hdg_alt_expect` | "November 4 Uniform Tango, runway 28, cleared for takeoff. Fly heading 050, climb and maintain 4,000. Expect 8,000 ten minutes after departure." | Checkride scenario |
| 4 | `atc.climb_maintain` | "November 4 Uniform Tango, climb and maintain 5,000." | Record at 5000, 6000, 8000 |
| 5 | `atc.climb_maintain_contact` | "November 4 Uniform Tango, climb and maintain 6,000. Contact Jacksonville Center on 132.05." | Altitude + freq combo |
| 6 | `atc.descend_maintain` | "November 4 Uniform Tango, descend and maintain 3,000, expect ILS 28 approach." | Record at 2000/3000 |
| 7 | `atc.descend_maintain_approach` | "November 4 Uniform Tango, descend and maintain 2,000. Expect RNAV runway 31 approach at St. Augustine." | Includes destination name |
| 8 | `atc.maintain_altitude_expect` | "November 4 Uniform Tango, maintain 6,000. Expect ILS runway 28 approach at KOJM." | Level-off |
| 9 | `atc.contact_departure` | "November 4 Uniform Tango, contact departure on 124.55." | Record at 124.55 |
| 10 | `atc.contact_center` | "November 4 Uniform Tango, contact Jacksonville Center on 134.75." | Record at 128.35/132.05/134.75 |
| 11 | `atc.frequency_change_approved` | "November 4 Uniform Tango, Ocala traffic 12 o'clock, 5 miles. Change to advisory frequency approved. Good day." | VFR termination |
| 12 | `atc.radar_contact` | "November 4 Uniform Tango, radar contact. Ocala altimeter 30.12." | |
| 13 | `atc.say_altitude` | "November 4 Uniform Tango, say altitude." | Short and direct |
| 14 | `atc.hold_as_published` | "November 4 Uniform Tango, hold as published at DLAND. Expect further clearance at 1845. Maintain 6,000." | Standard hold |
| 15 | `atc.hold_nonstandard` | "November 4 Uniform Tango, hold southwest of WLKRT on the 225 radial, right turns. Expect further clearance at 2245. Maintain 8,000." | Non-standard — emphasize "right turns" |
| 16 | `atc.cleared_approach` | "November 4 Uniform Tango, cleared ILS runway 7 approach. Descend and maintain 2,000. Contact Orlando tower on 118.7 at HARIS." | Full approach clearance |
| 17 | `atc.cleared_approach_report` | "November 4 Uniform Tango, cleared ILS runway 7 left approach. Report established on the localizer." | With reporting req |
| 18 | `atc.route_amendment` | "November 4 Uniform Tango, amendment to your route. After OCALA, proceed direct PALAT. Rest of route unchanged." | |
| 19 | `atc.execute_missed` | "November 4 Uniform Tango, execute missed approach. Climb heading 070, climb and maintain 3,000. Contact approach on 124.8." | |
| 20 | `atc.go_around` | "November 4 Uniform Tango, go around! Traffic on the runway. Climb heading 070, maintain 2,000. Contact approach on 124.0." | Urgent — emphasize "go around!" |
| 21 | `atc.weather_below_minimums` | "November 4 Uniform Tango, Orlando weather now below minimums — 200 overcast, visibility half mile fog. Sanford VFR. Say intentions." | Weather diversion prompt |

---

## Narration Clips (12 clips)

Record in a calm, narrator voice — like a flight instructor observing the situation.

| # | Key | Script | Notes |
|---|-----|--------|-------|
| 1 | `narration.ceiling_drop` | "ATIS update — KOJM now reporting 500 overcast, visibility 2 in mist. Minimums just got tighter." | |
| 2 | `narration.visibility_drop` | "ATIS update — KSGJ now reporting 1,500 broken, visibility 2 in rain. Winds 200 at 18 gusting 25." | |
| 3 | `narration.turbulence` | "Moderate turbulence encountered. The ride gets bumpy as you cross a frontal boundary." | No variables |
| 4 | `narration.icing_advisory` | "PIREP from a regional jet — moderate rime icing reported between 6,000 and 10,000 in your area." | |
| 5 | `narration.pitot_ice_fluctuation` | "You notice a slight fluctuation in your airspeed indicator. Temperature is near freezing at this altitude." | Subtle warning |
| 6 | `narration.pitot_ice_erratic` | "Your airspeed indicator drops to zero, then jumps erratically. OAT shows minus 2 Celsius. You're in visible moisture." | Urgent |
| 7 | `narration.alternator_failure` | "The low-voltage annunciator illuminates. You notice the ammeter showing a discharge." | |
| 8 | `narration.door_seal_failure` | "A loud rushing sound fills the cockpit. The cabin door seal has partially failed. Noise is extreme and you feel a draft." | Record with urgency |
| 9 | `narration.comm_failure` | "You hear only static on the radio. You try transmitting but get no response. You've been cleared for the approach." | |
| 10 | `narration.vacuum_failure` | "Your attitude indicator starts to tumble. The vacuum annunciator illuminates. You're in solid IMC." | |
| 11 | `narration.vacuum_failure_night` | "Your attitude indicator tumbles. The heading indicator starts precessing rapidly. Vacuum annunciator illuminates. You're in solid IMC at night." | Night version — higher stress |
| 12 | `narration.low_fuel_warning` | "After the go-around, you check fuel. Left tank shows 5 gallons, right tank shows 3 gallons. At current consumption, you have approximately 30 minutes of fuel remaining." | Deliver calmly but with gravity |

---

## Recording Tips

1. **ATC voice**: Slightly nasal, clipped, professional. No dramatic pauses. Numbers are spoken clearly: "one two four point five five" not "a hundred twenty-four fifty-five"
2. **Narrator voice**: Warm, conversational instructor tone. Like a CFI sitting right seat
3. **Format**: MP3, 128kbps mono, 44.1kHz. Normalize to -3dB
4. **Silence**: 0.3s lead-in, 0.5s tail silence
5. **Variable recordings**: Where noted, record multiple versions with different numbers. The engine will select the right file based on the variable values

## Total Clips to Record

| Category | Count |
|----------|-------|
| ATC transmissions | 21 |
| Narrations | 12 |
| **Total** | **33** |

Coaching text (28 strings) is display-only — no audio needed.

---

## Multi-Language Support

To add a new language (e.g., Spanish):

1. Copy `fixtures/strings/en.yaml` → `fixtures/strings/es.yaml`
2. Translate all `text:` values
3. Record audio into `static/audio/es/atc/` and `static/audio/es/narration/`
4. Add language selector to the session UI
5. The engine reads the string key and resolves to the correct language file
