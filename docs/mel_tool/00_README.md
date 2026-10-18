# CEL SAWA MEL Tool (v3, 18 Oct 2026): Markdown export

Source workbook: `SAWA_IP_MEL_System_Tool_CEL_v3_10_18_2026.xlsx`. Purpose: give Claude Code (VS Code) a complete text version of every sheet, including every formula and rule, so it can help refine the CEL MEL Platform (Streamlit). Values are the cached results of the active formulas; formulas are listed verbatim under *Formulas* in each file. Colours and widths are not kept, except the CEL-scope legend (from font colour) and the Gantt rules (as conditional-formatting formulas).

## Formula status of the workbook

- **1192 active formulas** across 10 sheets, **0 external-workbook references**, 0 formula errors after recalculation.
- Project IPTT used to point at another workbook (`[1]`); in this version it reads the BDS, WAN and Cross-cutting IPTT sheets inside the workbook.
- Formula counts by sheet: Project IPTT: 825, BDS IPTT: 148, WAN IPTT: 64, Cross-cutting IPTT: 85, MEL Plan: 5, A3 Results Framework (ToC): 37, A2 Data Flow & Roles: 4, A4 Onboarding Q2: 2, A5 Training Q2: 11, CEL IPTT Guide: 11.

## Files

| File | Sheet | What it holds |
|---|---|---|
| 01_Cover.md | Cover | Workbook map (owner, audience, update frequency, share with AIL), assignments tracker, submission pack, colour key |
| 02_ProFrame.md | ProFrame | Partners, 10 delivery models, key impact measures, goal/objectives/assumptions, results framework with indicators, assumptions and risks |
| 03_A3_Results_Framework_ToC.md | A3 Results Framework (ToC) | Assignment 3: theory of change, five results pathways, if-then logic; live links to ProFrame |
| 04_MEL_Plan.md | MEL Plan | Indicators, LoP targets, methods, frequency, sources, responsible roles, questions for Agri-Impact |
| 05_A2_Data_Flow_and_Roles.md | A2 Data Flow & Roles | Assignment 2: 7-stage data flow, key persons and roles, ownership per sheet, data use, data standards |
| 06_Project_IPTT.md | Project IPTT | Consolidated IPTT: 55 indicators, Y1 and Q1-Q4 targets and achievements, consolidation formulas |
| 07_BDS_IPTT.md | BDS IPTT | Input sheet: 21 BDS indicators |
| 08_WAN_IPTT.md | WAN IPTT | Input sheet: 9 WAN indicators |
| 09_Cross-cutting_IPTT.md | Cross-cutting IPTT | Input sheet: 12 inclusion, safeguarding and coverage indicators |
| 10_A4_Onboarding_Q2.md | A4 Onboarding Q2 | Assignment 4: Q2 onboarding schedule with live Q2 targets and Gantt rules |
| 11_A5_Training_Q2.md | A5 Training Q2 | Assignment 5: Q2 training schedule with live Q2 targets, cohort formula and Gantt rules |
| 12_PIRS.md | PIRS | 62 indicator reference sheets |
| 13_Shared_Measures_2.0.md | Shared Measures 2.0 | 46 AIL shared-measure definitions |
| 14_CEL_IPTT_Guide.md | CEL IPTT Guide | Workflow, roles, counting rules, field guide, worked example |

## How the workbook fits together

- **Sheet order and groups:** Cover; strategy and framework (ProFrame, A3, MEL Plan); data system and reporting (A2, Project IPTT, BDS/WAN/Cross-cutting IPTT); Q2 operations (A4, A5); reference (PIRS, Shared Measures 2.0, Guide).
- **Flow:** typed inputs live only in the three model IPTT sheets (targets and verified achievements per quarter). Project IPTT consolidates them by formula. A4 and A5 read Q2 targets from the model sheets. A3 reads text from ProFrame.
- **Reporting period:** Y1 = Jul 2026 to Jun 2027. Q1 Jul-Sep 2026, Q2 Oct-Dec 2026, Q3 Jan-Mar 2027, Q4 Apr-Jun 2027.
- **Indicator IDs:** IM1-IM4 (impact), OC1-OC15 (outcome), OP1-OP36 (output) in the IPTT sheets. The ProFrame has its own # numbering and the PIRS has no ID, so these are currently linked by wording only; a stable key is needed in the platform.
- **One indicator, one sheet:** each ID is typed in exactly one model sheet. The model sheets are the single source for every number.

