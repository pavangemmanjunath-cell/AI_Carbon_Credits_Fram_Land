# Tree age

The **Tree age** page answers two questions about trees you already have, or trees you are only planning:

1. How much carbon do trees of this age hold, and how much more do they take in each year?
2. Which programmes and laws treat trees of this age differently?

You do not need to mark your land first. Open **Tree age** in the left menu, under **INSIGHTS**, fill in a few boxes,
and the answer changes as you type. On a phone, tap **Menu** first.

> **Read this first.**
>
> - The numbers are a scenario estimate. The page says: "Scenario estimate only. This is not an issued carbon credit."
> - The rules are screening information, not legal advice. Rules change. Confirm with the responsible authority
>   before you act.
> - Old trees can hold a lot of carbon and still earn no carbon credits. Credits reward carbon that is added by new
>   planting, or loss that is avoided. They do not reward carbon that already stands.

![The Tree age page for 25 mango trees that are 80 years old on a farm in Haryana, with the three result cards, the carbon chart, the credit outlook box and the first rule cards.](../images/screenshots/10-tree-age.png)

*The numbers in the picture are examples. The grey tag on the first rule card reads "Payment" in this picture. The app
now calls that tag **Incentive scheme**.*

- [Fill in your trees](#fill-in-your-trees)
- [Read the results](#read-the-results)
- [Credit outlook](#credit-outlook)
- [Rules for trees of this age](#rules-for-trees-of-this-age)
- [Planning new trees](#planning-new-trees)
- [Share your numbers](#share-your-numbers)
- [What this page does not do](#what-this-page-does-not-do)
- [If something goes wrong](#if-something-goes-wrong)
- [Learn more](#learn-more)

## Fill in your trees

The **Your trees** card is on the left. On a phone it sits above the results. Whatever you change goes straight into
the address of the page, and the results update after a short pause. A small **Updating…** tag shows while the page
recalculates.

| Box | What to enter |
| --- | --- |
| **Country** | India, United States, or a country from the **European Union** group. The page starts with your **Default country** from **Settings**. If that is the whole European Union, it starts with India, because this page needs one country |
| **State or region** | Shown for India, the United States and Germany. Choose yours, or keep **Not sure**. Some rules apply in one state only, such as Haryana's pension or Karnataka's tree law. In Germany, choosing Berlin switches on Berlin's tree ordinance |
| **Where do the trees stand?** | **Farm**, **Town or city** or **Forest**. It matters: some rules cover only town trees, and some only forest |
| **Species** | The species listed for your country. The full list, with the growth numbers, is in **Settings**, then **Tree species reference** |
| **Age of the trees (years)** | A slider from 0 to 150 and a box that takes up to 300. "Use 0 if you are planning new trees." |
| **Number of trees** | From 1 to 1,000,000. It starts at 25 |
| **Trunk girth at chest height (cm)** (optional) | From 10 to 2000. "Wrap a tape around the trunk 1.3 m (about 4 ft) above the ground and read the distance around." Switched off at age 0: "A tree that is only planned has no trunk yet." |
| **Copy link** | Copies the address of the page. See [Share your numbers](#share-your-numbers) |

The page starts with age 30, 25 trees and **Farm**. If you type something it cannot use, a message appears under the
box: "Enter a number.", "Use digits only.", "Use a whole number.", "The smallest value is …" or "The largest value is …".

Measure the trunk when you can. It makes the estimate better, as [explained below](#how-was-this-estimated).

## Read the results

### The three cards

| Card | What it tells you |
| --- | --- |
| **Carbon stored now** | "All the carbon these trees have taken in so far." In tCO₂e, with a low to high range under the number |
| **Carbon removed per year now** | "How much more they take in each year at this age." In tCO₂e per year, with a low to high range |
| **Age class** | **Young**, **Mature**, **Old** or **Veteran**, with the years it covers: 0–20, 21–49, 50–74 and 75+ |

Two things to know:

- The age classes are labels chosen by this project to make results easier to read. They are not legal categories.
  The limits follow the rules the page knows about. Twenty years is where the IPCC splits young and older natural
  forest growth. Fifty years is the heritage-tree age reported for Maharashtra, and 75 years is the age in Haryana's
  pension scheme. Both of those rest on news reports. See
  [the research note](../research/tree-age-carbon-rules.md#age-classes-and-why-they-are-where-they-are).
- The numbers are ranges. Read the whole range, not only the big number.

For example, for 25 mango trees that are 80 years old on a farm in Haryana, the screenshot above shows about
56.5 tCO₂e stored (low to high 39.6 to 73.5), about 0.66 tCO₂e removed per year (0.46 to 0.86), and the age class
**Veteran**.

### The chart

**Carbon stored as the trees age** shows how the carbon in these trees builds up over the years.

- The dark line is the central estimate. The shaded band runs from the low to the high estimate.
- A dashed line marks **Today**, the age you entered.
- The curve starts at age 0 and runs to at least 20 years past today's age, and at least to age 40.
- Under the chart, the legend names the line, the band and the marker. The vertical axis is tCO₂e.
- Screen readers get the same numbers as a table, **Carbon stored by age**.

If you give a trunk measurement, the page adds: "Your trunk measurement gives the numbers above. The curve is based on
age alone, so the two can differ a little."

### How was this estimated?

Open **How was this estimated?** under the chart. It lists:

| Row | What it says |
| --- | --- |
| **Method** | "From the age of the trees only" or "From your trunk measurement" |
| **Confidence** | **Low**, **Medium** or **High** |
| **Climate zone** | The climate zone the app assumed, with where it comes from. It is the usual zone for your country, because this page does not know your plot |
| **Per tree** | "About … kg CO₂e stored, … kg CO₂e added per year" |
| **Growth numbers used** | How many numbers the calculation used, and how many of them are not yet verified, for example "… numbers, 2 not yet verified" |

Short notes from the calculation follow, for example when your trunk is outside the range the equation was made for.

**From the age of the trees only.** The app pretends that your trees were planted that many years ago. It adds up how
much carbon this species would have taken in each year since, with the same growth numbers as the plot estimate. The
number of trees you enter is counted as alive today. Nothing about your actual trees is measured, so the confidence is
always **Low**, and the range is wide (plus or minus 30 %).

**From your trunk measurement.** The app turns the girth into a trunk width (the girth divided by π) and uses a
standard tree-size equation (Chave and others, 2014) with the wood density of the species. Roots are added with an IPCC
ratio. On this path, **Carbon removed per year now** is the carbon stored divided by the age, an average over the
tree's whole life. It understates the yearly growth of a young tree and overstates it for an old one. The notes in
the fold-out say so.

What the estimate leaves out:

- It counts only living tree material, above and below ground. Soil, leaf litter, dead wood, harvest and loss are not
  counted.
- Growth after maturity uses a factor that the project assumed. The page does not claim that old trees stop growing.
- It treats your trees as one stand at the usual density for the species.

If the row **Growth numbers used** says that some numbers are "not yet verified", those growth numbers still wait for a
check against the published tables. See [what "pending" means](faq.md#what-does-pending-mean-next-to-a-value). A
production installation can refuse the estimate until they are verified.

## Credit outlook

A coloured box above the rules gives one sentence on whether trees like yours usually earn carbon credits. Screen
readers call it **Credit outlook**. It is always followed by "Scenario estimate only. This is not an issued carbon
credit."

| Your trees | What the box says in English |
| --- | --- |
| Planned (age 0) | "Newly planted trees can earn removal credits only through a project that meets a programme's rules; nothing is stored or creditable until they are planted and verified, and an estimate is never a credit." |
| Already standing, and no rule that applies gives them a route | "Trees that already stand usually do not earn removal credits under the rules that apply here, because credits reward carbon added by new planting, not carbon already stored." |
| Already standing, and at least one rule in force names a route | "Existing trees can qualify only under specific conditions in …; confirm with the programme, because an estimate is never a credit." If the route rests on a rule that is not yet verified, the sentence adds "(this rests on a rule not yet confirmed from a primary source)" |

The box never says that your trees are eligible. Only the programme itself can decide that.

## Rules for trees of this age

The page checks your country, state or region, setting and age against a list of real programmes and laws. The
heading says: "Programmes and laws that treat trees differently by age. This is screening information, not legal
advice."

### What the rules mostly say

- Carbon credit standards reward new, additional removals or avoided loss. They do not pay for carbon that old trees
  already hold. A 60-year-old tree stores a lot of carbon, but in the methods the project reviewed, that stock is the
  starting point, not a credit.
- Existing trees are protected or rewarded mainly in other ways: laws that require permission to fell a tree,
  heritage-tree laws, replanting rules, and, in Haryana, a pension for very old trees.
- Only two of the 22 rules use the age of a tree as a test (Haryana at 75 years and Maharashtra's heritage trees at
  50 years), and both are not yet verified. Most protection rules turn on trunk size or species.

### How to read a rule card

| Part of the card | What it means |
| --- | --- |
| A badge | What the rule means for trees like yours (see the next table) |
| A grey tag | The kind of rule: **Carbon credits**, **Incentive scheme**, **Tree protection**, **Replanting** or **Background** |
| An amber tag, if any | **Example — check your own city's rules**, **Proposed, not yet in force**, **Replaced by a newer rule** or **Status unclear** |
| The name and who made the rule | For example "Forest and Wildlife Department, Government of Haryana" |
| A short summary | In plain words |
| An amount, if the source states one | For example "₹3,000 per tree per year (as of 2026-07)" |
| **Verified source** or **Not yet verified — check with the authority** | Whether the project has read the rule in a primary source. Press reports alone are not enough |
| **Sources** | Links that open in a new tab |

| Badge | What it means |
| --- | --- |
| **Not eligible** | The rule gives no credits for trees that already stand |
| **Conditional** | Trees can qualify only under specific conditions. Check with the programme |
| **Protected** | A law protects trees like these. Felling usually needs permission, and often replanting |
| **Payment** | A scheme pays something for trees like these |
| **Eligible** | A rule may allow credits. Only the programme can confirm it. None of the rules on the page today says this |
| **Not applicable** | The rule is about trees that already stand, and yours are only planned |
| **Unknown** | The page cannot tell |

A payment such as Haryana's pension is other farm income. It is never added to a carbon value.

### Which rules show first

The rules that apply to your trees come first, as full cards. The others sit under **Other rules in** and your
country, with a number. Each of them gives the reason it does not apply, for example "Only in Karnataka (IN-KA)",
"Needs trees aged 75 years or more", "Only for trees in forests" or "Municipal example for Portland (US-OR); check
your own city's rules".

If nothing applies, the page says: "No rule matches these trees. The other rules we checked are listed below."

The page has no box for your city. So the city examples (Portland and Los Angeles) always sit under **Other rules**.
Berlin is the exception: it applies when you choose Berlin as your state. A city example only shows the kind of rule
that may exist. Look up the rules of your own city.

At the bottom: "Screening information only — not legal advice. Rules change; confirm with the responsible authority
before acting. Scenario estimate only. This is not an issued carbon credit."

The rule names and summaries are in English, whichever language you chose.

### Rules the page can show

This list follows the rules file, version 0.1.0 (updated 5 October 2026). Three of the 22 rules are not yet verified.
On a production installation, rules that are not yet verified may be held back and not shown at all. The page always
shows the current list.

**Worldwide** (shown for every country)

| Rule | In short | Outcome for trees that already stand | Source |
| --- | --- | --- | --- |
| ICVCM Core Carbon Principles 5–7 | A credit may only count removals that would not have happened without carbon revenue. Growth that standing trees would make anyway is not creditable on its own | **Conditional** | Verified |
| Verra VM0047, Afforestation, Reforestation and Revegetation, v1.1 | Credits trees that a project plants or restores. The carbon already stored in existing trees is measured as a starting stock and is not credited | **Not eligible** | Verified |
| Gold Standard Land Use & Forests Activity Requirements (A/R) v1.2.1, with A/R methodology v2.1 | Covers only planting on land that was not forest 10 years before the project start, so trees that already stand earn no credits | **Not eligible** | Verified |

#### India

| Rule | In short | Outcome | Source |
| --- | --- | --- | --- |
| Green Credit Programme: tree plantation (Green Credit Rules, 2023; revised 29 August 2025) | Green Credits for tree plantation are issued only for restoring degraded forest land of at least 5 ha under a State or UT Forest Department. Existing trees on a farm or in a town do not qualify. Green Credits and carbon credits are separate mechanisms | **Not eligible** | Verified |
| Carbon Credit Trading Scheme offset mechanism: BM FR05.002, afforestation and reforestation of lands except wetlands, v1.0 | India's approved carbon credit method for tree planting. It credits net removals above a baseline that already counts the tree biomass standing before the project, so existing trees earn nothing on their own | **Not eligible** | Verified |
| Pran Vayu Devta Pension Scheme (Haryana) | Pays the custodian of a living tree that is about 75 years old or more, and stands outside forest land, a yearly pension. Press reports give ₹3,000 per tree in 2025 and again in July 2026 | **Payment** | **Not yet verified.** Press reports only |
| Heritage trees, Maharashtra (Urban Areas) Protection and Preservation of Trees Act, 1975, as amended in 2021 | In urban areas a tree can be categorised as a heritage tree, and a proposal to fell one goes to the State Tree Authority. News reports put the age at 50 years or more, but the amended Act leaves the norms to the Government | **Protected** | **Not yet verified.** The age comes from news reports |
| Compensatory planting equal to the felled tree's estimated age (Maharashtra Trees Act, Section 8) | To fell a tree in a Maharashtra urban area you must plant as many trees as the felled tree's estimated age in years. A 60-year-old tree means 60 new trees | **Conditional** | Verified |
| Karnataka Preservation of Trees Act, 1976 | Where the Act applies, felling a tree needs the Tree Officer's previous permission, and you must plant replacement trees. The Act sets no age test | **Protected** | Verified |
| Delhi Preservation of Trees Act, 1994 | Felling, removing or disposing of a tree needs the Tree Officer's previous permission. The Act has no age test | **Protected** | Verified |
| Delhi Forest Department circular of 2 June 2023 | Felling permissions carry a condition to plant 10 saplings for each tree felled and to maintain them for 5 to 7 years | **Conditional** | Verified |

#### United States

| Rule | In short | Outcome | Source |
| --- | --- | --- | --- |
| City Forest Credits Preservation Protocol v14.40 (40-year) | Can credit the carbon already stored in an existing urban forest stand that is at risk of being cleared, if the owner commits to preserve it for 40 years. It credits avoided loss, not new growth | **Conditional** | Verified |
| City Forest Credits Afforestation and Reforestation Protocol v12 (26-year) | Credits only newly planted project trees. Trees that already stand, trees planted to meet a legal requirement and trees planted after cutting healthy trees are not eligible | **Not eligible** | Verified |
| Climate Action Reserve U.S. Forest Protocol v5.1, Improved Forest Management | Credits only the extra carbon an existing forest holds compared with a baseline, not the carbon it already stores. It requires 100 years of monitoring | **Conditional** | Verified |
| American Carbon Registry, Improved Forest Management on Non-Federal U.S. Forestlands, v2.1 | Credits the extra carbon a non-federal forest keeps compared with a harvest baseline. It sets no stand-age test and does not credit existing carbon stock as such | **Conditional** | Verified |
| Family Forest Carbon Program with Verra VM0045 | Private owners of 30 or more acres of naturally regenerating forest can enrol in a 20-year programme that rewards a changed management practice. It is measured against matched baseline plots, not against the age of the trees | **Conditional** | Verified |
| Portland City Code 11.20.060, Heritage Trees (an example) | Portland can designate a Heritage Tree because of its age, size, type, historical association or horticultural value. A designated tree cannot be removed without the consent of the Urban Forestry Commission | **Protected** | Verified |
| Los Angeles Protected Tree and Shrub regulations, Ordinance 186873 (an example) | Listed native trees are protected once they reach 4 inches in cumulative trunk diameter at 4.5 feet. The test is species and size, not age | **Protected** | Verified |

#### European Union

| Rule | In short | Outcome | Source |
| --- | --- | --- | --- |
| Regulation (EU) 2024/3012 (CRCF) | Under the EU's voluntary certification framework, only net removals above a baseline, from an activity lasting at least five years, can be certified. The activity must go beyond legal requirements. Certification is required, and an estimate is never automatically certifiable | **Conditional** | Verified |
| CRCF carbon farming certification methods (Commission Delegated Regulation C(2026)4666, adopted 10 July 2026) | Methods for afforestation, agroforestry on mineral soils and peatland rewetting. Until they enter into force, certification schemes cannot yet apply for recognition for these activities. Tagged **Proposed, not yet in force** | **Conditional** | **Not yet verified** |
| EU guidelines on primary and old-growth forests (SWD(2023) 62 final) | Non-binding guidance on how Member States can identify and strictly protect old-growth forests, using signs such as old or large trees and deadwood. It sets no tree-age threshold | **Conditional** | Verified |
| Berliner Baumschutzverordnung (an example) | In Berlin, deciduous trees (except fruit trees), Scots pines, walnuts and Turkish hazels are protected once the trunk circumference is 80 cm at 1.30 m height (50 cm on at least one stem of a multi-stem tree). The test is size, not age | **Protected** | Verified |

These are short summaries. The card on the page has the details and the links to the sources. The reasons behind each
rule, and the questions still open for the three that are not yet verified, are in
[the research note](../research/tree-age-carbon-rules.md#open-questions).

## Planning new trees

Set the age to 0. The page says "Planning new trees" and explains: "You are planning new trees, so nothing is stored
yet. The chart shows how much they could store as they grow."

- **Carbon stored now** starts from nothing. The chart shows what the trees could store as they grow.
- For planned trees, the app allows for some of them dying. For trees that already stand, the number you enter is
  counted as alive today.
- Rules about trees that already stand show **Not applicable**. Rules written for new planting, or for trees of any
  kind, show **Conditional**.
- The trunk girth box is switched off.

To compare different tree counts and years for a plantation you plan, use the [Simulation](simulation-lab.md) page.

## Share your numbers

**Copy link** copies the address of the page. The button then says "Link copied". If your browser does not allow it,
the page says: "Could not copy. Copy the address from the browser bar instead."

The address holds your country, state or region, setting, species, age, number of trees and trunk girth. Anyone who
opens it sees the same page. It holds no coordinates. Nothing you enter on this page is saved on the server.

## What this page does not do

- It does not look at your plot, your boundary or your satellite data. It works from the boxes on this page only.
- It does not decide eligibility. It tells you what the rules say in short and where to check.
- It does not know the rules of your own city, district or village. The city examples only show the kind of rule that
  may exist.
- It does not turn trees into credits. Nothing on the page is a certified result.
- It is not legal advice.

To have the team of helpers explain the same questions for one of your plots, run the **Tree-age check** plan in
[AI agents](ai-agents.md#the-three-plans).

## If something goes wrong

| You see | What to do |
| --- | --- |
| **The tree-age check needs the API** | The server is not answering. Ask whoever runs your copy of the app to start it, then press **Try again** |
| **Something went wrong**, with **Try again** | Press **Try again**. If it keeps happening, see [getting help](faq.md#getting-help) |
| A pink box with a message from the server and "HTTP 409" | The server refused the request. A production installation does this while some growth numbers are not yet verified. Read the message, and see [what "pending" means](faq.md#what-does-pending-mean-next-to-a-value) |
| "No tree species are listed for this country yet." | Choose another country |
| A rule you expected is not on the list | Look under **Other rules in** your country. Rules of your own city or district may not be in the list at all |
| A rule differs from what the authority told you | The authority is right. Please tell the project, see [getting help](faq.md#getting-help) |

## Learn more

- [Tree age model](../architecture/tree-age-model.md) explains how the numbers and the rule matching work.
- [Tree age, carbon credits and the law](../research/tree-age-carbon-rules.md) explains where each rule comes from.
  Its [science notes](../research/tree-age-carbon-rules.md#science-notes-for-the-dashboard) cover how trees keep
  growing as they age.
- [IPCC age-class growth](../research/ipcc-age-class-growth.md) explains the 20-year split.
- Words used on this page: [additionality](../concepts/additionality.md),
  [permanence](../concepts/permanence.md), [leakage](../concepts/leakage.md),
  [MRV](../concepts/mrv.md) and [carbon credit versus estimate](../concepts/carbon-credit-vs-estimate.md).

Back to the [user guide](README.md). Next: [AI agents](ai-agents.md) or [Results explained](results-explained.md).
