# A5 Training Q2

Assignment 5: training schedule for Quarter 2. Q2 targets are read live from the IPTT sheets by indicator ID; participants per cohort is computed from planned cohorts. Gantt bars are conditional formatting driven by Start, End and Status.

**Sheet title:** Assignment 5: Training schedule, Quarter 2

**Subtitle:** Training and capacity building, October to December 2026 (draft: yellow dates are proposals for the team to confirm)


## Q2 training targets (linked to the IPTT sheets)

- **Q2 window**: 1 October to 31 December 2026 (Y1 Q2)
- **Training indicators with a Q2 target**: 5
- **Reminder**: Q2 targets are indicator targets, not a headcount. Each participant is counted once per indicator.

| # | Training / activity | ID | Q2 target | Planned cohorts | Per cohort | Lead facilitator (R) | Support / partner | Venue | Start | End | Status | Prerequisite / note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A. Preparation** |  |  |  |  |  |  |  |  |  |  |  |  |
| 1 | Confirm partner calendar and cohorts (joint delivery calendar) |  |  |  |  | BDS Coach | Partner's; BDS Officer | CEL office | 2026-10-19 | 2026-10-30 | To confirm | Links to A4 step 1 |
| 2 | Prepare facilitators, content and accessible materials (PWD accommodation, language) |  |  |  |  | BDS Officer | GYSI Lead; Communication Lead | CEL office | 2026-10-26 | 2026-11-13 | To confirm | Accessibility checked for PWD participants |
| 3 | Book accessible venues and arrange logistics |  |  |  |  | CEL Admin | BDS Officer | To be confirmed | 2026-10-26 | 2026-11-20 | To confirm | Venue accessibility confirmed |
| **B. Training delivery** |  |  |  |  |  |  |  |  |  |  |  |  |
| 4 | BDS and entrepreneurship skills (ideation and early business development workshops) | OP9 | 135 |  |  | BDS Officer | BDS Coach; Partner's | To be confirmed | 2026-11-16 | 2026-12-18 | To confirm | After the cohort is onboarded (A4 steps 6 and 9) |
| 5 | Safeguarding: identify and respond to safeguarding issues | OP31 | 150 |  |  | GYSI Lead | Partner's; Communication Lead | To be confirmed | 2026-11-16 | 2026-12-11 | To confirm | Held early in each cohort; no case details in training records |
| 6 | Gender, financial literacy and business mentoring for women in cooperatives/clusters | OP29 | 150 |  |  | BDS Officer | GYSI Lead; BDS Coach | To be confirmed | 2026-11-23 | 2026-12-18 | To confirm | Needs the cooperative/cluster register and participant IDs |
| 7 | Gender transformative training | OP30 | 150 |  |  | GYSI Lead | BDS Officer | To be confirmed | 2026-11-23 | 2026-12-18 | To confirm | Count each person once per indicator |
| 8 | Mentorship and digital literacy | OP32 | 150 |  |  | BDS Officer | BDS Coach | To be confirmed | 2026-11-30 | 2026-12-22 | To confirm | Digital business skills for the BDS cohort |
| **C. Completion and data** |  |  |  |  |  |  |  |  |  |  |  |  |
| 9 | Attendance and completion verification (registers matched to participant IDs) |  |  |  |  | MEAL Officer | BDS Officer; GYSI Lead | CEL office | 2026-11-30 | 2026-12-23 | To confirm | Completion rule applied before counting |
| 10 | Q2 training report and data cut-off |  |  |  |  | MEAL Officer | Program Lead | CEL office | 2026-12-21 | 2026-12-31 | To confirm | Feeds the Q2 IPTT |

Notes: (1) Q2 targets are read from the IPTT sheets. They are separate indicator targets, not a headcount: one participant may attend several trainings and is counted once per indicator. (2) Enter planned cohorts (yellow) to see the participants per cohort. (3) Dates are proposals; change the yellow dates and the bars update.


## Gantt calendar (columns O to AB)

Week-beginning (Monday) dates in row 12: 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19, 2026-10-26, 2026-11-02, 2026-11-09, 2026-11-16, 2026-11-23, 2026-11-30, 2026-12-07, 2026-12-14, 2026-12-21, 2026-12-28. Bars are not stored as values: they are drawn by the conditional formatting rules below from the Start and End dates and the Status.


## Formulas (active; complete inventory)

11 formulas. Formulas are shown exactly as stored in the workbook. `{r}` stands for the formula's own row number. Cached values appear in the content tables above.

```
E8: =COUNT(E13:E24)
    => 5
E18: =SUMIFS('BDS IPTT'!$K$1:$K$100,'BDS IPTT'!$A$1:$A$100,"OP9")
    => 135
G18: =IF(AND(ISNUMBER(E18),ISNUMBER(F18),F18>0),ROUNDUP(E18/F18,0),"")
    => 
E19: =SUMIFS('Cross-cutting IPTT'!$K$1:$K$100,'Cross-cutting IPTT'!$A$1:$A$100,"OP31")
    => 150
G19: =IF(AND(ISNUMBER(E19),ISNUMBER(F19),F19>0),ROUNDUP(E19/F19,0),"")
    => 
E20: =SUMIFS('BDS IPTT'!$K$1:$K$100,'BDS IPTT'!$A$1:$A$100,"OP29")
    => 150
G20: =IF(AND(ISNUMBER(E20),ISNUMBER(F20),F20>0),ROUNDUP(E20/F20,0),"")
    => 
E21: =SUMIFS('Cross-cutting IPTT'!$K$1:$K$100,'Cross-cutting IPTT'!$A$1:$A$100,"OP30")
    => 150
G21: =IF(AND(ISNUMBER(E21),ISNUMBER(F21),F21>0),ROUNDUP(E21/F21,0),"")
    => 
E22: =SUMIFS('BDS IPTT'!$K$1:$K$100,'BDS IPTT'!$A$1:$A$100,"OP32")
    => 150
G22: =IF(AND(ISNUMBER(E22),ISNUMBER(F22),F22>0),ROUNDUP(E22/F22,0),"")
    => 
```

## Data validation

- type `list`, rule `"Not started,In progress,Done,Delayed,To confirm"` (between), applies to `J15:J16 J18:J20 J22:J24 J26:J27 M14:M16 M18:M22 M24:M25`

## Conditional formatting rules

- `O13:AB25`: `AND($K13<>"",$L13<>"",O$12<=$L13,O$12+6>=$K13,$M13="Done")` (fill FF548235)
- `O13:AB25`: `AND($K13<>"",$L13<>"",O$12<=$L13,O$12+6>=$K13,$M13="Delayed")` (fill FFC00000)
- `O13:AB25`: `AND($K13<>"",$L13<>"",O$12<=$L13,O$12+6>=$K13)` (fill FF2E75B6)
- `O12:AB12`: `AND(TODAY()>=O12,TODAY()<=O12+6)` (fill FFFFC000)

## Hyperlinks

| Cell | Target |
|---|---|
| T2 | 'Cover'!A1 |
