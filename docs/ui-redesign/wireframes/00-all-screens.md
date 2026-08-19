# Wireframes — Low-Fidelity (textual)

Covers the 7 mandated screens. These are layout/content-hierarchy wireframes, not visual design. Companion to `00`–`11`.

---

## 1. Global shell + Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│ ☰ ClinicCare          ⌕ Global patient search    Dr. Aisha Rahman ▾  │  <- topbar
│   [Dashboard] [Patients] [Drug Checker]            [dentist] [Sign out]
├──────────────────────────────────────────────────────────────────────┤
│  Today's schedule (Mon 19 Aug)                        Quick actions   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ ⬤ 09:00  John Smith   — consult  (dental)      [Open]           │  │
│  │ ⬤ 10:30  Maria Garcia — recall    (dental)      [Open]           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  Recent patients                          [View all →#/patients]     │
│  ┌──────────┬──────────────┬───────────┬───────────────┐             │
│  │ Name     │ DOB          │ Last visit│ Status        │             │
│  ├──────────┼──────────────┼───────────┼───────────────┤             │
│  │ John Smith │ 1978-04-12 │ Aug 12    │ ⚠ allergy pen │             │
│  └──────────┴──────────────┴───────────┴───────────────┘             │
│  Alerts (actionable):  ⚠ 2 patients due for follow-up review         │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Patient list

```
┌──────────────────────────────────────────────────────────────────────┐
│ Patients                                   [ + New patient ] (P1)   │
│ ┌───────────────────────────────────────────────┐   ⌕ search "smith" │
│ Filter: [All] [Dental] [Ortho]                  │  [🔍]             │
│ ┌──────────┬──────────────┬───────────┬─────────┬──────────────┐    │
│ │ Name     │ DOB          │ Phone     │ Clinic  │ Warnings     │    │
│ ├──────────┼──────────────┼───────────┼─────────┼──────────────┤    │
│ │ Smith, John │ 1978-04-12 │ 555-0101  │ Demo    │ ⚠ penicillin│    │
│ │ Smith, Ana  │ 1985-11-02 │ 555-0143  │ Demo    │ —            │    │
│ └──────────┴──────────────┴───────────┴─────────┴──────────────┘    │
│ Keyboard: ↑/↓ select row · Enter open · rows focusable               │
│ [ Empty state: "No patients match your search." ]                    │
└──────────────────────────────────────────────────────────────────────┘
```

## 3. Patient overview

```
┌──────────────────────────────────────────────────────────────────────┐
│ ‹ Patients › Smith, John            M 42y  DOB 1978-04-12   #P-0001 │  <- patient context bar (persistent)
│  ⚠ ALLERGIC: penicillin (rash)      💊 warfarin · aspirin            │
├──────────────────────────────────────────────────────────────────────┤
│ Tabs: [ Overview | Dental | Skeleton | Medications | Appointments ]  │
│ ┌ Summary       ┌ Medications           ┌ Allergies / History        │
│ │ Last visit    │ warfarin 5mg — active │ Allergies: penicillin      │
│ │ Next appt     │ aspirin 81mg — active │ Conditions: hypertension   │
│ │ Recent events │                       │                            │
│ └───────────────┴───────────────────────┴────────────────────────────┘
│ Quick actions: [ Dental chart → ] [ Skeleton chart → ] [ Assistant → ]│
│ Recent events (timeline)                                             │
│  • 12 Aug   Tooth 16 — restoration (Dr. Rahman)                     │
│  • 02 Aug   Region: femur, right — fracture           [ See all ]    │
└──────────────────────────────────────────────────────────────────────┘
```

## 4. Dental workspace

```
┌──────────────────────────────────────────────────────────────────────┐
│ ‹ Patients › Smith, John                          [ Chart | List ▾ ] │
│ WD 18 17 · 16 15 14 13 12 11 | 21 22 23 24 25 26 · 27 28   [legend]  │
│   [ 18][17][16][15][14][13][12][11] [21][22][23][24][25][26][27][28] │
│   [ 48][47][46][45][44][43][42][41] [31][32][33][34][35][36][37][38] │
│  MD 48 47 · 46 45 44 43 42 41 | 31 32 33 34 35 36 · 37 38           │
│  Legend (shape+text, not color-only):                                │
│  ▭ healthy  ▩ caries  ▦ restored  ▨ missing  ▤ root canal           │
│  ▧ crown    ▨ implant ▨ fracture  ▨ treated                         │
├──────────────────────────────────────────────────────────────────────┤
│ ┌ DRAWER: Tooth 16 (FDI) — upper left, state: caries ───────────────┐│
│ │ Surface: mesial  Event: caries  Date: 2026-08-19                  ││
│ │ History:  12 Aug  restoration                                      ││
│ │ [ Add event: type ▾ surface ▾  date ░    ]  [Save] [Cancel]       ││
│ └────────────────────────────────────────────────────────────────────┘│
│ List alternative: Quadrant 1 › Tooth 16 › caries  (region list for SR)│
└──────────────────────────────────────────────────────────────────────┘
```

## 5. Orthopedic workspace

```
┌──────────────────────────────────────────────────────────────────────┐
│ ‹ Patients › Smith, John                          [ Chart | List ▾ ] │
│            ┌───────── Front / Back ─────────┐                        │
│            │  Skull/Cervical   ▨            │  Legend:               │
│            │  Shoulder L/R     ▭            │  ▭ normal  ▨ fracture  │
│            │  Humerus · Elbow  ▭            │  ▩ under_treatment     │
│            │  Radius/Ulna      ▩            │  ▦ follow_up · healing │
│            │  Pelvis · Femur   ▨            │  ▧ surgical/chronic    │
│            │  Tibia/Fibula     ▭            │  ⋯ (worst-state rises) │
│            └────────────────────────────────┘                        │
│ Region list: ► Right femur — fracture                                │
├──────────────────────────────────────────────────────────────────────┤
│ ┌ DRAWER: Right femur — state: fracture ────────────────────────────┐│
│ │ Bone: femur (right)  Finding: fracture  Date: 2026-08-02         ││
│ │ History: 02 Aug fracture (confirmed)                              ││
│ │ [ Add event: type ▾ bone ▾ date ░ ]        [Save] [Cancel]       ││
│ └────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

## 6. Medication interaction checker

```
┌──────────────────────────────────────────────────────────────────────┐
│ Drug interaction checker                     Patient: [Smith, John ▾]│
│ Add medication:  [warfarin ░] [Search]   Selected:                  │
│   ┌ warfarin ✕ ┐ ┌ aspirin ✕ ┐   (chips — labelled buttons)         │
│ [ Check interactions ]                                              │
│ ┌───────────────────────────────────────────────────────────────────┐│
│ │ ⚠ MAJOR — warfarin + aspirin                                     ││
│ │ Severity: Major     Clinical significance: .....                  ││
│ │ Mechanism: additive antiplatelet/anticoagulant effect             ││
│ │ Source: preseeded interaction dataset   Evidence: level X        ││
│ │ "This is not a clinical recommendation."                         ││
│ └───────────────────────────────────────────────────────────────────┘│
│ No-record state (verbatim): "No interaction record found in this    │
│ system. This does NOT prove that no interaction exists."            │
│ Unresolved drug state: "Could not resolve drug — try a different    │
│ formulation."                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## 7. Patient assistant

```
┌──────────────────────────────────────────────────────────────────────┐
│ ‹ Smith, John › Assistant                    Patient banner pinned   │
│ ╔═══════════════════════════════════════════════════════════════════╗│
│ ║ DECISION SUPPORT ONLY — not a substitute for clinical judgment.    ║│
│ ║ Based on the local patient record and, where noted, web sources.   ║│
│ ╚═══════════════════════════════════════════════════════════════════╝│
│ Starter questions:  [Summarize dental history] [Check meds w/ IBS]   │
│ ┌───────────────────────────────────────────────────────────────────┐│
│ │ Q: Does warfarin interact with aspirin?                          ││
│ │ A: The record shows both are active. Seeded interaction data       ││
│ │    flags a major interaction (see citations).                     ││
│ │ ── Citations ─────────────────────────────────────────           ││
│ │  [1] drug_interactions (preseeded)  [2] patient record meds      ││
│ │ ── Evidence excerpt ──────────────────────────────────           ││
│ │  warfarin + aspirin → major (source: ...)                        ││
│ │ ── Missing information ──────────────────────────────            ││
│ │  No recent INR results on record.                                ││
│ └───────────────────────────────────────────────────────────────────┘│
│ [ ✍ Ask ......................]  [Send]                              │
│ Degraded state: "Retrieval unavailable — showing record-based answer │
│ only."                                                              │
└──────────────────────────────────────────────────────────────────────┘
```