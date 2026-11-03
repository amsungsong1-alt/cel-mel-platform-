# Project IPTT

Consolidated IPTT (Assignment 1). Formula-driven: for every indicator ID in column A, the quarter cells (H, I, K, L, N, O, Q, R) look the ID up in BDS IPTT, WAN IPTT and Cross-cutting IPTT inside this workbook and return blank if no sheet has a value, otherwise the sum. Y1 and % columns are formulas. Do not type into this sheet; enter targets and achievements in the model sheets. Column V ("Reported in") is a separate lookup that currently points at an external workbook rather than the three sheets inside this one (see the note under Header lines) and caches `#VALUE!` on every row; it does not affect the H/I/K/L/N/O/Q/R/E/F/G/J/M/P/S target-and-achievement formulas above, which are all still internal and working.

## Header lines

- B2: Last revised on: 22nd October 2026
- B3: Last revised by: Muhammadu Sungsong Aboubakr
- B4 (literal cached text): Consolidated from BDS, WAN and Cross-cutting sheets | CEL-scope indicators: 55 | Not in CEL scope: 0 | With Y1 achievement reported: 0 | At or above 100% of Y1 target: 0 | Unassigned/duplicated IDs: 0
- **B4 is currently broken and should not be trusted as-is.** Its formula is `="Consolidated from..."&(COUNTA(A10:A66)-COUNTIF(V10:V66,"Not in CEL scope"))&" | Not in CEL scope: "&COUNTIF(V10:V66,"Not in CEL scope")&...&COUNTIF(V10:V66,"CHECK*")`, which depends entirely on column V. Column V's own formula was changed in this revision to reference an external workbook (`'[1]BDS IPTT'!...`, resolving to `SAWA_IP_MEL_System_Tool_CEL_v3_10_22_2026_updated.xlsx`) instead of the internal BDS/WAN/Cross-cutting IPTT sheets, so every one of the 55 cells in column V now caches `#VALUE!`. With no cell in V ever equal to the text "Not in CEL scope" or "CHECK*", B4's formula always reports "CEL-scope indicators: 55 | Not in CEL scope: 0 | ... | Unassigned/duplicated IDs: 0" regardless of the real underlying data — the 55/0 is an artifact of the break, not a real count. A new "Footnote" block the sheet itself added below row 71 (rows 78-91, not otherwise reproduced in this file; out of scope for a fact-correction pass, flagged for a human to decide whether to add) restates what the pre-break figures meant: 42 of the 55 indicator IDs are physically present in one of the three model sheets (BDS IPTT 21, WAN IPTT 9, Cross-cutting IPTT 12) and the other 13 (IM4; OP1, OP2, OP3, OP6, OP7, OP8, OP12, OP13, OP14, OP19, OP20, OP21) are not reported in any CEL model sheet — this 42/13 split is the "Reported in" (column V) concept and is independent of the separate font-colour "CEL scope" legend in column B/the table below (which classifies indicators as Applicable to CEL / Not in CEL scope / etc. regardless of which sheet reports them).
- With Y1 achievement reported (0) and At or above 100% of Y1 target (0) do not depend on column V and remain accurate (no achievements have been entered yet).
- B5: Formular-driven: do not type in Targets or Achieved here. Enter them in the model sheets (BDS IPTT, WAN IPTT, Cross-cutting IPTT). Totals are NOT unique program reach: BDS, WAN and work results are not added together.
- B6: Indicator Performance Tracking Table (IPTT)

## Indicator definitions (55)

The "Reported in" column below is the indicator's real, manually-verified reporting sheet (confirmed directly against the BDS IPTT / WAN IPTT / Cross-cutting IPTT sheets' own column A). It is NOT the live cached value of column V, which is currently `#VALUE!` for all 55 rows because of the broken external-workbook reference described under Header lines.

