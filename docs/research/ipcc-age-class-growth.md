# IPCC natural-forest growth by age class

Research of 2026-10-05 for the "Tree age" dashboard. The question: what do the IPCC Tier 1 defaults say about the
above-ground growth of natural forest in the "up to 20 years" and "over 20 years" age classes, by ecological zone and
continent?

**Result: the official Table 4.9 values were NOT obtained, so no official value is recorded as verified.** The 2006
Guidelines and the 2019 Refinement PDFs could be opened only as far as about page 4.27 (the fetch tool truncates the
document), and Table 4.9 lies beyond that point in both. Nothing below may be copied into `config/` as an IPCC value
until a maintainer has read the cell in the official table. The values that are given come from a secondary source and
from an earlier IPCC publication, and are labelled that way.

## What was and was not obtained

| Item | Outcome |
|---|---|
| 2006 Guidelines, Vol. 4 Ch. 4, Table 4.9 "Above-ground net biomass growth in natural forests" | Listed in the contents (the fetch tool read it as printed page 4.57; not confirmed). Table body not retrieved: the PDF text ends at about page 4.27. No values. |
| 2019 Refinement, Vol. 4 Ch. 4, Table 4.9 | Listed in the contents on page 4.4. Table body not retrieved: the PDF text ends during Table 4.8 on page 4.27. No values. |
| IPCC Emission Factor Database (EFDB) pages for 4.A.1 and 3.B.1.a | Opened; no record of the table was returned. |
| Other copies of Table 4.9 (a UNFCCC training PDF, an ISFL guidance note, ResearchGate's copy of the chapter) | Not usable: no values were returned, or access was refused (HTTP 429 for ResearchGate). |
| 2019 Refinement, Table 4.4 root-to-shoot ratio R | Retrieved from the official PDF (pages 4.18 to 4.21) through the summarising fetch tool. Machine-read; four rows re-read verbatim; see below. |
| 2006 Guidelines, Table 4.4 | Not retrieved (the 2006 PDF text ends before it). |
| 2003 Good Practice Guidance for LULUCF, Table 3A.1.5 (page 3.163) | Opened. Africa values returned; Asia and America not returned. An earlier publication, not the 2006 table. |
| Requena Suarez et al. 2019, Table 1 | Retrieved from the open-access PMC copy (the Wiley page returned HTTP 403); values below. A secondary source for tropical and subtropical zones only. |

## Where the 20-year split comes from

- The IPCC Tier 1 default growth rates for natural forest have long had two age classes. The 2003 Good Practice
  Guidance for LULUCF presents them in Table 3A.1.5 (page 3.163) with columns for "≤20 years" and ">20 years". The 2006
  Guidelines carry the same split in Table 4.9.
- Requena Suarez et al. (2019) describe it in these words: "IPCC 2006 default ∆AGB rates divide natural forest stands
  into above and below 20 years, which is a broad classification that does not account for known age-related variation
  in secondary forests". They also say the 2006 defaults "come from a handful of studies, provide no uncertainty
  indications and do not distinguish between older secondary forests and old-growth forests".
- That 20-year boundary is the reason `config/tree-age/rules.yaml` starts its "mature" age class at 21 years.
  The 50-year and 75-year boundaries come from Indian rules, not from the IPCC (see
  [tree-age-carbon-rules.md](tree-age-carbon-rules.md)).

## Secondary source: refined rates for tropical and subtropical forest

Requena Suarez, D., Rozendaal, D. M. A., De Sy, V., Phillips, O. L., Alvarez-Davila, E., Anderson-Teixeira, K.,
Araujo-Murakami, A., et al. (2019). Estimating aboveground net biomass change for tropical and subtropical forests:
refinement of IPCC default rates using forest plot data. *Global Change Biology* 25(11): 3609-3624.
DOI [10.1111/gcb.14767](https://doi.org/10.1111/gcb.14767). Open-access copy:
<https://pmc.ncbi.nlm.nih.gov/articles/PMC6852081/>.

The paper says it was prepared "as part of the 2019 Refinement to the 2006 IPCC Guidelines" and that it refines the 2006
defaults "in tropical and subtropical ecological zones". **It does not state that its Table 1 was adopted unchanged as
the Refinement's Table 4.9**, so these numbers are not the IPCC table and must not be presented as such. It uses three
age classes in place of the two IPCC classes: younger secondary forest (YS, up to 20 years), older secondary forest (OS,
over 20 and up to 100 years) and old-growth forest (OG, no record of disturbance for 100 years or more). Its data are,
in the abstract's words, "176 chronosequences in secondary forests and 536 permanent plots in old-growth and
managed/logged forests located in 42 countries in Africa, North and South America and Asia".

Mean above-ground net biomass change, as printed in Table 1 in Mg ha⁻¹ yr⁻¹. The same unit as the IPCC's t d.m. ha⁻¹
yr⁻¹ only if the paper's biomass is dry matter, which the fetched text did not show; confirm in the paper. Figures in
brackets are the number of chronosequences or permanent plots (n), single read only.

| Zone | Continent | ≤20 y (YS) | >20 y up to 100 y (OS) | Old-growth (OG) | Source / page | Verified |
|---|---|---|---|---|---|---|
| Tropical rainforest | Africa | 7.6 (15) | 3.5 (10) | 1.3 (77) | Requena Suarez 2019, Table 1; the three means also appear in the abstract | No (secondary source; means match the abstract) |
| Tropical rainforest | North and South America | 5.9 (42) | 2.3 (39) | 1.0 (248) | Table 1 | No (secondary source; re-read once) |
| Tropical rainforest | Asia | 3.4 (7) | 2.7 (2) | 0.7 (66) | Table 1 | No (secondary source; re-read once) |
| Tropical moist forest | Africa | 2.9 (2) | 0.9 (2) | not given | Table 1 | No (secondary source; single read) |
| Tropical moist forest | North and South America | 5.2 (21) | 2.7 (18) | 0.4 (19) | Table 1 | No (secondary source; single read) |
| Tropical moist forest | Asia | 2.4 (2) | not given | not given | Table 1 | No (secondary source; re-read once) |
| Tropical dry forest | North and South America | 3.9 (6) | 1.6 (5) | not given | Table 1 | No (secondary source; re-read once) |
| Tropical mountain system | Africa | 5.5 (2) | not given | not given | Table 1 | No (secondary source; single read) |
| Tropical mountain system | North and South America | 4.4 (6) | 1.8 (4) | 0.5 (6) | Table 1 | No (secondary source; single read) |
| Tropical mountain system | Asia | 2.9 (5) | 1.1 (5) | -0.7 (5) | Table 1 | No (secondary source; re-read once) |
| Subtropical humid forest | Asia | 2.5 (4) | 1.0 (8) | not given | Table 1 | No (secondary source; re-read once) |
| Subtropical mountain system | Asia | 2.5 (2) | 0.5 (12) | not given | Table 1 | No (secondary source; re-read once) |

What this table shows and does not show:

- Rainforest ranges stated in the abstract: YS 3.4 (Asia) to 7.6 (Africa); OS 2.3 (North and South America) to 3.5
  (Africa); OG 0.7 (Asia) to 1.3 (Africa) Mg ha⁻¹ yr⁻¹. Growth falls steeply with stand age in every row that
  reports all three classes, which is the stand-level pattern behind the 20-year split.
- Several cells rest on two sites (n = 2) and, as printed in the paper's Table 1, some 95 percent confidence intervals
  include zero, so these are not tight numbers.
- The paper has no rows for subtropical dry forest or for any temperate or boreal zone, and it does not split Asia into
  continental and insular. Those requested zones remain empty. Old-growth forest is a third class that the IPCC two-class
  Table 4.9 did not have, so a ">20 y" column in the IPCC layout may differ from OS here.
- Stand-level growth falling with age does not contradict Stephenson et al. (2014), who find that the growth of an
  individual large tree keeps increasing with its size; the two statements are about different scales. See
  [tree-age-carbon-rules.md](tree-age-carbon-rules.md).

## Earlier IPCC publication: 2003 Good Practice Guidance, Table 3A.1.5 (Africa only, machine-read)

Annex 3A.1 of the 2003 Good Practice Guidance for LULUCF, page 3.163, gives the average annual above-ground biomass
increment in natural regeneration, by rainfall class, for the two age classes. The fetch tool returned only the Africa
rows and described the Asia, America, temperate and boreal sections without cell values, so they are not recorded here.
Values below are in t ha⁻¹ yr⁻¹ as returned. **This is a different, older table than the 2006 Table 4.9. It was read
once through the summarising tool and not re-read, so it is not verified and must not be used as the 2006 default.**

| Zone (Africa, rainfall class) | ≤20 y | >20 y | Source / page | Verified |
|---|---|---|---|---|
| Wet (R above 2000 mm per year) | 10.0 | 3.1 | GPG-LULUCF 2003, Table 3A.1.5, p. 3.163 | No (machine-read, single read) |
| Moist with short dry season | 5.3 | 1.3 | same | No (machine-read, single read) |
| Moist with long dry season | 2.4 | 1.8 | same | No (machine-read, single read) |
| Dry | 1.2 | 0.9 | same | No (machine-read, single read) |
| Montane moist | 5.0 | 1.0 | same | No (machine-read, single read) |
| Montane dry | 2.0 | 1.5 | same | No (machine-read, single read) |

## 2019 Refinement, Table 4.4: ratio of below-ground to above-ground biomass (R)

Table title as printed: "Ratio of below-ground biomass to above-ground biomass (R) [tonne root d.m. (tonne shoot
d.m.)⁻¹]", pages 4.18 to 4.21, with the note that the Forest Resources Assessment (2015) defines the ecological zones.
The text was read from the official PDF through the summarising tool. Four rows were re-read verbatim and agreed:
Tropical Rainforest, Asia, natural, up to 125: 0.207 (SD 0.072); Tropical Moist, Asia, natural, up to 125: 0.323 (SD
0.073); Subtropical Humid, Asia, natural, up to 125: 0.230 (default, plus or minus 90 percent); Tropical Dry, Asia,
natural, up to 125: 0.440 (default, plus or minus 90 percent). **Every other row is machine-read and not re-read.**
The columns are the above-ground biomass class in t ha⁻¹ (up to 125, over 125) for natural forest unless marked planted.
"SD" is the standard deviation given; "default" means a plus or minus 90 percent default uncertainty.

