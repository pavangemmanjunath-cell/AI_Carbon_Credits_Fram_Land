# Farmer data

This page is written for the people whose land the platform describes and
for the organizations that deploy it on their behalf. It explains, in
plain terms, what CarbonCreditBuy collects, why, who can see it and what control
you keep. Deployers should adapt it into their own privacy notice; the
legal obligations differ between India's Digital Personal Data Protection
Act, 2023 (<https://www.meity.gov.in/data-protection-framework>), US
state privacy laws, and the EU General Data Protection Regulation
(<https://eur-lex.europa.eu/eli/reg/2016/679/oj>), and this page is not
legal advice.

## What is collected and why

| Data | Why it is needed | Required? |
|---|---|---|
| The boundary you draw | To compute area, read satellite and land-cover data for that place, and derive the climate zone | Yes — nothing works without it |
| A name for the plot | So you can find it again | Optional; avoid personal names |
| Species, tree count, planting year, survival, measurements | To estimate carbon | Species, count and year are needed; the rest improves confidence |
| Country/region/district | To pick units, currency, programmes and statistics | Derived automatically from the boundary |
| Language preference | To show the interface in your language | Stored in your browser only |
| An API key or account (if the deployment uses one) | To make sure only you can see your plots | Deployment-dependent |

CarbonCreditBuy does **not** ask for your name, phone number, land record
numbers (such as survey or khata numbers), bank details or ownership
documents. A deployer who adds such fields takes on the obligations that
come with them and must say so in their notice.

## Who can see what

- **You** see everything about your plots, including the exact boundary.
- **Other users** see nothing about your plots unless you share a report
  or a link. Shared reports show your plot's location only as a
  district-scale point (rounded to a 0.05° grid, roughly 5 km) unless you
  explicitly include the exact boundary.
- **The operator** of the deployment can access the database and caches
  that contain your boundary; the operator's privacy notice must name who
  that is and how access is controlled.
- **Data providers** (satellite, climate, soil and map services) receive
  the area or point being looked up, without your identity, when the
  server fetches data for your plot
  ([privacy-design.md](privacy-design.md)).
- **An AI provider** receives nothing unless the operator has enabled the
  optional explanation feature, and then only summary indicators (area,
  counts, index values, the estimate range), never the boundary.
- **Governments, registries, buyers**: nothing is sent to any programme,
  registry or market. Applying to a programme is a separate step you take
  with your own documents; CarbonCreditBuy can produce a report you may choose
  to attach.

## What the results are and are not

The carbon figures are estimates with a range, not credits and not money
you will receive ([../concepts/carbon-credit-vs-estimate.md](../concepts/carbon-credit-vs-estimate.md)).
The programme list is a screening that says what you would need to
investigate, not a decision that you qualify. Market values are
scenarios, not offers. Please do not sign agreements, take loans or
change land use on the basis of CarbonCreditBuy alone; use it to ask better
questions of an advisor or a programme office.

## Your controls

| Control | How |
|---|---|
| See all data stored about a plot | `GET /plots/{id}` and the related endpoints; the "Export" button in the workspace downloads a JSON bundle |
| Delete a plot and everything derived from it | `DELETE /plots/{id}` or the "Delete" button; deletion covers inventories, estimates, reports and cached rasters ([data-retention.md](data-retention.md)) |
| Keep the boundary out of a report | Leave "include exact boundary" unchecked (default) |
| Share without location | Use the Simulation Lab share link, which carries species, counts and years only |
| Use without any network | Ask the deployer for demo mode or an offline workshop build |
| Ask questions or complain | The deployer's contact in their privacy notice; for the open-source project itself, [SECURITY.md](../../SECURITY.md) for privacy defects |

## For cooperatives, NGOs and advisors deploying CarbonCreditBuy

You are the data controller for your farmers' plots. Before going live:
set `ATLAS_API_KEYS` or an authentication layer; set retention defaults;
publish a notice naming the operator, the data providers you configured,
whether the AI explanation is enabled and with which provider, and how to
request export or deletion; obtain consent before entering a plot on a
farmer's behalf; and never publish a map of exact boundaries, even with
consent, without a specific purpose and a way to withdraw. Treat cached
rasters and database backups as personal data in your retention schedule.
