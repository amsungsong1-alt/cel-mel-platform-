# CEL Internal IPTT

Model sheet: CEL-only indicators not in the AIL/Agri-Impact framework (CI-1 to CI-10, plus the CI-8a sub-row). Added to the workbook 22 Oct 2026 (MEL In-house session resolutions); every row on this sheet is new as of that revision. Tracked by CEL now; submitted to AIL once AIL accepts them (question 11, still open as of this writing). Input sheet, same shape as BDS/WAN/Cross-cutting IPTT (CEL fills in Target/Achieved per quarter directly), not a rollup like Project IPTT — and it is **not** consolidated into Project IPTT at all: Project IPTT's lookup formulas never reference this sheet.

This file documents the sheet for the first time. The earlier docs-refresh pass (bringing docs/mel_tool/00-14 up to date with the Oct 2026 workbook revision) correctly left this sheet out as a wholesale-new-content addition, out of scope for a fact-correction-only pass — see 00_README.md's and 06_Project_IPTT.md's notes on it. This file was added alongside the app's CEL Internal IPTT integration (new `model_sheet='CEL Internal IPTT'` value, `database/seed_cel_internal_iptt.py`, a new Module M tab).

## Header lines

- A1: CEL Internal IPTT: CEL Indicators not in the AIL framework (CI-1 to CI-10)
- A2 (merged A2:T2): New sheet added 22 Oct 2026 (MEL session resolutions): all content on this sheet is new. Tracked by CEL now; submitted to AIL once AIL accepts them (question 11). Targets are set from the validated needs assessment (30 Oct 2026) unless a number is shown. Enter Targets and Achieved for Q1-Q4 only; Y1 and % are formulas.

No B2/B3 "Created on / Last revised on / Last revised by" lines, unlike the other model sheets — this sheet has no revision-date cells at all.

## Indicator definitions (11)

Columns, in sheet order: ID (A), Indicator (B), Definition and counting rule (C), Delivery model (ProFrame) (D), Unit (E), Y1 Target (F, formula), Y1 Achieved (G, formula), % Achieved (H, formula), Q1-Q4 Target (I, K, M, O), Q1-Q4 Achieved (J, L, N, P), Aggregation type (Q), Evidence (R), Responsible (S — a single column, not the model sheets' Collect/Verify/Review three-way split), Target status (T).

| ID | Indicator | Definition and counting rule | Delivery model (ProFrame) | Unit | Aggregation type | Evidence | Responsible | Target status |
|---|---|---|---|---|---|---|---|---|
| CI-1 | Enterprise diagnoses completed | Enterprises with a completed diagnosis record (business decision faced, buyers, costs, barriers, assets and income control). | 2: Accelerator and Enterprise Transition | Enterprises | Incremental | Diagnosis record | BDS Coach | Set from the validated needs assessment (30 Oct) |
| CI-2 | Enterprise growth plans agreed | Plans with priorities, baseline, actions, responsibilities and review dates, agreed with the woman or group. | 2: Accelerator and Enterprise Transition | Enterprises | Incremental | Signed growth plan | BDS Coach | Set from the validated needs assessment (30 Oct) |
| CI-3 | Coaching and mentoring received | Women (and, separately, enterprises) with an agreed plan who received at least 2 coaching sessions in the period. Each woman counted once. | 2: Accelerator and Enterprise Transition | Women; enterprises | Incremental | Coaching record | BDS Coach | Set from the coaching list (30 Oct) |
| CI-4 | Half-day workshops held | Events held; participants reported separately as unique women. Each ends with an action list and a named follow-up contact. | 3: Partner Half-day Workshops | Events; women | Incremental | Attendance list; action list | BDS Officer | Q2: 2 workshops (financial literacy; market access). Q3: digital skills; regulatory clinic |
| CI-5 | Partner trainers supported | Partner trainers or mentors who received ToT or co-facilitation support. Sessions co-facilitated reported separately. | 1 and 3 | Trainers | Incremental | ToT register | BDS Officer | Set after the trainer capacity assessment |
| CI-6 | Women applying new practice | Share of trained or coached women who report and show at least one new business practice (costing, records, pricing, buyer engagement) at follow-up. | 1 to 3 | % | Annual survey (not summed) | Follow-up call; records | BDS Coach; MEAL Officer | Set after the first follow-up |
| CI-7 | WAN market opportunities and orders | Verified buyer opportunities shared with WAN members; members or groups that received an order. Opportunities, orders and women reported separately. | 6: WAN Market Access, Linkages and Opportunities | Opportunities; groups | Incremental | Market opportunity log | GYSI Lead | Set at the 4 Dec WAN review |
| CI-8 | WAN mentors prepared and matched | Mentors who completed preparation and are matched to mentees. | 8: WAN Mentoring, Leadership and Exchange | Mentors | Incremental | Mentor register | GYSI Lead | Total set at the 4 Dec WAN review |
| CI-8a | ...of which young women with disabilities (mentors) | Young women with disabilities serving as mentors (planner I.13: 1/2/2/3 = 8). Also reported on OP22. | 8: WAN Mentoring, Leadership and Exchange | Mentors | Incremental | Mentor register | GYSI Lead | Planner I.13 |
| CI-9 | Feedback answered on time | Share of feedback items and WAN issues with a response by the agreed date. No case details. | 5 to 9 | % | Annual survey (not summed) | Feedback log | GYSI Lead; MEAL Officer | Set after the first quarter of logging |
| CI-10 | WAN forum and peer-circle attendances (supporting count) | Total attendance lines at WAN forums and peer circles in the period. A woman attending three forums is 3 attendances and 1 woman. Supports OP16 (unique women engaged, planner I.11) and the concept note's "forum engagements". | 5: WAN Governance Structure, Membership, Charter and Affiliation; 8: WAN Mentoring, Leadership and Exchange | Attendances | Incremental | Attendance register | GYSI Lead | WAN note: 300 (Q3), 200 (Q4) |

**Transcription note on CI-10's raw Unit cell (E15):** the live workbook cell literally contains `"Attendances / Attendance register / GYSI Lead"` — Unit, Evidence and Responsible concatenated into one cell, a data-entry error on the source sheet itself. R15 and S15 separately hold the correct Evidence ("Attendance register") and Responsible ("GYSI Lead") values, confirming the error is isolated to E15. This table above, and the app's seed data (`database/seed_cel_internal_iptt.py`), use the clean, split values; this note exists so the discrepancy from the raw cell is traceable.

No Fish Type column exists on this sheet at all (structurally absent, unlike the other model sheets — not just blank per row).

No Level (Impact/Outcomes/Outputs) column exists either. The app's `mel_indicators.level` is NOT NULL, so a value had to be assigned when seeding these into the database: CI-1 to CI-5, CI-7, CI-8, CI-8a, CI-9 and CI-10 (process/delivery counts) were assigned 'Outputs'; CI-6 ("Women applying new practice", a behaviour-change/practice-adoption metric at follow-up) was assigned 'Outcomes'. This is an editorial judgement call, not stated anywhere on the sheet — flagged for a human (Muhammadu) to confirm or correct.

## Relationship to the 55 AIL-framework (IM/OC/OP) indicators

Checked systematically against all 55 indicators, not just the two the sheet itself flags:

- **CI-8a relates to OP22** (explicit in C13: "Also reported on OP22"). Both track the same 8 PWD mentors (planner I.13: 1/2/2/3), but their quarterly phasing has already diverged: CI-8a keeps the original 1/2/2/3 split; OP22's Q1 was folded into Q2 in the 22 Oct 2026 revision (now blank/3/2/3). Seeded independently, not reconciled — see `database/schema.sql`'s comment on `mel_indicators.related_indicator_id` and `pages/13_M_IPTT.py`'s read-only cross-reference display in the CEL Internal IPTT tab.
- **CI-10 relates to OP16** (explicit in C15: "Supports OP16 (unique women engaged, planner I.11)"). CI-10 counts attendance *lines* (a woman at three forums is 3); OP16 counts unique women. Related, not a duplicate.
- CI-1, CI-2, CI-3, CI-4, CI-5, CI-6, CI-7, CI-8 and CI-9: no AIL-framework counterpart found.

Neither relationship is auto-synced anywhere in the app: both rows in each pair are filled in independently by their own responsible roles, and the display is informational only.

## Targets and achievements (cached values)

Blank = not due / not reported (not zero). `-` = percentage not computable. Y1 = Jul 2026 to Jun 2027; Q1 Jul-Sep 2026, Q2 Oct-Dec 2026, Q3 Jan-Mar 2027, Q4 Apr-Jun 2027. Every row's Y1 Achieved is currently blank (no achievements reported yet, same as every other model sheet in this revision).

Only CI-8a has an approved quarterly target. The other 10 indicators' targets are still pending the 30 Oct 2026 validated needs assessment / 4 Dec 2026 WAN review (see the Target status column above) — not seeded as placeholder rows in the app (see `database/seed_cel_internal_iptt.py`'s module docstring for why).

