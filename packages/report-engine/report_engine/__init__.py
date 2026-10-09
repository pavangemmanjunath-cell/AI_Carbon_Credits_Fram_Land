"""report_engine — renders a plot's evidence file as HTML, Markdown, JSON or PDF.

The renderer is a pure function of the context it is given (built by the API's
ReportService); it computes nothing and fetches nothing.
"""

from report_engine.ids import ReportIdSequencer, new_report_id
from report_engine.renderer import (
    FORMATS,
    MEDIA_TYPES,
    PdfNotAvailableError,
    ReportRenderer,
    pdf_available,
)

__version__ = "0.1.0"
__all__ = [
    "FORMATS",
    "MEDIA_TYPES",
    "PdfNotAvailableError",
    "ReportIdSequencer",
    "ReportRenderer",
    "new_report_id",
    "pdf_available",
]
