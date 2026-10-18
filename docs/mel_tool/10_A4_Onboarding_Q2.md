# A4 Onboarding Q2

Assignment 4: onboarding schedule for Quarter 2 (1 Oct to 31 Dec 2026). Yellow Start/End dates are proposals; Gantt bars are conditional formatting driven by Start, End and Status. Q2 targets are read live from the IPTT sheets.

**Sheet title:** Assignment 4: Onboarding schedule, Quarter 2

**Subtitle:** Onboarding of participants, October to December 2026 (draft: yellow dates are proposals for the team to confirm)


## Q2 onboarding targets (linked to the IPTT sheets)

- **Q2 window**: 1 October to 31 December 2026 (Y1 Q2)
- **Youth mobilised into the programme, Q2 target (OP27)**: 135
- **Young women PWDs engaged, Q2 target (OP22)**: 2
- **Completed onboarding is needed before training starts (see A5)**: Cohort lists handed to the training schedule

| # | Activity | Output / what "done" looks like | Lead (R) | Support | Location / partner | Start | End | Status |
|---|---|---|---|---|---|---|---|---|
| **A. Preparation** |  |  |  |  |  |  |  |  |
| 1 | Confirm partner needs and joint delivery calendar | Partner needs assessment completed; joint onboarding and training calendar agreed. | BDS Coach | MEAL Officer; Partner's | All partners | 2026-10-19 | 2026-10-30 | To confirm |
| 2 | Confirm eligibility criteria, ID and consent forms, and registers | Final registration form, consent form and participant register template approved. | MEAL Officer | GYSI Lead; BDS Officer | CEL office | 2026-10-19 | 2026-10-30 | To confirm |
| **B. Mobilisation and selection** |  |  |  |  |  |  |  |  |
| 3 | Community entry and stakeholder engagement | Community leaders, group champions and partners engaged; entry meetings recorded. | BDS Officer | Project Team; Communication Lead | To be confirmed | 2026-10-26 | 2026-11-13 | To confirm |
| 4 | Sensitisation and mobilisation sessions (gender inclusion, disability inclusion, safeguarding messages) | Sessions held; attendance lists and session reports. | Communication Lead | GYSI Lead; BDS Officer | To be confirmed | 2026-11-02 | 2026-11-27 | To confirm |
| 5 | Participant identification and eligibility screening | Screened list of eligible youth, with PWDs identified (aim: 5%). | BDS Officer | GYSI Lead; Partner's | To be confirmed | 2026-11-09 | 2026-12-04 | To confirm |
| **C. Registration and data** |  |  |  |  |  |  |  |  |
| 6 | Registration: consent, unique ID, contacts, location and disability status | Registered participants with valid ID, consent and group champion contact. | BDS Officer | MEAL Officer; Partner's | To be confirmed | 2026-11-16 | 2026-12-11 | To confirm |
| 7 | Enter participants in the register and run the duplicate check | Clean participant register; duplicates resolved. | MEAL Officer | BDS Officer | CEL office | 2026-11-23 | 2026-12-15 | To confirm |
| 8 | Data quality check: completeness check and phone-call verification sample | Verification note; agreement of 80% or more accepted, otherwise rework. | MEAL Officer | MEAL Lead | CEL office | 2026-11-30 | 2026-12-18 | To confirm |
| **D. Handover and reporting** |  |  |  |  |  |  |  |  |
| 9 | Allocate participants to cohorts and hand over to the training schedule (A5) | Cohort lists for each training in A5. | BDS Officer | BDS Coach; GYSI Lead | CEL office | 2026-12-07 | 2026-12-18 | To confirm |
| 10 | Q2 onboarding report and data cut-off | Onboarding report with numbers against the Q2 target; data cut-off for the Q2 IPTT. | MEAL Officer | Program Lead | CEL office | 2026-12-21 | 2026-12-31 | To confirm |

Notes: (1) Dates are proposals; change the yellow dates and the bars update. (2) Locations are to be confirmed with partners. (3) Q2 onboarding feeds the Q2 training targets in A5; each participant is counted once per indicator.


## Gantt calendar (columns K to X)

Week-beginning (Monday) dates in row 13: 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19, 2026-10-26, 2026-11-02, 2026-11-09, 2026-11-16, 2026-11-23, 2026-11-30, 2026-12-07, 2026-12-14, 2026-12-21, 2026-12-28. Bars are not stored as values: they are drawn by the conditional formatting rules below from the Start and End dates and the Status.


## Formulas (active; complete inventory)

2 formulas. Formulas are shown exactly as stored in the workbook. `{r}` stands for the formula's own row number. Cached values appear in the content tables above.

```
E8: =SUMIFS('BDS IPTT'!$K$1:$K$100,'BDS IPTT'!$A$1:$A$100,"OP27")
    => 135
E9: =SUMIFS('Cross-cutting IPTT'!$K$1:$K$100,'Cross-cutting IPTT'!$A$1:$A$100,"OP22")
    => 2
```

## Data validation

- type `list`, rule `"Not started,In progress,Done,Delayed,To confirm"` (between), applies to `J15:J16 J18:J20 J22:J24 J26:J27 M14:M16 M18:M22 M24:M25`

## Conditional formatting rules

- `K14:X27`: `AND($H14<>"",$I14<>"",K$13<=$I14,K$13+6>=$H14,$J14="Done")` (fill FF548235)
- `K14:X27`: `AND($H14<>"",$I14<>"",K$13<=$I14,K$13+6>=$H14,$J14="Delayed")` (fill FFC00000)
- `K14:X27`: `AND($H14<>"",$I14<>"",K$13<=$I14,K$13+6>=$H14)` (fill FF2E75B6)
- `K13:X13`: `AND(TODAY()>=K13,TODAY()<=K13+6)` (fill FFFFC000)

## Hyperlinks

| Cell | Target |
|---|---|
| Q2 | 'Cover'!A1 |