| ID | Level | Indicator | Unit of Measure | Fish Type | CEL scope (font legend) | Reported in (manually verified; live column V formula is broken, see above) | CEL planner notes (col U) |
|---|---|---|---|---|---|---|---|
| IM1 | Impact | SM 5.1 <br>Number of young women and PWDs in Youth-in-Work (YiW) attributable to program interventions across the aquaculture value chain (all aquaculture-related work) | Young Women & PWDs | Catfish and Tilapia | Applicable to CEL | BDS IPTT | Planner III.R1: 100 YiW in value addition (40/30/30). Disaggregate "value addition": a job needs verified work and income. Updated 22 Oct 2026 (MEL session): LoP 2,000 over 4 years (Program Lead); Year 1 is 100. |
| IM2 | Impact | SM 6.1 <br>Percentage of young women accessing dignifed and fulfilling (D&F) work attributable to program interventions across the aquaculture value chain | Young Women | Catfish and Tilapia | Applicable to CEL | BDS IPTT | 86% of YiW, so 86 of the 100 jobs, and LoP 1,720. Measured by a participant survey; regular income plus any two of sense of purpose, respect at the workplace, reputable work. |
| IM3 | Impact | SM 6.1 <br>Percentage of PWDs accessing dignifed and fulfilling (D&F) work attributable to program interventions across the aquaculture value chain | PWDs | Not applicable | Applicable to CEL | Cross-cutting IPTT | 5% of the 1,720 is 86; the planner Y1 is 8 (1/2/2/3). |
| IM4 | Impact | SM 5.1 <br>Percentage of young women and PWDs who report improved ability to meet basic household needs (food, education, health, housing, savings) attributable to incomes earned by participation in SAWA | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | |
| OC1 | Outcomes | SM 5.1 <br>Number of young women tranistioned into wage- and self-employment in the aquaculture value chain | Young Women & PWDs | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OC2 | Outcomes | SM 5.1 Number of young women tranistioned into wage employment in the aquaculture value chain | Young Women & PWDs | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OC3 | Outcomes | SM 5.1 Number of young women tranistioned into self-employment in the aquaculture value chain | Young Women & PWDs | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OC4 | Outcomes | SM 5.1 <br>Number of young women in new, improved and additional employments in the aquaculture value chain | Young Women & PWDs | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OC5 | Outcomes | SM 4.2 <br>Number of supported young-women-owned enterprises showing growth through market expansion / diversification | Enterprises | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OC6 | Outcomes | SM 4.1<br>Number of supported young-women-owned enterprisesshowing growth through increased in revenue | Enterprises | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OC7 | Outcomes | Number of CEL-referred enterprises supported with Catalytic Fund | Enterprises supported | Catfish and Tilapia | Not in CEL scope | BDS IPTT | TechnoServe planner III.3: 10 enterprises (Q3 3, Q4 7). Programme-wide figure kept as a reference; CEL’s share to be agreed by 30 Oct 2026. |
| OC8 | Outcomes | Number of CEL-referred enterprises supported with Micro Investment Fund | Enterprises supported | Catfish and Tilapia | Not in CEL scope | BDS IPTT | TechnoServe planner III.4: 150 enterprises (Q3 52, Q4 98). Programme-wide figure kept as a reference; CEL’s share to be agreed by 30 Oct 2026. |
| OC9 | Outcomes | Quantity (MT) of fish produced annually | Fish (MT) | Catfish and Tilapia | Not in CEL scope | BDS IPTT | Planner III.R2 total 115.7 MT (Q2 46.3, Q3 34.7, Q4 34.7). PWD MT (II.R6: 1/2/2/3) is a disaggregation, not an addition. Updated 22 Oct 2026; re-phase with AIL (planner Q1 PWD of 1 MT exceeds the Q1 total of 0). |
| OC10 | Outcomes | Amount of revenue (USD) from fish produced annually | US Dollars | Catfish and Tilapia | Not in CEL scope | BDS IPTT | Planner III.R3 total USD 208,333 (Q2 83,333, Q3 62,500, Q4 62,500). PWD revenue (II.R7, USD 16,667) is a disaggregation. Updated 22 Oct 2026; re-phase with AIL. |
| OC11 | Outcomes | SM 8.2<br>Percentage of young women and PWDs who report receiving support (business regularisation, mentorship, market linkage, BDS, etc.) from WAN | WAN participants | Not applicable | Applicable to CEL | WAN IPTT | |
| OC12 | Outcomes | SM 8.2<br>Percentage of young women and PWDs who report active participantion in WAN activities | WAN participants | Not applicable | Applicable to CEL | WAN IPTT | |
| OC13 | Outcomes | SM 8.2<br>Percentage of WAN members who demonstrate increased confidence, agency and voice in aquaculture-related decision-making | WAN participants | Not applicable | Applicable to CEL | WAN IPTT | |
| OC14 | Outcomes | Percentage of PWDs who report that workplaces are accessible and inclusive | PWDs | Not applicable | Applicable to CEL | Cross-cutting IPTT | |
| OC15 | Outcomes | Percentage of young women and PWDs who report that workplaces are safe | PWDs | Not applicable | Applicable to CEL | Cross-cutting IPTT | |
| OP1 | Outputs | SM 1.1 <br>Number of young women accessing starter pack for production | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Starter packs: planner shows 0/blank (I.10, II.1). No target set. |
| OP2 | Outputs | SM 1.1 <br>Number of young women accessing starter pack for processing and value-added products development | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Starter packs: planner shows 0/blank (I.10, II.1). No target set. |
| OP3 | Outputs | SM 1.1 <br>Number of young women accessing starter pack for marketing and distribution of aquaculture products | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Starter packs: planner shows 0/blank (I.10, II.1). No target set. |
| OP4 | Outputs | SM 4<br>Number of young women supported to start/operate their own aquaculture enterprises | Young Women & PWDs | Catfish and Tilapia | Not in CEL scope | BDS IPTT | |
| OP5 | Outputs | SM 4.3 Number of young women and PWDs employed by supported aquaculture enterprises | Young Women & PWDs | Catfish and Tilapia | Not in CEL scope / unclassified (plain font) | BDS IPTT | |
| OP6 | Outputs | SM 1.1 <br>Number of young women who completed training in aquaculture production | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | |
| OP7 | Outputs | SM 1.1<br>Number of young women who completed training in aquaculture processing and product development | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | |
| OP8 | Outputs | SM 1.1<br>Number of young women who completed training in marketing of aquaculture products (fresh and processed) | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | |
| OP9 | Outputs | SM 1.1 <br>Number of young women who completed training in aquaculture business development and entrepreneurship skills | Young Women & PWDs | Catfish and Tilapia | Applicable to CEL | BDS IPTT | Planner I.3 BDS/entrepreneurship training: 500 (95/135/135/135). |
| OP10 | Outputs | Number of existing aquaculture enterprises trained in BDS, production, and value addition | Existing enterprises | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OP11 | Outputs | Number of new aquaculture enterprises trained in BDS, production, and value addition | Existing enterprises | Catfish and Tilapia | Applicable to CEL | BDS IPTT | |
| OP12 | Outputs | SM 1.1<br>Number of young women who access training starter pack for aquaculture production | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Starter packs: planner shows 0/blank (I.10, II.1). No target set. |
| OP13 | Outputs | SM 1.1<br>Number of young women who access training starter pack for aquaculture processing and value addition | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Starter packs: planner shows 0/blank (I.10, II.1). No target set. |
| OP14 | Outputs | SM 1.1<br>Number of young women who access training starter pack for marketing of aquaculture products | Young Women & PWDs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Starter packs: planner shows 0/blank (I.10, II.1). No target set. |
| OP15 | Outputs | Number of Women in Aquaculture Network (WAN) groups established and active | WAN groups (cooperatives/clusters) | Not applicable | Applicable to CEL | WAN IPTT | PROXY: planner III.6 cooperatives/clusters established (15/10 = 25). The WAN note confirms Q3/Q4 phasing. |
| OP16 | Outputs | Number of young women actively participating in WAN | Young Women | Not applicable | Applicable to CEL | WAN IPTT | Planner I.11 WAN leadership/mentorship forums: 500 women engaged (Q3 300, Q4 200). Phasing confirmed in concept note. |
| OP17 | Outputs | Number of young women-owned enterprises mentored and coached by WAN | WAN participants | Not applicable | Applicable to CEL | WAN IPTT | Not in CEL Y1 planner. No target set. |
| OP18 | Outputs | SM 8.2<br>Number of advocacy campaigns undertaken by WAN | WAN | Not applicable | Applicable to CEL | WAN IPTT | |
| OP19 | Outputs | Number of implementing partners that engage PWDs in aquaculture-related work. | IPs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Not in CEL Y1 planner. No target set. |
| OP20 | Outputs | Number of employers or enterprises (including anchor private sector) that engage PWDs in aquaculture-related work. | SMEs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Not in CEL Y1 planner. No target set. |
| OP21 | Outputs | Number of employers that provided reasonable accommodation to PWDs | SMEs | | Not in CEL scope / unclassified (plain font) | Not reported in any CEL model sheet | Not in CEL Y1 planner. No target set. |
| OP22 | Outputs | Number of young women PWDs engaged | PWDs | Not applicable | Applicable to CEL | Cross-cutting IPTT | Planner I.13/II.R5: 8 PWD (planner says 8 PWD mentors; 1/2/2/3). Also tracked on CI-8. 5% aim confirmed. |
| OP23 | Outputs | Number of community sensitization campaigns held on gender inclusion, disability inclusion and safeguarding | Campaigns | Not applicable | Applicable to CEL | Cross-cutting IPTT | Planner I.22 safeguarding awareness campaigns/roadshows: 6 (3/3). 3 in Q3, 3 in Q4. |
| OP24 | Outputs | Number of communities sensitized on gender inclusion and safeguarding | Communities | Not applicable | Not in CEL scope | Cross-cutting IPTT | |
| OP25 | Outputs | Number of regions, districts and communities reached through partner operations (hubs, clusters, anchor sites, etc.) | Regions, districts, communities | Not applicable | Applicable to CEL | Cross-cutting IPTT | |
| OP26 | Outputs | Number of region, districts and communities in which participants can be traced to as their residence | Regions, districts, communities | Not applicable | Applicable to CEL | Cross-cutting IPTT | |
| OP27 | Outputs | Number of youth mobilised into the programme (community entry, sensitization, selection) | Youth Mobilised | Catfish and Tilapia | Applicable to CEL | BDS IPTT | Planner I.1: Y1 500 x4. Onboarding, not a WEO count. |
| OP28 | Outputs | Number of gender focal persons trained on GALS and EMAP | Focal persons (count of individuals) | Not applicable | Applicable to CEL | Cross-cutting IPTT | Planner I.9: Y1 25 x4. Quarter split assumed, confirm. |
| OP29 | Outputs | Number of young women in women-led cooperatives/clusters trained in gender, financial literacy and business mentoring | Young women (count of individuals) | Catfish and Tilapia | Missing indicator/new output identified (in CEL's consolidated plan) | BDS IPTT | Planner I.17: Y1 500 x4. The BDS note confirms 150/150/200. |
| OP30 | Outputs | Number of persons trained in gender transformative trainings | Persons (count of individuals) | Not applicable | Applicable to CEL | Cross-cutting IPTT | Planner I.19: Y1 500 x4. Quarter split assumed, confirm. |
| OP31 | Outputs | Number of young women trained to identify and respond to safeguarding issues | Young women (count of individuals) | Not applicable | Applicable to CEL | Cross-cutting IPTT | Planner I.20: Y1 500 x4. Quarter split assumed, confirm. |
| OP32 | Outputs | Number of persons trained in mentorship and digital literacy | Persons (count of individuals) | Catfish and Tilapia | Missing indicator/new output identified (in CEL's consolidated plan) | BDS IPTT | Planner IV.5: Y1 500 x4. Quarter split assumed, confirm. |
| OP33 | Outputs | Number of WAN leadership bootcamps and exchange visits held | Events (count of bootcamps and visits) | Not applicable | Applicable to CEL | WAN IPTT | WAN note: 1 bootcamp or exchange visit in Q3. A planner note citing Y1 2 x4 is superseded: confirm with the Program Lead. |
| OP34 | Outputs | Number of women-led cooperatives/clusters with developed gender-responsive governance frameworks | Cooperatives/clusters (count) | Not applicable | Applicable to CEL | WAN IPTT | Women-led groups strengthened (WAN note: 15 in Q3, 10 in Q4 = 25). Adopted governance framework plus evidence of changed practice. One group register: report once. |
| OP35 | Outputs | Number of sites/partners with institutionalized safeguarding and occupational health standards | Sites/partners (count) | Not applicable | Not in CEL scope | Cross-cutting IPTT | |
| OP36 | Outputs | Number of enterprises prepared and referred to TechnoServe for Catalytic Fund or Micro Investment Fund support | Enterprises referred | Catfish and Tilapia | Applicable to CEL | BDS IPTT | TechnoServe planner III.3 / III.4 (referral step): Q3 88, Q4 163 (young women at the growout stage, PII.R3). A referral is not a funding or job outcome. |

## Targets and achievements (cached values)

Blank = not due / not reported (not zero). `-` = percentage not computable. Y1 = Jul 2026 to Jun 2027; Q1 Jul-Sep 2026, Q2 Oct-Dec 2026, Q3 Jan-Mar 2027, Q4 Apr-Jun 2027.

| ID | Y1 Target | Y1 Achieved | Y1 % | Q1 Target | Q1 Achieved | Q1 % | Q2 Target | Q2 Achieved | Q2 % | Q3 Target | Q3 Achieved | Q3 % | Q4 Target | Q4 Achieved | Q4 % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IM1 | 100 | | - | 0 | | - | 40 | | - | 30 | | - | 30 | | - |
| IM2 | 86 | | - | 0 | | - | 34.4 | | - | 25.8 | | - | 25.8 | | - |
| IM3 | | | - | | | - | | | - | | | - | | | - |
| IM4 | | | - | | | - | | | - | | | - | | | - |
| OC1 | | | - | | | - | | | - | | | - | | | - |
| OC2 | | | - | | | - | | | - | | | - | | | - |
| OC3 | | | - | | | - | | | - | | | - | | | - |
| OC4 | | | - | | | - | | | - | | | - | | | - |
| OC5 | | | - | | | - | | | - | | | - | | | - |
| OC6 | | | - | | | - | | | - | | | - | | | - |
| OC7 | 10 | | - | | | - | | | - | 3 | | - | 7 | | - |
| OC8 | 150 | | - | | | - | | | - | 52 | | - | 98 | | - |
| OC9 | 123.7 | | - | 1 | | - | 48.3 | | - | 36.7 | | - | 37.7 | | - |
| OC10 | 225000 | | - | 2083 | | - | 87500 | | - | 66667 | | - | 68750 | | - |
| OC11 | | | - | | | - | | | - | | | - | | | - |
| OC12 | | | - | | | - | | | - | | | - | | | - |
| OC13 | | | - | | | - | | | - | | | - | | | - |
| OC14 | | | - | | | - | | | - | | | - | | | - |
| OC15 | | | - | | | - | | | - | | | - | | | - |
| OP1 | | | - | | | - | | | - | | | - | | | - |
| OP2 | | | - | | | - | | | - | | | - | | | - |
| OP3 | | | - | | | - | | | - | | | - | | | - |
| OP4 | | | - | | | - | | | - | | | - | | | - |
| OP5 | | | - | | | - | | | - | | | - | | | - |
| OP6 | | | - | | | - | | | - | | | - | | | - |
| OP7 | | | - | | | - | | | - | | | - | | | - |
| OP8 | | | - | | | - | | | - | | | - | | | - |
| OP9 | 500 | | - | | | - | 230 | | - | 135 | | - | 135 | | - |
| OP10 | | | - | | | - | | | - | | | - | | | - |
| OP11 | | | - | | | - | | | - | | | - | | | - |
| OP12 | | | - | | | - | | | - | | | - | | | - |
| OP13 | | | - | | | - | | | - | | | - | | | - |
| OP14 | | | - | | | - | | | - | | | - | | | - |
| OP15 | 25 | | - | 0 | | - | 0 | | - | 15 | | - | 10 | | - |
| OP16 | 500 | | - | 0 | | - | 0 | | - | 300 | | - | 200 | | - |
| OP17 | | | - | | | - | | | - | | | - | | | - |
| OP18 | | | - | | | - | | | - | | | - | | | - |
| OP19 | | | - | | | - | | | - | | | - | | | - |
| OP20 | | | - | | | - | | | - | | | - | | | - |
| OP21 | | | - | | | - | | | - | | | - | | | - |
| OP22 | 8 | | - | | | - | 3 | | - | 2 | | - | 3 | | - |
| OP23 | 3 | | - | | | - | 0 | | - | 0 | | - | 3 | | - |
| OP24 | | | - | | | - | | | - | | | - | | | - |
| OP25 | | | - | | | - | | | - | | | - | | | - |
| OP26 | | | - | | | - | | | - | | | - | | | - |
| OP27 | 500 | | - | | | - | 230 | | - | 135 | | - | 135 | | - |
| OP28 | 25 | | - | 0 | | - | 0 | | - | 15 | | - | 10 | | - |
| OP29 | 500 | | - | 0 | | - | 150 | | - | 150 | | - | 200 | | - |
| OP30 | 500 | | - | 0 | | - | 150 | | - | 150 | | - | 200 | | - |
| OP31 | 500 | | - | 0 | | - | 150 | | - | 150 | | - | 200 | | - |
| OP32 | 500 | | - | 0 | | - | 150 | | - | 150 | | - | 200 | | - |
| OP33 | 1 | | - | 0 | | - | 0 | | - | 1 | | - | 0 | | - |
| OP34 | 25 | | - | 0 | | - | 0 | | - | 15 | | - | 10 | | - |
| OP35 | 2 | | - | 0 | | - | 0 | | - | 0 | | - | 2 | | - |
| OP36 | 251 | | - | | | - | | | - | 88 | | - | 163 | | - |

## Formulas (active; complete inventory)

883 formulas (825 in the 15 column patterns below, plus column V's 55-cell broken lookup, plus B4, T3 and T4, none of which were previously itemized in this inventory). Formulas are shown exactly as stored in the workbook. `{r}` stands for the formula's own row number. Cached values appear in the content tables above.

**Column E**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNT(H{r},K{r},N{r},Q{r})=0,"",SUM(H{r},K{r},N{r},Q{r}))
```

**Column F**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNT(I{r},L{r},O{r},R{r})=0,"",SUM(I{r},L{r},O{r},R{r}))
```

**Column G**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(F{r}="","-",IFERROR(F{r}/E{r},"-"))
```

**Column H**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!H$9:H$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!H$9:H$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!H$9:H$80,"<>")=0,"",SUMIFS('BDS IPTT'!H$9:H$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!H$9:H$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!H$9:H$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column I**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!I$9:I$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!I$9:I$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!I$9:I$80,"<>")=0,"",SUMIFS('BDS IPTT'!I$9:I$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!I$9:I$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!I$9:I$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column J**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(I{r}="","-",IFERROR(I{r}/H{r},"-"))
```

**Column K**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!K$9:K$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!K$9:K$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!K$9:K$80,"<>")=0,"",SUMIFS('BDS IPTT'!K$9:K$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!K$9:K$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!K$9:K$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column L**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!L$9:L$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!L$9:L$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!L$9:L$80,"<>")=0,"",SUMIFS('BDS IPTT'!L$9:L$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!L$9:L$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!L$9:L$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column M**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(L{r}="","-",IFERROR(L{r}/K{r},"-"))
```

**Column N**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!N$9:N$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!N$9:N$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!N$9:N$80,"<>")=0,"",SUMIFS('BDS IPTT'!N$9:N$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!N$9:N$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!N$9:N$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column O**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!O$9:O$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!O$9:O$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!O$9:O$80,"<>")=0,"",SUMIFS('BDS IPTT'!O$9:O$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!O$9:O$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!O$9:O$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column P**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(O{r}="","-",IFERROR(O{r}/N{r},"-"))
```

**Column Q**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!Q$9:Q$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!Q$9:Q$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!Q$9:Q$80,"<>")=0,"",SUMIFS('BDS IPTT'!Q$9:Q$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!Q$9:Q$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!Q$9:Q$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column R**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(COUNTIFS('BDS IPTT'!$A$9:$A$80,$A{r},'BDS IPTT'!R$9:R$80,"<>")+COUNTIFS('WAN IPTT'!$A$9:$A$80,$A{r},'WAN IPTT'!R$9:R$80,"<>")+COUNTIFS('Cross-cutting IPTT'!$A$9:$A$80,$A{r},'Cross-cutting IPTT'!R$9:R$80,"<>")=0,"",SUMIFS('BDS IPTT'!R$9:R$80,'BDS IPTT'!$A$9:$A$80,$A{r})+SUMIFS('WAN IPTT'!R$9:R$80,'WAN IPTT'!$A$9:$A$80,$A{r})+SUMIFS('Cross-cutting IPTT'!R$9:R$80,'Cross-cutting IPTT'!$A$9:$A$80,$A{r}))
```

**Column S**, rows 10-13, 15-29, 31-66 (55 cells):

```
=IF(R{r}="","-",IFERROR(R{r}/Q{r},"-"))
```

Total: 825 formulas in 15 distinct patterns (E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S), plus:

**Column V**, rows 10-13, 15-29, 31-66 (55 cells) — broken, see Header lines:

```
=IF($A{r}="","",IF(COUNTIF('[1]BDS IPTT'!$A$9:$A$80,$A{r})+COUNTIF('[1]WAN IPTT'!$A$9:$A$80,$A{r})+COUNTIF('[1]Cross-cutting IPTT'!$A$9:$A$80,$A{r})>1,"CHECK: in more than one sheet",IF(COUNTIF('[1]BDS IPTT'!$A$9:$A$80,$A{r})=1,"BDS IPTT",IF(COUNTIF('[1]WAN IPTT'!$A$9:$A$80,$A{r})=1,"WAN IPTT",IF(COUNTIF('[1]Cross-cutting IPTT'!$A$9:$A$80,$A{r})=1,"Cross-cutting IPTT","Not in CEL scope")))))
    => #VALUE! (all 55 cells)
```

**B4** (1 cell): see Header lines for the formula text; cached value quoted there.

**T3** (1 cell): `=86*4` => 344

**T4** (1 cell): `=0.05*1720` => 86

Total: 883 formulas in 18 distinct patterns.

## Conditional formatting rules

- `G22`: `AND(ISNUMBER(G22),G22<0.7)` (fill FFF8CBAD)
- `G22`: `AND(ISNUMBER(G22),G22>=0.7,G22<1)` (fill FFFFE699)
- `G22`: `AND(ISNUMBER(G22),G22>=1)` (fill FFC6E0B4)
- `J22`: `AND(ISNUMBER(J22),J22<0.7)` (fill FFF8CBAD)
- `J22`: `AND(ISNUMBER(J22),J22>=0.7,J22<1)` (fill FFFFE699)
- `J22`: `AND(ISNUMBER(J22),J22>=1)` (fill FFC6E0B4)
- `M22`: `AND(ISNUMBER(M22),M22<0.7)` (fill FFF8CBAD)
- `M22`: `AND(ISNUMBER(M22),M22>=0.7,M22<1)` (fill FFFFE699)
- `M22`: `AND(ISNUMBER(M22),M22>=1)` (fill FFC6E0B4)
- `P22`: `AND(ISNUMBER(P22),P22<0.7)` (fill FFF8CBAD)
- `P22`: `AND(ISNUMBER(P22),P22>=0.7,P22<1)` (fill FFFFE699)
- `P22`: `AND(ISNUMBER(P22),P22>=1)` (fill FFC6E0B4)
- `S22`: `AND(ISNUMBER(S22),S22<0.7)` (fill FFF8CBAD)
- `S22`: `AND(ISNUMBER(S22),S22>=0.7,S22<1)` (fill FFFFE699)
- `S22`: `AND(ISNUMBER(S22),S22>=1)` (fill FFC6E0B4)
- `G21`: `AND(ISNUMBER(G21),G21<0.7)` (fill FFF8CBAD)
- `G21`: `AND(ISNUMBER(G21),G21>=0.7,G21<1)` (fill FFFFE699)
- `G21`: `AND(ISNUMBER(G21),G21>=1)` (fill FFC6E0B4)
- `J21`: `AND(ISNUMBER(J21),J21<0.7)` (fill FFF8CBAD)
- `J21`: `AND(ISNUMBER(J21),J21>=0.7,J21<1)` (fill FFFFE699)
- `J21`: `AND(ISNUMBER(J21),J21>=1)` (fill FFC6E0B4)
- `M21`: `AND(ISNUMBER(M21),M21<0.7)` (fill FFF8CBAD)
- `M21`: `AND(ISNUMBER(M21),M21>=0.7,M21<1)` (fill FFFFE699)
- `M21`: `AND(ISNUMBER(M21),M21>=1)` (fill FFC6E0B4)
- `P21`: `AND(ISNUMBER(P21),P21<0.7)` (fill FFF8CBAD)
- `P21`: `AND(ISNUMBER(P21),P21>=0.7,P21<1)` (fill FFFFE699)
- `P21`: `AND(ISNUMBER(P21),P21>=1)` (fill FFC6E0B4)
- `S21`: `AND(ISNUMBER(S21),S21<0.7)` (fill FFF8CBAD)
- `S21`: `AND(ISNUMBER(S21),S21>=0.7,S21<1)` (fill FFFFE699)
- `S21`: `AND(ISNUMBER(S21),S21>=1)` (fill FFC6E0B4)
- `G65:G66`: `AND(ISNUMBER(G65),G65<0.7)` (fill FFF8CBAD)
- `G65:G66`: `AND(ISNUMBER(G65),G65>=0.7,G65<1)` (fill FFFFE699)
- `G65:G66`: `AND(ISNUMBER(G65),G65>=1)` (fill FFC6E0B4)
- `J65:J66`: `AND(ISNUMBER(J65),J65<0.7)` (fill FFF8CBAD)
- `J65:J66`: `AND(ISNUMBER(J65),J65>=0.7,J65<1)` (fill FFFFE699)
- `J65:J66`: `AND(ISNUMBER(J65),J65>=1)` (fill FFC6E0B4)
- `M65:M66`: `AND(ISNUMBER(M65),M65<0.7)` (fill FFF8CBAD)
- `M65:M66`: `AND(ISNUMBER(M65),M65>=0.7,M65<1)` (fill FFFFE699)
- `M65:M66`: `AND(ISNUMBER(M65),M65>=1)` (fill FFC6E0B4)
- `P65:P66`: `AND(ISNUMBER(P65),P65<0.7)` (fill FFF8CBAD)
- ... 65 more

## Cell comments

| Cell | Comment |
|---|---|
| B10 | ams: Plll.R1 |
| B12 | ams: Pll.R5 |
| B21 | ams: TechnoServe planner III.3 / III.4 |
| B22 | ams: TechnoServe planner III.3 / III.4 |
| B23 | ams: Pll.R6 & Plll.R2 |
| B24 | ams: Pll.R7 & Plll.R3 |
| H24 | ams: Pll.R7 |
| K24 | ams: Pll.R7 & Plll.R3 |
| N24 | ams: Pll.R7 & Plll.R3 |
| Q24 | ams: Pll.R7 & Plll.R3 |
| B39 | ams: Pl.3 |
| B45 | ams: PIII.6 Number of strengthened women-led cooperatives/clusters across the aquaculture value chain. CEL planner III.6: Y1 25 x4. Same 25 cooperatives/clusters as the WAN-group proxy (row 47) and I.18. LoP = Y1 x4. |
| B46 | ams: PI.11 Number of young women engaged in leadership and mentorship forums under WAN. CEL planner I.11: Y1 500 x4. Same planner line as the WAN participation indicator |
| B52 | ams: Pl.13 |
| B53 | ams: Pl.22 |
| B57 | ams: Pl.1 |
| B58 | ams: Pl.9 |
| B59 | ams: Pl.17 |
| B60 | ams: Pl.19 |
| B61 | ams: Pl.20 |
| B62 | ams: PlV.5 |
| B63 | ams: Pl.12 |
| B64 | ams: Pl.18 |
| B65 | ams: Pl.23 |
| B66 | ams: TechnoServe planner II.R3 |
| U45 | ams: Counts groups affiliated to WAN and active. Target set after the WAN group map (30 Oct 2026). The 25 strengthened groups are reported once, on OP34: never add OP15 and OP34. |
| U46 | ams: Counts unique registered women who took part in a WAN activity. Target set by 4 Dec 2026 from member registration. Forum engagements (planner I.11: 300 Q3, 200 Q4) are tracked on CI-10. |
| U52 | ams: Planner I.13/II.R5: 8 PWDs (planner says 8 PWD mentors; 1/2/2/3). Also tracked on CI-8. AIL to confirm 8 vs the 5% aim (question 6). |
| U53 | ams: Planner I.22: 6 campaigns (3 in Q3, 3 in Q4). Updated 22 Oct 2026 (was 3 in Q4 only); confirm with the Program Lead. |

B66's comment changed from "TechnoServe planner III.3 / III.4" to "TechnoServe planner II.R3"; U45, U46, U52 and U53 are new comments not present before this revision.

## Legend (font colour of indicator text)

- Applicable to CEL
- To Be Confirmed (Not directly in CEL's Consolidated Plan) — no indicator currently carries this classification; all 17 that did before this revision moved to another category (see the CEL scope column above).
- Missing indicator/new output identified (in CEL's Consolidated Plan) — renamed from "New output indicators (in CEL's Consolidated Plan)"; only OP29 and OP32 still carry it.
- Out of CEL's delivery model scope (To be confirmed by AIL) — renamed from "Not treated as WEO indicators (CEL's Consolidated Plan)"; no indicator currently carries this classification either (OP27, the only prior holder, moved to "Applicable to CEL"). The purple (FF7030A0) font on OP5 and OP24, distinct from the plain/black font used elsewhere in the "Not in CEL scope" set, is not a separate category: a parallel check on the ProFrame sheet found the same kind of font-colour variation among cells that the corrected database (commit 0599884) confirms are plainly "Not in CEL scope," which indicates this workbook applies that category's colouring somewhat inconsistently (openpyxl also cannot see colour driven by conditional formatting, only the static font) rather than meaning a fourth font variant. The "CEL scope" column above uses the text already verified against that corrected database, which is the higher-confidence source for the category label itself.
