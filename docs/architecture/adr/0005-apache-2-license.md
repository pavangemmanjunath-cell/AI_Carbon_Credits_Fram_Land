# ADR-0005: Apache License 2.0

- **Status:** accepted
- **Date:** 2026-10-04
- **Deciders:** project lead

## Context

The project needs a license that lets farmers' cooperatives, NGOs,
agencies, universities and companies deploy and adapt the platform, that
protects contributors and users with respect to patents, that is
compatible with the licenses of the dependencies and data we use, and
that is familiar to the institutions most likely to adopt it. The code
will be reused in contexts with very different legal capacity, from a
state agricultural department to a two-person consultancy.

The permissive candidates were MIT, BSD-3-Clause and Apache-2.0; the
copyleft candidates were GPL-3.0, AGPL-3.0 and MPL-2.0.

## Decision

AgriCarbon Atlas is licensed under the Apache License, Version 2.0
([LICENSE](../../../LICENSE)). Contributions are accepted under the same
license with a Developer Certificate of Origin sign-off
([CONTRIBUTING.md](../../../CONTRIBUTING.md)); no contributor license
agreement is required. Source files may carry an SPDX header
(`SPDX-License-Identifier: Apache-2.0`). Documentation in `docs/` is
covered by the same license unless a page states otherwise.

Data is **not** covered by this decision: every external dataset keeps its
own license and attribution requirements, which are tracked in
[../../licensing/DATA_LICENSES.md](../../licensing/DATA_LICENSES.md), and
derived outputs (reports, exports) must reproduce the required attribution
strings.

## Consequences

Positive:

- **Patent grant.** Section 3 grants every user a license to contributors'
  patents embodied in their contributions and terminates it for anyone who
  sues over the software; relevant in a field where MRV methods are
  patented.
- **Institutional familiarity.** Apache-2.0 is on every common
  allow-list (public-sector procurement, universities, corporate OSS
  policies), which lowers the barrier to adoption and to contributions
  from employees of such institutions.
- **Compatibility.** Compatible with the MIT/BSD licenses of MapLibre,
  deck.gl, three.js, React, Vite, FastAPI, Shapely, NumPy, Rasterio and
  with LGPL-3.0 (psycopg 3) when used as a library. Apache-2.0 code can be
  included in GPL-3.0 projects (one-way compatibility), so downstream
  copyleft projects can reuse it.
- **Attribution.** Section 4 requires preservation of notices and the
  `NOTICE` file, which gives the project a lightweight mechanism to carry
  data and software attributions downstream.

Negative:

- No copyleft: a company can build a closed service on the platform
  without contributing back. We accept this; the mission is adoption and
  the honest presentation of estimates, and the trademark and governance
  documents, not the license, protect the project's name.
- Apache-2.0 is longer and less familiar to individual developers than
  MIT. Mitigated by this ADR and a clear `LICENSE` file.

## Alternatives considered

- **MIT / BSD-3-Clause.** Simpler, but no explicit patent grant.
- **GPL-3.0 / AGPL-3.0.** Would guarantee that modifications to hosted
  deployments are shared (AGPL), but would deter the agencies and
  cooperatives we most want to deploy it, and complicate reuse of our
  engines inside other tools.
- **MPL-2.0.** File-level copyleft is a reasonable middle ground, but
  less familiar to the target institutions and offers no advantage over
  Apache-2.0 for a project whose value is in adoption and in verified
  configuration rather than in code secrecy.
- **Open data licenses (CC BY 4.0, ODbL) for `config/`.** Rejected for
  simplicity: configuration is part of the software. Where a configuration
  value is a verbatim excerpt from a licensed table, the entry's `source`
  field and `DATA_LICENSES.md` carry the attribution.

## Revisit when

Only with the thirty-day public comment period required for guardrail
changes in [GOVERNANCE.md](../../../GOVERNANCE.md), since relicensing
affects every contributor.
