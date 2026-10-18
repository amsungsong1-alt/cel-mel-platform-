# CEL SAWA MEL Tool: Markdown export

Source workbook: `SAWA_IP_MEL_System_Tool_CEL_v1 (1).xlsx` (converted 18 Oct 2026). Purpose: give Claude Code (VS Code) a text version of every sheet so it can help refine the CEL MEL Platform. Values are cached cell values; formulas are described per sheet. Colours and column widths are not kept, except the CEL-scope legend, which is derived from font colour.

## Files

| File | Sheet | What it holds |
|---|---|---|
| 01_ProFrame.md | ProFrame | Programme details, partners, 10 delivery models, key impact measures, goal/objectives/assumptions, results framework (areas, indicators 1-52, key measures, disaggregation, markers, MoV, assumptions, risks) |
| 02_MEL_Plan.md | MEL Plan | Indicators with baseline, LoP target, methods, frequency, sources, responsible role, CEL planner basis; open questions for Agri-Impact |
| 03_Project_IPTT.md | Project IPTT | Consolidated IPTT: 56 indicators (IM, OC, OP IDs), Y1 and Q1-Q4 targets/achievements, reported-in check |
| 04_BDS_IPTT.md | BDS IPTT | Model sheet: 22 BDS indicators |
| 05_WAN_IPTT.md | WAN IPTT | Model sheet: 9 WAN indicators |
| 06_Cross-cutting_IPTT.md | Cross-cutting IPTT | Model sheet: 12 inclusion, safeguarding and coverage indicators |
| 07_CEL_IPTT_Guide.md | CEL IPTT Guide | User guide: workflow, roles, counting rules, field guide, verification, worked example |
| 08_PIRS.md | PIRS | 59 indicator reference sheets (definition, disaggregation, unit, data type, method, source, frequency) |
| 09_Shared_Measures_2.0.md | Shared Measures 2.0 | 46 programme-wide shared measure definitions |

## How the workbook fits together

- **Flow:** ProFrame (framework) -> MEL Plan (targets, methods, roles) -> model sheets (BDS, WAN, Cross-cutting IPTT: where targets and verified achievements are entered) -> Project IPTT (formula-only consolidation). PIRS and Shared Measures hold indicator definitions.
- **Reporting period:** Y1 = Jul 2026 to Jun 2027. Q1 Jul-Sep 2026, Q2 Oct-Dec 2026, Q3 Jan-Mar 2027, Q4 Apr-Jun 2027.
- **Indicator IDs:** IM1-IM4 (impact), OC1-OC13 (outcome), OP1-OP39 (output). The ProFrame uses a different number (# 1-52) and the PIRS has no ID, so indicators are currently linked by wording only.
- **One indicator, one sheet:** each ID appears in exactly one model sheet. Project IPTT pulls values with `SUMIFS`/`COUNTIFS` on the ID in column A and returns blank (not 0) when the model sheet has no entry. The earlier design had a check column V in Project IPTT (values `BDS IPTT`, `WAN IPTT`, `Cross-cutting IPTT`, `Not in CEL scope`, `NOT ASSIGNED`, `CHECK: in more than one sheet`); in this file column V is empty, so the export computes the reported-in sheet from the model-sheet IDs.
- **Core formulas:** Y1 value = `IF(COUNT(Q1..Q4)=0,"",SUM(Q1..Q4))`; percentage = `IF(achieved="","-",IFERROR(achieved/target,"-"))`.
- **Blank vs zero:** blank = not due or not reported; 0 = measured and none achieved.
- **Aggregation types:** Incremental, Cumulative, Annual survey (not summed). **Fish type:** Catfish, Tilapia, Catfish and Tilapia, Not applicable. Achieved cells accept numbers >= 0.
- **No unique-reach totals:** BDS, WAN and work results are not added together as unique programme reach; participants need a unique ID (Ghana Card or alternative).
- **CEL scope:** derived from font colour in ProFrame, MEL Plan and Project IPTT (Applicable to CEL; To be confirmed; New output indicator; Not treated as WEO; plain font = not in CEL scope). Starter packs and micro-grants are not CEL scope.
- **WEO rule:** training delivered by CEL is WEO. Mobilisation/sensitisation is onboarding (not WEO). Gender focal persons are not WEO participants.
- **Roles:** MEAL Lead, MEAL Officer, BDS Coach, BDS Officer, GYSI Lead (leads WAN), Communication Lead, Finance Lead, Project Team, Program Lead, CEL Admin, Partner's. Each model-sheet row has Collect / Verify / Review roles.
- **Data quality (from the 13 Oct 2026 MEL meeting):** completeness check, then phone-call verification (80% agreement accepted; below 80% rework and resubmit).

## Suggested entities for the platform

`Indicator` (id, text, level, unit, fish type, aggregation type, owner model, scope flag, key measure, markers, disaggregations, MoV, PIRS definition) | `Target` (indicator, quarter, value) | `Achievement` (indicator, quarter, value, verified by, evidence) | `DeliveryModel` (slot, name, sheet) | `ResultsArea` (id, name, key result statement, assumptions, risks) | `Participant` (unique ID, sex, disability status, youth category, location, consent) | `Group/Cooperative` (register with status flags) | `Role/User`.

## Items to settle before building (observed in this file)

- Indicators in plain (not-in-CEL-scope) font in Project IPTT (13): IM4, OP1, OP2, OP3, OP6, OP7, OP8, OP12, OP13, OP14, OP19, OP20, OP21.
- MEL Plan rows whose note says the value was cleared or replaced but still show a LoP target: row 18 (36000), row 19 (34000), row 20 (90000000).
- MEL Plan YiW LoP target (row 12) and the Project IPTT Y1 target (IM1) use different bases; confirm the Y1 x 4 rule and the tracking level (CEL vs programme).
- Indicator wording has typos carried from the source template (for example "tranistioned", "dignifed", "enterprisesshowing"); keep the approved wording or correct it everywhere (ProFrame, MEL Plan, IPTT, PIRS).
- Sheet layouts differ slightly (header row is row 8 in Project IPTT and row 7 in the model sheets); a parser should find the header row by the `ID` cell in column A.
- Several quarterly phasings are marked to confirm (yellow cells in the model sheets).
