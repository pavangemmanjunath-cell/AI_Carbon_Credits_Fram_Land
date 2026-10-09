# Satellite imagery

On the **My land** map you can change the background from a plain map to pictures taken from above. This page
explains how to switch, which pictures you get in each country, how sharp they are, who owns them, and why these
pictures are for looking at and not for measuring.

- [Switch between Map and Satellite](#switch-between-map-and-satellite)
- [Which pictures you get](#which-pictures-you-get)
- [Sharp or blurry: 10 m and sub-metre pictures](#sharp-or-blurry-10-m-and-sub-metre-pictures)
- [How old are the pictures](#how-old-are-the-pictures)
- [Licences and credits](#licences-and-credits)
- [Viewing versus analysing](#viewing-versus-analysing)
- [Choose other pictures in Settings](#choose-other-pictures-in-settings)
- [If Satellite does not work](#if-satellite-does-not-work)

## Switch between Map and Satellite

The **Map | Satellite** switch is at the bottom left of the map. **Map** is the plain map. **Satellite** shows aerial or
satellite pictures where your copy of the app has a source for them.

- Hover over **Satellite** to see the name of the pictures it will show.
- Your plot outlines and the layers you switched on stay on top of the pictures.
- The **Legend** is hidden while **Satellite** is on, because its colours belong to the plain map.
- The credit for the pictures appears in the bar at the bottom of the map. Keep it if you take a screenshot or print
  the map.
- The app remembers your choice in this browser.

## Which pictures you get

The app picks the pictures by the country of the plot you have selected. Before you select a plot, it uses your
**Default country**. With **European Union** selected and no plot chosen, it uses the standard pictures for
everywhere else.

| Where your land is | Pictures | How sharp | Licence |
| --- | --- | --- | --- |
| India, and every country not listed below, including the other EU countries | EOX Sentinel-2 cloudless 2016 | 10 m per pixel | CC BY 4.0 |
| United States | USGS The National Map, USGS Imagery Only (aerial photographs, mostly from the NAIP programme) | Sharp in the source, but the map tiles stop at zoom 16, so you see about 1.6 to 2.2 m per pixel | Public domain |
| France | IGN Géoplateforme, aerial photographs (BD ORTHO) | 20 cm | Licence Ouverte 2.0 |
| Spain | IGN España, PNOA aerial photographs (Sentinel-2 when zoomed far out) | 25 cm and 50 cm | CC BY 4.0 scne.es |
| Netherlands | PDOK Luchtfoto RGB | 8 cm, 5 cm in places | CC BY 4.0 |

India has no openly licensed, high-resolution picture service that the project could verify, so Indian land uses
the standard 10 m pictures. Google and Bing pictures are not offered, because their terms do not allow the app to
use them this way.

Two more sources can be switched on in **Settings** (see [below](#choose-other-pictures-in-settings)): newer or older
EOX mosaics, and **Esri World Imagery**, which appears only when the person who runs your copy of the app has added
an Esri key.

## Sharp or blurry: 10 m and sub-metre pictures

- **10 m pictures** (EOX, from the Sentinel-2 satellites). Each pixel covers 10 m by 10 m on the ground. You can see a
  village, a large field, a river or a forest edge. You cannot see single trees or small plots. Zoom in past level 14
  and the picture is only enlarged, so it gets blurry. This is not a fault of the app.
- **Sub-metre pictures** (United States, France, Spain, Netherlands). Many places show single trees, tree rows and
  the shapes of fields. Sharpness still varies from place to place. In the United States the stored map tiles stop at
  zoom 16, so you will not see the finest detail of the source photographs.
- **Esri World Imagery**, where it is switched on, is sharp in many places and coarse in others.

## How old are the pictures

The pictures are not live. They can be months or years old, and different parts of one map can come from different
survey dates.

- The standard 10 m pictures show **2016**. A plantation made after 2016 will not show on them, and roads, buildings
  and fields may have changed.
- The name of the pictures appears in the tooltip of **Satellite** and in **Settings**. The app does not show the
  date of each aerial photograph.

Do not use a picture alone to decide whether trees are there. Walk the land, or use a recent picture you took
yourself.

## Licences and credits

Every picture source has its own licence. The open ones let you look at the pictures and share what you see if you
credit the owner. The app shows the credit text in the bar at the bottom of the map.

| Source | What the licence allows, in short |
| --- | --- |
| EOX 2016 and 2017 mosaics | Yes, including commercial use, with the credit (CC BY 4.0) |
| EOX 2025 mosaic | Non-commercial use only (CC BY-NC-SA 4.0). Commercial use needs a licence from EOX |
| USGS (United States) | Yes. Public domain, and USGS asks for credit |
| IGN France, IGN Spain, PDOK Netherlands | Yes, with the credit given in the licence |
| Esri World Imagery | Only under Esri's own terms and the key of whoever runs the app. For display only. Check Esri's terms before any commercial use |

This is a plain-language summary, not legal advice. The exact credits and the project's research notes are in
[map and imagery licences](../licensing/MAP_LICENSES.md), [attribution strings](../licensing/ATTRIBUTION.md),
[imagery providers](../research/imagery-providers.md) and the
[data source reference](../data-sources/FREE_APIS.md#satellite-and-aerial-imagery).

## Viewing versus analysing

The pictures in the **Satellite** view are for **looking**. The app's own calculations do not use them.

- **Vegetation health (NDVI)**, **Tree cover (AI detected)** and the land cover figures come from Sentinel-2 data and
  the ESA WorldCover map, which the server reads separately from open data services. They do not read the pictures
  you see on the map. (In demo mode these values are made up.)
- If you want to run your own analysis on a picture, for example to outline trees with an AI tool in QGIS, check the
  licence first. Many picture sources forbid automated analysis, even when you may look at them. **Settings** shows
  **Automated analysis** for each source as "allowed", "not allowed" or "check the terms". Esri World Imagery is
  "not allowed". The 2025 EOX mosaic says "check the terms".
- Use pictures that allow analysis, such as the open aerial photographs above, or your own drone or aircraft images.
  Free 10 m Sentinel-2 pictures are open, but they are too coarse to separate single trees.

The [QGIS plugin](qgis-plugin.md#imagery-check-the-licence-first) repeats this warning for people who segment
imagery in QGIS.

## Choose other pictures in Settings

Open **Settings**, then **Map imagery**. It says: "Choose the satellite or aerial imagery the map shows for" and the
name of the country, then "Imagery is for viewing; automated analysis only runs where the licence allows it."

Each source is a card with a round button. The card shows:

- the name, with a "recommended" tag on the one the app uses by default, and a "covers other countries" tag on a source
  that has pictures for other countries only. Such a source will usually show nothing over your land;
- how sharp the pictures are;
- the **Licence**, as a link to the licence text;
- **Automated analysis**: "allowed", "not allowed" or "check the terms";
- for a source that cannot be used, a dimmed card and the reason, for example "Not available: Set ESRI_API_KEY to
  enable".

Your choice is saved in this browser for that country. Choosing the recommended source again returns to the default.
If the person who runs your copy of the app has fixed the pictures for the whole site, **Settings** says so:
"VITE_SATELLITE_TILES_URL is set for this build, so that imagery is used instead."

## If Satellite does not work

| You see | What it means or what to do |
| --- | --- |
| **Satellite** is greyed out. The tooltip says "Satellite imagery needs the API (or VITE_SATELLITE_TILES_URL)." | The app has no list of picture sources. Check that the server is running, or ask whoever runs your copy of the app |
| "Satellite tiles could not be loaded — showing the plain map" | The picture service did not answer. Try again later, or pick another source in **Settings** |
| The pictures turn blurry when you zoom in | You have reached the sharpest level of that source ([above](#sharp-or-blurry-10-m-and-sub-metre-pictures)) |
| A grey or blank area | That source has no pictures for the place. Switch to another source |
| The free picture service is slow | The standard 10 m pictures come from a free public service that can be busy |

The company that provides the pictures can see which map squares your browser asks for, the same as for the plain
map. Your boundary is not sent to them. See [privacy in the FAQ](faq.md#privacy-and-your-data).

Back to [Mark your land](mark-your-land.md#map-or-satellite) or the [user guide](README.md).
