# Mark your land

This page shows how to tell the app where your land is. You do it on the **My land** page, the map screen that
opens when you press **Open workspace**. All the ways to add land are in one vertical toolbar named **Mark your
land**, at the left of the map. Use the way that matches what you know: the shape of the field, a row of trees, a
pin and a size, GPS readings, or a file.

![The My land page with an example plot: the Mark your land toolbar at the left of the map, the Earth data & insights panel and the Selected plot details panel at the right, and three result cards below the map.](../images/screenshots/02-workspace.png)

The screenshots in this guide show demo data, not a real farm. Whatever the app calculates for a plot is a scenario
estimate, not an issued carbon credit.

- [Before you start](#before-you-start)
- [Find your place on the map](#find-your-place-on-the-map)
- [Choose a way to mark your land](#choose-a-way-to-mark-your-land)
- [Boundary](#boundary)
- [Tree line](#tree-line)
- [Pin + size](#pin--size)
- [Coordinates](#coordinates)
- [Import file](#import-file)
- [After the plot is created](#after-the-plot-is-created)
- [Exact and approximate boundaries](#exact-and-approximate-boundaries)
- [Fix a mistake: Edit and Delete](#fix-a-mistake-edit-and-delete)
- [Look at your land with the layers](#look-at-your-land-with-the-layers)
- [Map or Satellite](#map-or-satellite)
- [If something goes wrong](#if-something-goes-wrong)

## Before you start

- **Three regions.** The app works for India, the United States and the European Union (its 27 member states).
  It works out the country from where your land is. Land anywhere else is refused with a message such as "The plot
  could not be created: Country XX is not supported in this release (IN, US, EU members)."
- **Size limits.** A plot can be from 0.01 hectares (100 m², about 0.025 acres) up to 10,000 hectares. The app reads
  vegetation data on a grid of 30 m squares and can handle at most 40,000 of them. A plot whose surrounding box is
  bigger than about 3,600 hectares gets no vegetation data, so the vegetation layers and the **Change over time**
  card stay empty for it. Split a very large plot into smaller plots.
- **Default country.** The country you chose on the landing page, or in **Settings** under **Default country**,
  decides where the search box looks and which unit the size boxes start with (see
  [Pin + size](#pin--size)).
- **Phones.** The steps are the same, but you tap instead of click. The panel for each way opens below the map
  instead of on top of it.

## Find your place on the map

- **Search a place or address.** Type at least three letters in the search box at the top left of the map. A list
  of places appears. Pick one and the map flies there. If nothing matches, the list says "No places found".
  The search looks in your **Default country**; with **European Union** it is not limited to one country. If a
  place you know is missing, check that setting. When your copy of the app runs in demo mode, the search knows
  only a few example places.
- **From the landing page.** If you typed a **Village, district or address** there and pressed **Locate my land**,
  the search box on the map is already filled in. Press Enter to take the first result, or click the box and
  pick one.
- **Use my location** (at the right of the map) flies to where your device says you are. Your browser asks for
  permission first. If it cannot tell, you see "Location unavailable — check browser permissions."
- **Zoom in** and **Zoom out** are the plus and minus buttons at the right. The map is flat and always has north
  at the top. Zoom in until you can see the edges of your field before you draw.

## Choose a way to mark your land

When you have no land yet, a card called **Add your land** says "Choose the easiest way for you. You can draw the
exact edges later." and offers the five ways as big buttons. **Explore the map first** closes the card. After you
have land, the same five ways are in the **Mark your land** toolbar, followed by **Edit** and **Delete**.

| If you know... | Use | The boundary is |
| --- | --- | --- |
| The shape of your field and can see its corners on the map | **Boundary** | Exact |
| You have a row of trees along a bund, a road or a field edge | **Tree line** | Approximate |
| Where the land is and about how big it is | **Pin + size** | Approximate |
| GPS readings for the corners, or one reading and the size | **Coordinates** | Exact with three or more corners, approximate with one point |
| A file from QGIS, a GPS app or Google Earth | **Import file** | Exact when the file holds a boundary |

Choosing a tool again switches it off. Choosing another tool cancels the first one. The panel of each tool has a
close button and, for most of them, **Cancel**. Nothing is saved until the plot is created.

## Boundary

Use this when you can recognise your field on the map.

1. Choose **Boundary**. The panel says: "Click on the map at each corner of your land; click the first corner
   again to finish."
2. Click each corner in turn, going around the field.
3. Click the first corner again to finish.

The app checks the shape, creates the plot and selects it. If the shape is not accepted, an amber message says
"The polygon is not valid:" followed by the reason, and you can draw it again.

| Reason shown | What to do |
| --- | --- |
| at least 4 vertices are required | Add corners. The shape needs at least three different corners (the app also counts the closing point, so it says 4) |
| at most 500 vertices are allowed | Use fewer corners |
| coordinates are out of range | A point is not on the earth. Draw it again on the map |
| area must be at least 0.01 ha | The shape is too small |
| area must be at most 10 000 ha | The shape is too large. Split it into smaller plots |
| edges must not cross | The outline crosses itself, like a figure eight. Draw it again without crossing |

The boundary is saved as **Exact**, with the source "Drawn on the map".

## Tree line

Use this for a row of trees along a bund, a road or a field edge, when you do not have a field to outline.

1. Choose **Tree line**. The panel says: "Click along the row of trees. Click the last point again (or press Enter)
   to finish."
2. After you finish, the panel shows the **Length** of your line and the **Suggested trees**, and the map previews
   the strip around the line.
3. Change **Space between trees** if needed. It starts at 5 m and can be 0.5 to 50 m. The suggested number of trees
   is the length divided by the spacing, rounded down, plus one (a tree at each end).
4. Change **Strip width** if needed. It starts at 4 m and can be 1 to 50 m. It is the total width of the strip, so
   the strip reaches half that distance to each side of the line.
5. Press **Create plot**. If the line is wrong, press **Draw again**.

The note in the panel explains the result: "The strip along the line becomes an approximate plot, and the
suggested count fills in your number of trees." So the new plot has the suggested count already entered as the
**Number of trees**. Change it if you counted differently.

If a value is out of range you see "Space between trees must be 0.5–50 m." or "Strip width must be 1–50 m." A line
can have at most 500 points and be at most 50 km long. A very short line makes a strip below the 0.01 hectare
minimum, which is refused. The source is "Tree line" and the boundary is **Approximate**.

## Pin + size

Use this when you know where your land is and about how big it is, but not its exact shape.

1. Choose **Pin + size**. The panel says: "Click the map to drop a pin, or use the centre of the map." Click the
   spot, or press **Use map centre**. The panel then says "Pin at" and the position.
2. Under **How big is your land?**, type the size. It starts at 2. Choose **acres** or **hectares**. The unit starts as
   acres for India and the United States and hectares for the European Union, unless you chose a unit in
   **Settings**.
3. A line such as "Square of … around the pin" shows the area of the square. The note says: "A square of this size
   around the pin becomes an approximate boundary."
4. Press **Create plot**.

The square has the size you typed, with the pin at its centre. It will not match the real shape of your field, so
the plot is **Approximate**, with the source "Pin + size". If you type something the app cannot use, you see
"Enter the size as a number.", "The size must be larger than 0." or "That is larger than 10 000 hectares."

## Coordinates

Use this when you have GPS readings, for example from a phone or a survey sheet.

1. Choose **Coordinates**. The box is labelled: "Paste or type latitude, longitude — one point per line (decimal or
   13°17'32"N 77°32'18"E)".
2. Type or paste one point per line, latitude first, for example `13.2923, 77.5384`.
3. Read the line the panel shows, then press **Create plot**.

What you can type:

| Format | Example |
| --- | --- |
| Decimal degrees, separated by a comma, a semicolon or a space | `13.2923, 77.5384` |
| With the letters N, S, E, W | `13.29N 77.53E` |
| Degrees, minutes and seconds | `13°17'32"N 77°32'18"E` |
| Degrees and decimal minutes | `13°17.538'N 77°32.303'E` |

Latitude comes first. If the first number cannot be a latitude (it is beyond 90) and the second can, the app swaps
them and tells you which lines it swapped. Lines it cannot read are skipped, and the panel names their line numbers.
Header lines and empty lines are ignored. You can enter up to 500 lines and 20,000 characters.

What happens depends on how many points you give:

| Points | Result |
| --- | --- |
| One | The panel says "One point:" and the position, and asks you to give the size of your land in the same **How big is your land?** box as for [Pin + size](#pin--size). It then works like **Pin + size**: an **Approximate** square |
| Two | Not enough for an area. The app says that two points describe a line, not an area, and asks for a third corner (or suggests **Tree line**). Or delete one point and give the size instead |
| Three or more | A polygon. The panel shows "3 corners" (or however many) and the area. List the corners in order around the field. The app closes the shape by itself, so you do not have to repeat the first corner. The plot is **Exact**, with the source "Typed coordinates" |

If the shape crosses itself, the panel asks you to list the corners in order around the boundary. When the server
is offline, the panel adds: "Calculated in your browser while the server is offline — it is checked again when the
plot is saved."

## Import file

**Import file** opens the **Import data** window, where you add GeoJSON, KML/KMZ, CSV, LAS or LAZ files. A file with
a boundary can become your land; a file with tree points or crowns can give you a tree count. See
[Import data](import-data.md).

## After the plot is created

- The app names the plot "Plot A". The next plots are "Plot B", "Plot C" and so on.
- It selects the plot, flies to it, and shows its name and area at the top of the map, for example "2.13 ha · 5.26
  ac".
- If something goes wrong, an amber line under the map starts with "The plot could not be created:" and gives the
  reason.
- Next, describe your trees in the **Selected plot details** panel. See
  [Getting started, step 2](getting-started.md#step-2-add-your-trees).
- To work with another plot, click its outline on the map or choose it in the **Plot** box of the panel. The
  **Data** page lists all of them ([Import data](import-data.md#the-data-page)).

## Exact and approximate boundaries

| Kind | Made by | How you can tell |
| --- | --- | --- |
| **Exact** | **Boundary**, **Coordinates** with three or more corners, **Edit** with **Apply**, an imported boundary | A solid outline |
| **Approximate** | **Tree line**, **Pin + size**, **Coordinates** with one point | A dashed outline on the map, the label "Approximate boundary" in the **Source** column of the **Data** page, and a note in the plot panel |

An approximate boundary is a good start, but the area, and so the tree density and the estimate, depend on a guess
about the shape. The plot panel says "Approximate boundary — draw the exact edges for a better estimate" and offers
**Draw exact edges**, which starts **Edit**.

## Fix a mistake: Edit and Delete

**Edit** and **Delete** work on the selected plot, so both are greyed out until a plot is selected.

- **Edit.** Choose **Edit**. The panel says: "Drag the corners to fit your land, then press Apply. It is saved as a
  new plot." Move the corners, then press **Apply**, or **Cancel** to leave things as they were. The result is a **new**
  plot with the next free name, an **Exact** boundary and the source "Drawn on the map". The old plot stays. Tree
  details are not copied, so enter them again, and delete the old plot when you no longer need it.
- **Delete.** Choose **Delete** and confirm "Delete this plot and its analysis?". The plot, its analysis, its tree
  details and its estimate are removed. The **Data** page can also delete plots.
- Plots cannot be renamed in this version.

## Look at your land with the layers

The **Earth data & insights** panel at the right of the map lists the layers. It shows "N on" for the number that
are switched on. The panel appears on screens the width of a tablet or wider. It is hidden on phones and while you
are drawing. Two layers are on at first. A small **Legend** at the bottom of the panel explains the colours of the
plain map: **Tree plantation zone**, **Cultivated land**, **Other plots** and **Water body**. It is hidden in the
satellite view.

| Layer | What it shows |
| --- | --- |
| **Land use layer** | Its hint says "ESA WorldCover 2021 · plot shares". In this version switching it does not change the map. The land cover shares of your plot are in the [report](reports.md) |
| **Vegetation health (NDVI)** | Coloured squares, about 30 m wide, over your plot, from brown (bare or sparse) through yellow to dark green (dense, healthy). It follows the **Observation year** slider. It needs a selected plot |
| **Soil & terrain** | Its hint says "SoilGrids SOC · climate zone". In this version switching it does not change the map. The soil number is in the [report](reports.md) |
| **Tree cover (AI detected)** | Separate patches of trees, each with a confidence score. See below |
| **Imported trees** | Tree tops or crowns from your imported files. See below |

**Observation year.** When the plot has vegetation data for more than one year, the **Vegetation health (NDVI)** layer
is on and a plot is selected, a slider appears at the bottom of the map on wider screens. Move it to see the
latest month of that year. Its caption, such as "2026 · NDVI 0.63", gives the year and the average NDVI of the
plot. NDVI is explained in [Getting started](getting-started.md#step-3-the-app-analyzes-your-plot). For the whole
series month by month, see
[Change over time](results-explained.md#change-over-time).

**Tree cover (AI detected).** Switch it on with a plot selected. The panel says "Detecting tree cover…", then
gives a line such as "3 patches · 12% of plot". Click a patch to see "Tree cover · confidence 0.72 · 0.3 ha" or
similar. Read it with care:

- The app marks places where the vegetation index (NDVI) stays high over recent months. It looks at groups of
  satellite squares, so the panel notes: "10 m satellite pixels show groups of trees, not single crowns". The
  analysis grid is 30 m wide, built from 10 m Sentinel-2 pixels.
- It cannot tell trees from other dense green plants, such as a thick crop, tall grass or a hedge.
- The confidence is a ranking score between 0 and 1, not a probability. Patches below 0.5 are left out. It rises
  with how green the cells are, how many cells form the patch and how steady the greenness stayed.
- It does not count trees. To get a tree count, use the [Tree line](#tree-line) tool, count them yourself, or
  [import detected trees](import-data.md#use-the-trees-as-your-tree-count).
- In demo mode the satellite values are synthetic, so the patches are an example only.

**Imported trees.** Switch it on to see the trees from your latest import for the selected plot as points or
outlines. The panel says "No imported trees for this plot yet", or it gives the count and the file name, in the form
"N trees from your-file.laz". The **View on map** button on the **Data** page opens a particular file.

## Map or Satellite

The **Map | Satellite** switch at the bottom left of the map changes the background. **Satellite** shows aerial or
satellite pictures where your copy of the app has a source for them. Pictures are for looking; the app does not
analyse them for you. Read [Satellite imagery](satellite-imagery.md) for which pictures you get in each country, how
sharp they are and who owns them. If **Satellite** is greyed out, hover over it: the tooltip says why, for example
"Satellite imagery needs the API (or VITE_SATELLITE_TILES_URL)."

The credits for the map and the pictures are at the bottom of the map. Press the small "i" ("Show all map
credits") to see them all.

## If something goes wrong

| You see | What it means or what to do |
| --- | --- |
| "Your browser does not support WebGL, which the map needs." | Update your browser or try another one |
| "Basemap unavailable — showing your plot on a plain ground" | The background map could not load. Your plot still works. Try again later |
| "Satellite tiles could not be loaded — showing the plain map" | The picture source did not answer. Switch back to **Map** or try later |
| "Location unavailable — check browser permissions." | Allow location for this site, or search for your place instead |
| "The polygon is not valid: …" | See the table under [Boundary](#boundary) |
| "The plot could not be created: …" | Read the reason after the colon. A country that is not supported, or a shape that is too small or too large, are the usual causes |
| "No places found" | Check the spelling, or your **Default country** in **Settings** |
| **Edit** or **Delete** is greyed out | Select a plot first |

Next: [Getting started, step 2](getting-started.md#step-2-add-your-trees), or back to the [user guide](README.md).
