# Leakage

**Leakage** is an increase in greenhouse-gas emissions outside a project's
boundary that is caused by the project. If planting trees on a field
pushes the previous crop onto newly cleared land elsewhere, the removal
inside the boundary is partly or wholly offset by emissions outside it.
Programmes require leakage to be assessed and, where it is material,
deducted. CarbonCreditBuy does not assess leakage; its screening statuses carry
that requirement forward.

## Definitions

- The Verra VCS Program Definitions describe leakage as the net change in
  GHG emissions occurring outside the project boundary that is measurable
  and attributable to the project activity; AFOLU methodologies
  distinguish **activity-shifting leakage** (the displaced activity moves
  elsewhere) and **market leakage** (reduced supply of a commodity raises
  production elsewhere), and include ecological leakage for some wetland
  activities (<https://verra.org/programs/verified-carbon-standard/>).
  VM0047, the afforestation, reforestation and revegetation methodology,
  specifies when leakage must be quantified and when a default deduction
  applies
  (<https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-0/>).
  Verify thresholds against the current version.
- The ICVCM Core Carbon Principles' quantification principle requires
  robust quantification that accounts for leakage
  (<https://icvcm.org/core-carbon-principles/>).
- Regulation (EU) 2024/3012 (CRCF) addresses leakage within the
  quantification criterion (Article 4) and the sustainability criterion
  (Article 7): net benefit must account for indirect effects, and
  activities must not lead to significant harm; certification
  methodologies adopted by delegated act specify how carbon farming
  activities quantify or avoid leakage
  (<https://eur-lex.europa.eu/eli/reg/2024/3012/oj>). Verify against the
  adopted methodology for the activity.
- IPCC national inventories account for all land within the national
  boundary, so leakage between parcels is captured automatically at
  national scale; this is a reason why project-level accounting needs
  explicit leakage rules while inventories do not (2006 Guidelines,
  Volume 4, Chapter 1,
  <https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html>).

## Leakage on farms

| Situation | Likely leakage type | Typical treatment |
|---|---|---|
| Cropland converted to orchard; the farmer rents other land to grow the same crop | Activity shifting | Quantified from pre-project production and displaced area; may be deducted in full |
| Agroforestry rows added to a field that stays in production | Little or none | Often a default low or zero deduction when yields are maintained |
| Grazing displaced to communal or forest land | Activity shifting | Requires monitoring of the displaced herd; can be a project killer |
| Many farms in a region switch from annual crops to tree crops | Market leakage | Default factors from the methodology, applied at project or programme level |
| Timber plantation replacing fuelwood collection from a forest | Negative leakage (benefit) | Usually not credited, but may be documented |

Smallholder orchards planted for fruit usually have low activity-shifting
leakage because the land use is the farm's own plan; the larger question
for them is additionality ([additionality.md](additionality.md)).

## What CarbonCreditBuy does and does not do

- Policy rules in `config/policies/` list "leakage assessment" among the
  requirements of crediting pathways (CCTS offsets, voluntary ARR
  methodologies, CRCF), and the screening status reflects that.
- The land-cover analysis shows the plot's own classes, not the
  surrounding landscape; detecting displacement would need
  multi-year analysis beyond the plot boundary, which the platform does
  not perform.
- The carbon estimate is a **gross** removal inside the polygon. It is not
  a net project figure and must not be read as one.

For a project developer, the practical implication is to document the
previous land use and what happened to it (the same records that the
baseline needs), to design the activity so that production is maintained
where possible, and to choose a methodology whose leakage rules fit the
system.