## The formulas the platform must reproduce

1. **Y1 total (E, F):** `IF(COUNT(Q1..Q4)=0,"",SUM(Q1..Q4))` for targets and for achievements. Blank quarters are ignored, never treated as 0.
2. **Percentage (G, J, M, P, S):** `IF(achieved="","-",IFERROR(achieved/target,"-"))`.
3. **Consolidation (Project IPTT H, I, K, L, N, O, Q, R):** for the indicator ID in column A, count non-blank entries for that ID in the three model sheets (rows 9 to 80); return blank if none, otherwise the sum of the matches (`COUNTIFS` + `SUMIFS`). Fish type (D) is looked up with `INDEX/MATCH` the same way.
4. **Reported-in check:** an ID must appear in exactly one model sheet; otherwise flag `NOT ASSIGNED` or `CHECK: in more than one sheet`.
5. **Sheet summary lines:** counts of indicators, with a Y1 target, with an achievement, and at or above 100%.
6. **A4/A5:** Q2 target = `SUMIFS(<model sheet>!K, <model sheet>!A, "<ID>")`; participants per cohort = `ROUNDUP(target / planned cohorts)` when both are numbers; Gantt bar for a week = week start <= End and week start + 6 >= Start, coloured by Status (Done green, Delayed red, otherwise blue); the current week is highlighted.
7. **A3:** goal, key result statements, assumptions and risks are direct links to ProFrame cells.
8. **Percentage colour rules:** red below 70%, amber 70-99%, green 100% or more.

## Business rules

- Blank = not due or not reported; 0 = measured and none achieved. Aggregation types: Incremental, Cumulative, Annual survey (not summed). Fish type list: Catfish, Tilapia, Catfish and Tilapia, Not applicable. Achieved values must be numbers >= 0.
- BDS, WAN and work results are not added together as unique programme reach. Participants need a unique ID (Ghana Card or alternative); each person is counted once per indicator.
- CEL scope comes from font colour in ProFrame, MEL Plan and Project IPTT. Starter packs and micro-grants are not CEL scope. Gender focal persons trained are WEO (planner I.9). Mobilisation is onboarding, not WEO.
- Roles: MEAL Lead, MEAL Officer, BDS Coach, BDS Officer, GYSI Lead (leads WAN), Communication Lead, Finance Lead, Project Team, Program Lead, CEL Admin, Partner's. Each model-sheet row has Collect / Verify / Review roles. Workflow: Draft, Submitted, Verified, Approved.
- Data quality: completeness check, then phone verification (80% agreement or more accepted; below 80% goes back for rework).

## Suggested entities for the platform

`Indicator` (id, text, level, unit, fish type, aggregation type, owner sheet, scope, key measure, markers, disaggregations, MoV, PIRS definition) | `Target` (indicator, quarter, value, phasing confirmed flag) | `Achievement` (indicator, quarter, value, verified by, evidence) | `DeliveryModel` (slot, name, owner sheet) | `ResultsArea` (id, statement, assumptions, risks) | `ActivitySchedule` (A4/A5: activity, lead, support, location, start, end, status, linked indicator) | `Participant` (unique ID, sex, disability status, youth category, location, consent) | `Group/Cooperative` (register with status flags) | `Role/User` (role, name, backup, reports-to).

## Items to settle before building (found in this version)
- Indicators in plain (not-in-CEL-scope) font in Project IPTT (13): IM4, OP1, OP2, OP3, OP6, OP7, OP8, OP12, OP13, OP14, OP19, OP20, OP21.
- ProFrame # numbers that repeat across results areas: 9, 10, 30, 31, 32, 37, 43, 44, 45, 46, 47. Use the IPTT ID or a new stable key.
- The MEL Plan LoP targets and the IPTT Y1 targets use different bases for some indicators (for example YiW). Confirm the Y1 x 4 rule and the tracking level (CEL vs programme).
- Dates in A4 and A5 and some quarterly phasings are proposals (yellow cells); owners' names and backups in A2 are blank.
- A4/A5 conditional-formatting bars and the 'current week' highlight use `TODAY()`; replicate as a computed field in the app.
- Typos from the source template remain in approved indicator wording (for example "tranistioned", "dignifed", "enterprisesshowing", "Resilence").