| ID | Y1 Target | Y1 Achieved | Y1 % | Q1 Target | Q1 Achieved | Q1 % | Q2 Target | Q2 Achieved | Q2 % | Q3 Target | Q3 Achieved | Q3 % | Q4 Target | Q4 Achieved | Q4 % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CI-1 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-2 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-3 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-4 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-5 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-6 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-7 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-8 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-8a | 8 |  | - | 1 |  | - | 2 |  | - | 2 |  | - | 3 |  | - |
| CI-9 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |
| CI-10 |  |  | - |  |  | - |  |  | - |  |  | - |  |  | - |

## Formulas (active; complete inventory)

33 formulas (3 per row — Y1 Target, Y1 Achieved, % Achieved — across the 11 rows). Formulas are shown exactly as stored in the workbook. `{r}` stands for the formula's own row number. Cached values appear in the content table above.

**Column F** (Y1 Target), rows 5-15 (11 cells):

```
=IF(COUNT(I{r},K{r},M{r},O{r})=0,"",SUM(I{r},K{r},M{r},O{r}))
```

Only F13 (CI-8a) has a non-blank cached value: `=> 8`.

**Column G** (Y1 Achieved), rows 5-15 (11 cells):

```
=IF(COUNT(J{r},L{r},N{r},P{r})=0,"",SUM(J{r},L{r},N{r},P{r}))
```

All 11 cells cache blank (no achievements reported yet).

**Column H** (% Achieved), rows 5-15 (11 cells):

```
=IF(G{r}="","-",IFERROR(G{r}/F{r},"-"))
```

All 11 cells cache `-`.

Total: 33 formulas in 3 distinct patterns.

## Data validation

- type `decimal`, rule `0` (greaterThanOrEqual), applies to `I5:P15`
- type `list`, rule `"Incremental,Cumulative,Annual survey (not summed)"` (between), applies to `Q5:Q15`

## Conditional formatting rules

None on this sheet (unlike BDS/WAN/Cross-cutting IPTT, which colour the % columns red/amber/green — this sheet has no achievements yet to colour, and no RAG rule was added).

## Cell comments

None on this sheet.

## Merged cells

- A2:T2 (the sheet-wide intro note, see Header lines above)
