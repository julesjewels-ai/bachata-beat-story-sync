"""
Component builders for Excel reports.
Handles charts and image embedding.
"""
import io
import logging
from typing import Optional
from openpyxl.chart import BarChart, Reference
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)


class ChartBuilder:
    """
    Constructs Excel charts for visualization.
    """

    def create_intensity_chart(self, source_ws: Worksheet,
                             data_count: int,
                             intensity_col_idx: int) -> Optional[BarChart]:
        """
        Creates a Bar Chart visualizing intensity scores.

        Args:
            source_ws: The worksheet containing the data.
            data_count: Number of data rows (excluding header).
            intensity_col_idx: The column index containing intensity scores.

        Returns:
            A BarChart object or None if no data.
        """
        if data_count == 0:
            return None

        chart = BarChart()
        chart.type = "col"
        chart.style = 10
        chart.title = "Video Intensity Distribution"
        chart.y_axis.title = "Intensity Score"
        chart.x_axis.title = "Video Clip Index"

        # Reference Data: Header is row 1
        data = Reference(
            source_ws,
            min_col=intensity_col_idx,
            min_row=1,
            max_row=data_count + 1,
            max_col=intensity_col_idx
        )
        chart.add_data(data, titles_from_data=True)
        return chart


class ThumbnailEmbedder:
    """
    Handles embedding of thumbnail images into Excel cells.
    """

    def embed_thumbnail(self, ws: Worksheet, row: int, col: int,
                       image_data: bytes) -> bool:
        """
        Embeds a PNG thumbnail into the specified cell.

        Args:
            ws: The worksheet.
            row: Row number (1-based).
            col: Column number (1-based).
            image_data: Binary image data (PNG).

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Pass a fresh BytesIO directly to openpyxl so it owns the
            # stream and can re-read at save time (no stale-fp issue).
            img_stream = io.BytesIO(image_data)
            img = OpenpyxlImage(img_stream)

            col_letter = get_column_letter(col)
            cell_address = f"{col_letter}{row}"

            ws.add_image(img, cell_address)

            # Adjust row height to accommodate image (approx 60 points)
            ws.row_dimensions[row].height = 60
            return True

        except Exception as e:
            logger.warning(
                "Could not embed image at %d,%d: %s", row, col, e
            )
            return False
