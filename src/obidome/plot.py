"""Plotting module."""

from collections import deque

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen

from obidome.settings import SparklineSettings


class SparklineGenerator:
    """Generates sparkline graphs as DataURI scheme strings."""

    def __init__(  # noqa: PLR0913
        self,
        settings: SparklineSettings,
        width: int = 50,
        height: int = 30,
        max_len: int = 30,
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> None:
        """Initialize the SparklineGenerator.

        Args:
            settings (SparklineSettings): Settings for the sparkline plot.
            width (int): Width of the sparkline image in pixels.
            height (int): Height of the sparkline image in pixels.
            max_len (int): Maximum number of data points to keep in history.
            min_val (float | None): Minimum value for normalization. If None, auto-calculated.
            max_val (float | None): Maximum value for normalization. If None, auto-calculated.

        """
        self.line_color = settings.line_color
        self.fill_style = settings.fill_style
        self.fill_color = settings.fill_color

        self.width = width
        self.height = height
        self.min_val = min_val
        self.auto_min_val = min_val is None
        self.max_val = max_val
        self.auto_max_val = max_val is None

        # Ring buffer to hold historical values
        self.history = deque([0.0] * max_len, maxlen=max_len)

        # Reusable QImage and QPainter objects
        self._image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        self._byte_array = QByteArray()
        self._buffer = QBuffer(self._byte_array)
        self._painter = QPainter()

    def update_and_get_b64(self, new_value: float) -> str:  # noqa: PLR0915 TODO (hisaknown): Reduce complexity
        """Update the sparkline with a new value and return the image as a Base64-encoded DataURI string."""
        self.history.append(new_value)

        if self.auto_min_val:
            self.min_val = min([*self.history, self.min_val] if self.min_val is not None else self.history)
        if self.auto_max_val:
            self.max_val = max([*self.history, self.max_val] if self.max_val is not None else self.history)
        if self.min_val is None or self.max_val is None:
            # NOTE: This should never happen due to the checks above
            msg = "min_val and max_val cannot be None when auto_min_val or auto_max_val is enabled."
            raise ValueError(msg)

        # Clear the canvas (fully transparent)
        self._image.fill(QColor(0, 0, 0, 0))

        # Begin drawing
        self._painter.begin(self._image)
        self._painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Make the path
        path = QPainterPath()
        points = []
        step_x = self.width / (len(self.history) - 1) if len(self.history) > 1 else 0

        # Start from bottom-left
        path.moveTo(0, self.height)

        for i, val in enumerate(self.history):
            # Normalize to (0.0 - 1.0)
            ratio = (val - self.min_val) / (self.max_val - self.min_val)
            ratio = max(0.0, min(1.0, ratio))  # Clamp

            x = i * step_x
            y = self.height - (ratio * self.height)

            point = QPointF(x, y)
            path.lineTo(point)
            points.append(point)

        if self.fill_style == "solid":
            # Close the path at bottom-right
            path.lineTo(self.width, self.height)
            path.closeSubpath()

            # Fill the path
            self._painter.setPen(Qt.PenStyle.NoPen)
            self._painter.setBrush(QBrush(QColor(self.fill_color)))
            self._painter.drawPath(path)
        elif self.fill_style == "gradient":
            # Close the path at bottom-right
            path.lineTo(self.width, self.height)
            path.closeSubpath()

            # Create gradient fill
            base_color = QColor(self.fill_color)
            gradient = QLinearGradient(0, 0, 0, self.height)

            # Set gradient colors
            c_top = QColor(base_color)
            c_top.setAlpha(180)
            c_bottom = QColor(base_color)
            c_bottom.setAlpha(20)

            gradient.setColorAt(0, c_top)
            gradient.setColorAt(1, c_bottom)

            # Fill the path
            self._painter.setPen(Qt.PenStyle.NoPen)
            self._painter.setBrush(QBrush(gradient))
            self._painter.drawPath(path)

        # Draw the top line (to make it clearer)
        pen = QPen(QColor(self.line_color))
        pen.setWidth(2)  # 1.5 makes it smoother
        self._painter.setPen(pen)
        self._painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw polyline connecting points
        if len(points) > 1:
            self._painter.drawPolyline(points)

        self._painter.end()

        # Base64 encode the image
        self._buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self._buffer.seek(0)  # Seek to the beginning
        self._byte_array.clear()  # Clear previous data

        self._image.save(self._buffer, "PNG")  # type: ignore[arg-type] (QBuffer is a subclass of QIODevice)
        self._buffer.close()

        b64_str = bytes(self._byte_array.toBase64().data()).decode("ascii")
        return f"data:image/png;base64,{b64_str}"
