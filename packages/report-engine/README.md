# report-engine

Renders a plot's evidence file as **HTML**, **Markdown**, **JSON** or **PDF**.
The renderer is a pure function of the context it is given: it computes
nothing, fetches nothing and never sees the exact plot boundary. The API's
`ReportService` assembles the context (plot summary, inventory, analysis,
estimate, programme screening, market scenarios, sources) and this package
turns it into a document.

Every report opens with "Scenario estimate - not an issued carbon credit",
labels programme results as an initial screening and ends with the full
disclaimer. Those texts come from the context and templates, not from a
language model.

## Install

```bash
python3 -m pip install -e packages/report-engine                 # or: make install
python3 -m pip install -e "packages/report-engine[pdf]"          # adds WeasyPrint
```

The only required dependency is Jinja2. PDF output uses the optional
WeasyPrint library, which needs the system libraries Pango and Cairo. Without
it, requesting a PDF raises `PdfNotAvailableError`; the API answers HTTP 501
with the problem type `pdf-unavailable`. The web app's report page offers
"Print / Save as PDF" through the browser as an alternative.

## Public API

Import from `report_engine`:

| Name | Purpose |
| --- | --- |
| `ReportRenderer(templates_dir=None)` | `render(context, fmt)` returns `bytes`; also `render_html`, `render_markdown`, `render_json`, `render_pdf` |
| `FORMATS` | `("html", "json", "markdown", "pdf")` |
| `MEDIA_TYPES` | Format to `Content-Type` |
| `pdf_available()` | True when WeasyPrint imports cleanly |
| `PdfNotAvailableError` | Raised by `render_pdf` when WeasyPrint is missing |
| `new_report_id(day, sequence)`, `ReportIdSequencer` | Ids of the form `RPT-YYYY-MM-DD-NNNN`; the sequence restarts each day |

```python
from report_engine import ReportRenderer, ReportIdSequencer

sequencer = ReportIdSequencer()
context["report_id"] = sequencer.next_id()  # e.g. RPT-2026-10-04-0001
html = ReportRenderer().render(context, "html")  # bytes
```

`ReportIdSequencer` is thread-safe. A persistent store calls `observe(id)` for
every existing report on start-up so the counter continues instead of
restarting (the API does this in `ReportService.__init__`).

## Templates and context

Templates are in `report_engine/templates/`: `report.html.j2` (print-ready,
self-contained CSS) and `report.md.j2`. Sections: plot, plantation, earth
observations, carbon, potential programmes (screening), financial scenarios,
evidence and disclaimer. The JSON format is the context itself.

Two Jinja2 environments are used, an autoescaping one for HTML and a plain one
for Markdown, with `StrictUndefined`: a template that references a key the
context does not provide fails loudly instead of printing an empty value.
Custom filters: `num` (number formatting), `pct` and `humanize`.

The context built by the API contains the plot's `public_centroid` and
`perimeter_m` but not its exact geometry or exact centroid. Keep it that way:
a report is meant to be shared.

The report covers what the assessment chain produces: plot, inventory, analysis,
estimate, programme screening, market scenarios and sources. Tree-cover
detection, imported files, tree-age results and agent transcripts (all v0.2) are
not part of the report; they are shown in the web app.

Report text is English. The `language` field of the request is recorded and sets
the HTML `lang` attribute; the templates themselves are not translated yet.

## Tests

```bash
python3 -m pytest packages/report-engine -q
```

`tests/test_report_engine.py` checks that the HTML report contains every
section and design token and escapes hostile input (a plot name containing a
`<script>` tag), that Markdown and JSON render, that format dispatch and media
types are right, that PDF fails cleanly without WeasyPrint, that missing
optional blocks render placeholders, and the report id format.

## Design notes

- No business logic: if a number or a sentence is wrong, fix it where it is
  produced (engine, configuration or service), not in a template.
- Reports are generated on request and stored by the repository (in memory, or
  PostgreSQL as `bytea`). Deleting a plot deletes its reports in PostgreSQL (a
  foreign key cascades); the memory repository keeps them until the process
  restarts, which differs from the promise in
  [data retention](../../docs/privacy/data-retention.md).
- New sections must keep the three values (environmental benefit, indicative
  carbon value, other farm income) separate and must never add them together.

## Links

- [Architecture tour](../../docs/developer-guide/architecture-tour.md)
- [Reports in the user guide](../../docs/user-guide/reports.md)
- [API contract](../../docs/architecture/api-contract.md)
