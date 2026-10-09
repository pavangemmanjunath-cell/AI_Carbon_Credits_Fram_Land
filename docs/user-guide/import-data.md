# Import data

You can bring files into the app instead of drawing: a file with the **boundary** of your land, a file with the
**trees** someone has already detected, or a **point cloud** from a drone or a laser scan. The app reads the file,
keeps only the results, and lets you decide what to use. This page explains the **Import data** window, what each
file type can give you, and the **Data** page where the results are listed.

![The Import data window over the My land page: a drop area for files, the two switches for boundary files and tree detection both turned on, and the Import button not yet active because no file has been added.](../images/screenshots/04-import-dialog.png)

An import gives you outlines and counts. They are not carbon values. Any carbon figure the app calculates from them
is a scenario estimate, not an issued carbon credit.

- [Open the Import data window](#open-the-import-data-window)
- [What you can import](#what-you-can-import)
- [Import step by step](#import-step-by-step)
- [The two switches](#the-two-switches)
- [What you see after an import](#what-you-see-after-an-import)
- [Use a boundary as your land](#use-a-boundary-as-your-land)
- [Use the trees as your tree count](#use-the-trees-as-your-tree-count)
- [How the app reads a file](#how-the-app-reads-a-file)
- [Point clouds](#point-clouds)
- [Limits](#limits)
- [Privacy: what is kept](#privacy-what-is-kept)
- [The Data page](#the-data-page)
- [Bring in results from QGIS AI Segmentation](#bring-in-results-from-qgis-ai-segmentation)
- [Try the sample files](#try-the-sample-files)
- [If an import fails](#if-an-import-fails)

## Open the Import data window

Any of these opens the same window:

- the green **Import** button at the top right of the app (on a narrow screen it is an icon, and its tooltip says
  "Import data");
- **Import file** in the **Mark your land** toolbar on the **My land** page, or in the **Add your land** card;
- **Import** on the **Data** page.

## What you can import

| Type | File ends in | What the app looks for |
| --- | --- | --- |
| GeoJSON | `.geojson`, `.json` | A boundary polygon, many small polygons (tree crowns) or points (trees). Coordinates must be longitude and latitude (WGS 84). Lines are not imported |
| KML | `.kml` | The same, from Google Earth, QGIS or a GPS app |
| KMZ | `.kmz` | A zipped KML file |
| CSV table | `.csv` | Rows of points. The app finds the latitude column (`lat`, `latitude` or `y`) and the longitude column (`lon`, `lng`, `long`, `longitude` or `x`). A `name`, `label` or `title` column names the point; `score` and `height` columns are kept. Without column names, the first two columns are read as latitude and longitude |
| LAS point cloud, LAZ point cloud | `.las`, `.laz` | A 3D cloud of laser or photo points over the land. The app looks for tree tops |
| E57 point cloud | `.e57` | Only if your server supports it. Otherwise convert the cloud to LAS or LAZ first (CloudCompare or PDAL can do it) |

The window says: "Drag GeoJSON, KML/KMZ, CSV, LAS or LAZ files here or browse to upload", with the note ".e57 if
your server supports it". The app checks the start of each file, not only its name, so renaming a file to another
type does not work.

## Import step by step

1. **Add your files.** Drag them into the dashed area, or press **browse** and choose them. You can add several at
   once. Each file is listed with its name, its size and its type, for example "1.8 MB · LAZ point cloud". A file the
   app cannot read shows "This file type cannot be imported. Use GeoJSON, KML/KMZ, CSV, LAS or LAZ." The **x** button
   at the end of a row, labelled "Remove" followed by the file name, takes a file off the list. Adding the same file
   twice is ignored.
2. **Check the two switches** (below) and the line at the bottom. It says "Results are linked to" and the name of
   the selected plot, or "No land selected — tree counts cover the whole file."
3. **Press Import.** The button says "Importing…" while it works. Files go up one at a time. Each row shows
   "Uploading" and a percentage, then "Analysing…".
4. **Read the result under each file** and use the buttons it offers (see [below](#what-you-see-after-an-import)).
5. **Press Done.** Before that, the left button reads **Cancel**; when the files are finished it reads **Close**.

If you press **Cancel**, press **Close** or shut the window while files are still going up, the rest are cancelled
and their rows say "Cancelled". A file that has already been analysed is kept.

## The two switches

Both are on when the window opens. They apply to the whole batch, and you cannot change them while it is running.

| Switch | What it does |
| --- | --- |
| **Use boundary files as my land** | "A boundary found in a file becomes a land plot right away." Switch it off if you want to look first. You will then see a **Use as my land** button for each boundary |
| **Run tree detection on import** | The information button ("What is this?") says: "Counts tree points/crowns (for example from QGIS AI Segmentation) and finds tree tops in LAS/LAZ point clouds. Runs on your server — nothing is sent to an AI service." Switched off, a point cloud is only inspected, with no tree search, so the row says "No boundary or trees found in this file." |

## What you see after an import

| Text under the file | What it means |
| --- | --- |
| "Uploading 40%", then "Analysing…" | The file is on its way, then being read |
| "Boundary found · 2.13 ha" | The file holds the outline of a piece of land. With the first switch on, the button next to it goes from "Adding…" to "Added as Plot B". With it off, the button reads **Use as my land** |
| "198 trees detected" | The file holds tree points or crowns, and this is how many the app counted |
| "472 trees detected (mean height 5.0 m)" | A point cloud. The mean height is shown too |
| "243 inside Plot A" | How many of those trees lie inside the linked land. It appears only when the app could tell and the number differs from the total |
| **Use 243 trees for Plot A** | Saves the count as the tree count of that plot (see [below](#use-the-trees-as-your-tree-count)). It then reads "Saving…" and "Saved as the tree count of Plot A" |
| "Add or select your land first to use these trees." | There is no land to attach the trees to yet |
| "No boundary or trees found in this file." | The file is readable, but holds nothing the app can use |
| "Import failed: …" | The file was refused. The text after the colon says why. See [If an import fails](#if-an-import-fails) |
| "Cancelled" | You stopped the import before this file was done |

Under a row you may also see up to three short notes in grey, for example that several polygons were found and the
largest was used, or that the point cloud is thinner than 2 points per square metre.

A file can hold both a boundary and trees. You then see both lines.

## Use a boundary as your land

When a file holds a boundary, the app creates a plot from it:

- The plot gets the name stored in the file, such as "Demo mango orchard (synthetic)". If the file has no name, it
  gets the next free "Plot A", "Plot B", and so on.
- The boundary is **exact**, and the source is "Imported file". It is selected on the map when it is created.
- The country is worked out from where the boundary is. Land outside India, the United States and the European
  Union is refused, and the reason appears under the file.
- If a file holds several polygons, the largest one is used and a note says so.
- With the first switch on, files that come later in the same batch are linked to the new land, so their trees are
  counted inside it.

Then describe your trees in **Selected plot details**. See [Getting started, step 2](getting-started.md#step-2-add-your-trees).

## Use the trees as your tree count

A file with tree points or crowns, or a point cloud, gives a count. The button, for example **Use 243 trees for Plot A**,
turns that count into the tree details of the plot. This is what it saves:

- **Number of trees:** the trees inside the plot when the app could tell, otherwise all trees in the file.
- **Tree type, planting year and survival:** the values from the tree details you are editing on the **My land**
  page. If there are none, the first tree type in the list and the example planting year are used, so check them
  afterwards.
- **Average height:** for a point cloud, the mean height of the tree tops. Diameter is left empty.
- **Where the numbers came from:** the tree details are marked "model-estimated", so anyone who reads the
  [report](reports.md) can see that the count came from detection and not from a count in the field. The estimate is
  then updated.

It is a count of **features in the file**. If a segmentation tool drew two outlines around one tree, it is counted
twice, and a tree it missed is not counted. Compare the count with a count in the field on a sample of your land.
Then read [what the numbers mean](results-explained.md#what-the-number-is).

## How the app reads a file

The window always lets the app decide what a GeoJSON, KML, KMZ or CSV file contains.

| The file holds | The app reads it as |
| --- | --- |
| One polygon, or a large polygon with a few small ones | A **boundary**. If there are several, the largest |
| Many small polygons, each under 0.05 hectares (at least 10 of them, or at least 3 with a typical area under 200 m²) | **Tree crowns**, counted by their centre points |
| Many points | **Tree points** |
| 3 to 50 points that enclose at least 0.01 hectares | A **boundary**, with the corners taken in the order of the file. A note says so |

These rules are a guess. If the guess is wrong (for example you want seven corner points counted as seven trees),
the window cannot be told otherwise. The server can, through the API, which is described in
[Geometry helpers, imports and detection](../architecture/imports-and-detection.md).

- **Confidence.** If the file has a column named `score`, `confidence`, `prob` or `probability`, the app uses it.
  Values from 0 to 1 are used as they are; values up to 100 are read as percentages. Trees below 0.5 are left out,
  and the window does not let you change that limit. Trees with no value are kept.
- **Height.** A column named `height`, `height_m`, `h`, `tree_height` or `tree_height_m` supplies tree heights.
- **Inside your plot.** A crown counts when its centre lies inside the plot. A point counts when it lies inside or
  on the edge.
- **Several files.** You can mix types in one batch, for example a KML boundary followed by a CSV of trees.

## Point clouds

A LAS or LAZ file is a cloud of points with heights. The app finds the ground, subtracts it to get the height of
everything above it, keeps the highest point in each 0.5 m square, and marks the peaks that rise at least 2 m as
**tree tops**. Each top is one tree. You get the number of tops, their mean height and, when possible, the number
inside your plot.

- **Whole file versus your plot.** The count and the heights describe the **whole cloud**. Only the number "inside"
  your plot is limited to it.
- **Coordinates.** The cloud should use a projected coordinate system in metres, such as a UTM zone. A cloud in
  degrees is refused. A cloud with no coordinate system is still analysed as if its units were metres, but it cannot
  be placed on the map or counted inside a plot.
- **Ground.** If the cloud has points classified as ground, the app uses them. If not, it uses the lowest point in
  each 5 m square, and heights can come out too low under dense trees. A note tells you.
- **Density.** Below about 2 points per square metre, false tree tops can appear, and the app adds a warning.
- **Size.** A very large cloud (over 30 million points) is thinned before it is read, and one with over 300 million
  points is refused.
- **How good is it?** The settings of the method are project assumptions that nobody has verified on real farms
  ([detection settings](../architecture/imports-and-detection.md#4-parameters)). Real tree crowns touch and overlap,
  so expect under-counts, and some double counts on wide crowns. Do not quote the accuracy of the sample files, which
  are artificial. Check a count against a count in the field.

## Limits

| What | Limit |
| --- | --- |
| File size | 50 MB, unless whoever runs your copy of the app has set another limit. A larger file is refused: "The file is larger than the upload limit of 50 MB." |
| GeoJSON | At most 20,000 features. WGS 84 only |
| KML and KMZ | A KMZ may hold at most 100 files and unpack to at most 50 MB. A KML that declares a document type (a DOCTYPE) is refused for safety |
| CSV | At most 20,000 rows |
| Preview on the map | At most 5,000 trees are drawn, picked evenly. The count still covers all of them |
| Plot made from a boundary | 0.01 to 10,000 hectares, and no crossing edges, as for any plot ([Mark your land](mark-your-land.md#boundary)) |
| Point clouds | See [above](#point-clouds) |

## Privacy: what is kept

- **The file itself is not stored.** The window says it: "Only the results are kept — the file itself is not
  stored." The server reads the file in memory and drops it.
- **The results are kept as private records:** a summary, the boundary or tree positions for a map preview, any
  notes, and which method produced the numbers. A record is tied to the plot it was linked to and is deleted with
  that plot. You can also delete a record yourself on the [Data page](#the-data-page).
- **Coordinates are not written to the server's logs.** The checks run on your server with fixed rules. No AI model
  reads your file, and no coordinates go to one.

See [privacy in the FAQ](faq.md#privacy-and-your-data) for the wider picture.

## The Data page

**Data** in the left menu (under **Land**) lists what you have. The page says: "Your land plots and imported files.
Exact boundaries stay private." The **Import** button is at the top right. Two tabs show a count each. The address
of the second tab ends in `?tab=files`.

![The Data page with the Land plots tab open, listing three demo plots with their area, source and date, and the Open on map, Results and bin buttons on each row.](../images/screenshots/05-data.png)

The screenshot shows demo data: three made-up plots, one for each country. The page lists land and files only. Any
carbon figure you open from it with **Results** is a scenario estimate, not an issued carbon credit.

The **Land plots** tab has these columns:

| Column | What it shows |
| --- | --- |
| **Name** | The plot name, with its ID and region below |
| **Area** | The area in hectares (ha) or acres (ac). With the default **Area units** setting, each plot uses the usual unit of its own country: acres for a plot in the United States, hectares for India and the EU. **Hectares first** or **Acres first** in **Settings** changes it for every plot |
| **Source** | How the plot was made: Drawn on the map, Uploaded file, Imported file, Pin + size, Tree line, Typed coordinates, QGIS plugin, API, Demo data or Other. A blue "Approximate boundary" tag marks plots made from a pin, a tree line or a single point |
| **Added** | The date |
| **Actions** | **Open on map**, **Results** (opens the carbon potential page of that plot, explained in [Results explained](results-explained.md)) and a bin icon (**Delete**) |

Deleting asks, for example, "Delete Plot B and everything linked to it?". Its tree details, estimates and import
records go too. With no land, the tab says "No land yet. Mark your land on the map or import a boundary file." and
offers **Go to the map**.

The **Imported files** tab has these columns:

| Column | What it shows |
| --- | --- |
| **Name**, **Type**, **Size**, **Added** | The file, its kind, its size and the date |
| **Linked land** | The plot the results were linked to, or a dash |
| **Result** | "Boundary · 2.13 ha", "198 trees", "472 trees · mean height 5.0 m", "Import failed" or "No boundary or trees found" |
| **Actions** | **View on map**, greyed out when there is nothing to show, and a bin icon. **View on map** opens the **My land** page with the **Imported trees** layer on and that file's results drawn, and selects its linked land. The bin asks, for example, "Delete the record of trees.geojson?" and removes only the record, not any plot or tree count you made from it |

When there is nothing yet, the tab says: "No imported files yet. Import GeoJSON, KML/KMZ, CSV or LAS/LAZ files —
only the results are kept." If the list cannot load, you see "Imported files could not be loaded."

## Bring in results from QGIS AI Segmentation

If you use QGIS, an AI segmentation tool can outline the trees in an image. The result is a polygon layer, one
outline per tree, usually with a score column.

1. Run the tool on imagery you are **allowed to analyse**. Many picture sources forbid automated analysis. Read
   [Satellite imagery](satellite-imagery.md#viewing-versus-analysing) and the
   [imagery note for the QGIS plugin](qgis-plugin.md#imagery-check-the-licence-first) first. Free Sentinel-2 images are
   open, but their 10 m pixels are too coarse for single trees.
2. Export the result layer from QGIS as GeoJSON or KML in WGS 84 (EPSG:4326). In QGIS you will find this under
   the layer's **Export** menu, **Save Features As**. The exact wording differs between versions.
3. Import the file here. Leave **Run tree detection on import** on. Select your land first, so that the trees are
   counted inside it.
4. Press **Use 243 trees for Plot A** (your own count and plot name will show) and check the tree type and planting year.

If you work in QGIS all day, the [QGIS plugin](qgis-plugin.md) can count the crowns inside a field and send the
count to the app directly.

## Try the sample files

The project has four small synthetic files for practice, all made up and free to reuse: a KML boundary of 7
corners (about 2.13 ha), a CSV of the same 7 corners, a GeoJSON with 220 tree crowns (198 count at the 0.5 score
limit) and a LAZ point cloud with about 472 trees. They are in `data/sample/imports/`. Ask whoever runs your copy of
the app for them, or see [the sample files page](../../data/sample/imports/README.md) for what each one produces. They
are made for the demo plot in Karnataka, so use them in a demo copy of the app.

## If an import fails

| You see | What to do |
| --- | --- |
| "Import failed: The file is larger than the upload limit of 50 MB." | Split the file, thin the point cloud, or ask whoever runs your copy to raise the limit |
| "Import failed:" with "Unsupported file type" or a message about the file type | Use GeoJSON, KML/KMZ, CSV, LAS or LAZ. A renamed file is refused too |
| "Import failed:" with a message that E57 needs another package | Convert the cloud to LAS or LAZ and import that |
| "Import failed:" with a message about a geographic coordinate system | Export the point cloud in a projected system in metres, such as the UTM zone of your land |
| "Import failed: The file is empty." | The file has no content. Export it again |
| "No boundary or trees found in this file." | Check the file in QGIS. It may hold only lines, or detection may be switched off for a point cloud |
| "Boundary found" but **Use as my land** gives an error | The boundary may be too small, too large, cross itself, or lie outside India, the United States and the European Union |
| The tree count looks too high or too low | Compare with a count in the field. See [Use the trees as your tree count](#use-the-trees-as-your-tree-count) |

Back to the [user guide](README.md).