| Zone | Continent | Origin | R, AGB up to 125 | R, AGB over 125 | Verified |
|---|---|---|---|---|---|
| Tropical Rainforest | Africa | natural | 0.825 (default) | 0.532 (default) | No (machine-read) |
| Tropical Rainforest | N and S America | natural | 0.221 (SD 0.036) | 0.221 (SD 0.036) | No (machine-read) |
| Tropical Rainforest | N and S America | planted | 0.170 (SD 0.11) | 0.170 (SD 0.11) | No (machine-read) |
| Tropical Rainforest | Asia | natural | 0.207 (SD 0.072) | 0.212 (SD 0.077) | Partly (the up-to-125 value re-read verbatim) |
| Tropical Rainforest | Asia | planted | 0.325 (SD 0.025) | not listed | No (machine-read) |
| Tropical Moist | Africa | natural | 0.232 (default) | 0.232 (default) | No (machine-read) |
| Tropical Moist | N and S America | natural | 0.2845 (SD 0.061), see note | 0.284 (SD 0.061) | No (machine-read) |
| Tropical Moist | Asia | natural | 0.323 (SD 0.073) | 0.246 (SD 0.036) | Partly (the up-to-125 value re-read verbatim) |
| Tropical Dry | Africa | natural | 0.332 (SD 0.247) | 0.379 (SD 0.040) | No (machine-read) |
| Tropical Dry | N and S America | natural | 0.334 (SD 0.040) | 0.379 (SD 0.040) | No (machine-read) |
| Tropical Dry | Asia | natural | 0.440 (default) | 0.379 (SD 0.040) | Partly (the up-to-125 value re-read verbatim) |
| Tropical Mountain | N and S America | natural | 0.348 (default) | 0.283 (SD 0.16) | No (machine-read) |
| Tropical Mountain | N and S America | planted | 0.205 (default) | not listed | No (machine-read) |
| Tropical Mountain | Asia | natural | 0.322 (SD 0.084) | 0.345 (SD 0.280) | No (machine-read) |
| Subtropical Humid | Africa | natural | 0.232 (default) | 0.232 (default) | No (machine-read) |
| Subtropical Humid | N and S America | natural | 0.175 (default) | 0.284 (default) | No (machine-read) |
| Subtropical Humid | Asia | natural | 0.230 (default) | 0.246 (default) | Partly (the up-to-125 value re-read verbatim) |
| Subtropical Dry | N and S America | natural | 0.336 (default) | 0.352 (SD 0.047) | No (machine-read) |
| Subtropical Dry | Asia | natural | 0.440 (SD 0.184) | 0.440 (SD 0.184) | No (machine-read) |

