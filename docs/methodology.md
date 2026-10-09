# Methodology

**Tier 1 (age and area).** Annual change in biomass carbon follows the IPCC 2006 gain–loss method
(Vol. 4, Ch. 2 and 4): `ΔC = A · G_w · m_sp · f_d · s · f_t(a) · (1 + R) · CF`, converted with `CO₂e = C · 44/12`.
Growth `G_w`, root-to-shoot ratio `R` and carbon fraction `CF` come from `config/` with a source and a
`verification_status`.

**Tier 2 (measured trunk).** Above-ground biomass uses Chave et al. (2014) equation 4,
`AGB = 0.0673 (ρ D² H)^0.976`, with wood density from the Global Wood Density Database.

**Uncertainty.** Every carbon output is `low / central / high` with unit, confidence, model and methodology.

**Verification gate.** Parameters are `verified`, `pending` or `assumption`. Production mode refuses `pending`.

**What the numbers are not.** Estimates are not carbon credits (`certified: false`); an LLM never computes a number.

Details: [architecture/carbon-engine.md](architecture/carbon-engine.md),
[research/validation/README.md](../research/validation/README.md),
[benchmarks/](../benchmarks/README.md).