Note on the Tropical Moist, N and S America row: the tool returned "0.2845" for the up-to-125 class and 0.284 for the
over-125 class. The four-decimal figure looks like a transcription artefact; read the cell in the PDF.

Temperate rows as returned (species group in brackets; all machine-read, not re-read; defaults carry plus or minus 90
percent unless marked):

| Zone | Continent | Natural, up to 125 | Natural, over 125 | Planted rows returned |
|---|---|---|---|---|
| Temperate oceanic | Europe | conifer 0.359 | other broadleaf 0.172 (other broadleaf, all size classes, natural or planted: 0.192) | conifer over 125: 0.206; conifer all sizes: 0.359 (SD 0.145); Quercus up to 125: 1.400 |
| Temperate oceanic | N and S America | conifer 0.337; other broadleaf 0.466 | conifer 0.338; other broadleaf 0.190 | conifer over 125: 0.203 |
| Temperate continental | Europe | not returned | Quercus 0.477 | conifer up to 125: 0.340 |
| Temperate continental | N and S America | other broadleaf 0.481 | other broadleaf 0.277 | conifer up to 125: 0.237 |

Rows for temperate oceanic Oceania and temperate continental mountain Asia (0.224 to 0.307) were also returned. Boreal
rows (coniferous, tundra woodland and mountain systems): up to 75 t ha⁻¹, 0.390 (range 0.23 to 0.96); over 75 t ha⁻¹,
0.240 (range 0.15 to 0.37). Subtropical steppe rows (1.338 and 2.158) were returned as well and are not used by 
CarbonCreditBuy.

## Relation to the repository's parameter file (read only)

`config/methodologies/ipcc-2006-tier1.yaml` was read, not edited. It already marks both groups `pending`.

- **Root-to-shoot ratios.** The file attributes them to "IPCC 2006 Vol.4 Ch.4 Table 4.4" with `verification_status:
  pending`. This research could not open the 2006 table, so it can neither confirm nor refute those cells. It can say
  that the 2019 Refinement table, as read, is structured differently (by continent, origin and species group, with
  classes of up to 125 and over 125 t ha⁻¹) and has different values for the tropical zones. For example, tropical moist
  forest in Asia reads 0.323 and 0.246 in 2019, against 0.20 and 0.24 in the file; tropical rainforest reads 0.207 to
  0.825 by continent, against 0.37. The file's boreal pair (0.39 and 0.24) equals the 2019 boreal rows as read. Which
  edition the model should follow is a maintainer decision; the choice and the cell-by-cell check need recording.
- **Above-ground growth, up to 20 years.** The file labels its values "young plantations/stands" and cites Tables 4.10
  and 4.12 as working values. Per the 2006 contents, Table 4.10 is "Above-ground net biomass growth in tropical and
  sub-tropical forest plantations", a plantation table and not the natural-forest Table 4.9 that this note is about;
  Table 4.12 was not identified. Plantation growth and natural-forest growth are different quantities and must
  not be mixed. For orientation only: the file's working values for tropical wet (10.0), tropical moist (7.0) and
  subtropical humid (7.0) are higher than the refined natural secondary-forest means above (rainforest 3.4 to 7.6, moist
  2.4 to 5.2, subtropical humid Asia 2.5), which is plausible for plantations but is not a verification of either.

## How to complete the verification

1. Open the official PDFs locally, not through a summarising tool:
   [2006 Vol. 4 Ch. 4](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/4_Volume4/V4_04_Ch4_Forest_Land.pdf) and
   [2019 Refinement Vol. 4 Ch. 4](https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/4_Volume4/19R_V4_Ch04_Forest%20Land.pdf).
2. Copy Table 4.9 (and Tables 4.4 and 4.10) cell by cell with the printed page number, and record who checked it and
   when, as the parameter file's rules require.
3. Compare the 2019 Table 4.9 with Requena Suarez et al. Table 1 for the tropical and subtropical zones, and take the
   temperate and boreal zones, which the paper does not cover, only from the Refinement table.
4. Only then change `verification_status` in `config/methodologies/ipcc-2006-tier1.yaml`; the production-mode
   data-quality test is meant to refuse `pending` parameters until then.

## Sources

All accessed on 2026-10-05; the PDF and web pages were read through a summarising fetch tool, so every number above
carries the caveat stated beside it.

- IPCC 2006 Guidelines, Vol. 4 Ch. 4 Forest Land: <https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/4_Volume4/V4_04_Ch4_Forest_Land.pdf>
- IPCC 2019 Refinement, Vol. 4 Ch. 4 Forest Land: <https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/4_Volume4/19R_V4_Ch04_Forest%20Land.pdf>
- IPCC Good Practice Guidance for LULUCF (2003), Annex 3A.1 data tables: <https://www.ipcc-nggip.iges.or.jp/public/gpglulucf/gpglulucf_files/Chp3/Anx_3A_1_Data_Tables.pdf>
- IPCC Emission Factor Database, 4.A.1: <https://www.ipcc-nggip.iges.or.jp/EFDB/find_ef.php?ipcc_code=4.A.1&ipcc_level_1=4&ipcc_level_2=A&ipcc_level_3=1&ipcc_level_4=0>
- Requena Suarez et al. 2019, Global Change Biology 25(11): 3609-3624, DOI 10.1111/gcb.14767; open-access copy: <https://pmc.ncbi.nlm.nih.gov/articles/PMC6852081/>
