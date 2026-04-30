"""
Spectrum Panel — Displays NMR and IR spectral plots.

Shows ¹H NMR stick plot, ¹³C NMR stick plot, and IR absorption
spectrum using pyqtgraph for fast, interactive rendering with
region shading and peak annotations.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QCheckBox, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainterPath

from .styles.colors import Colors, FONT_FAMILY
from ..core.nmr_data import NMRData, NMRPeak
from ..core.ir_data import IRData

# Try pyqtgraph import
try:
    import pyqtgraph as pg
    _HAS_PYQTGRAPH = True
except ImportError:
    _HAS_PYQTGRAPH = False

# Try numpy
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _configure_pyqtgraph():
    """Configure pyqtgraph for dark theme."""
    if not _HAS_PYQTGRAPH:
        return
    pg.setConfigOptions(
        background=QColor(Colors.BG_DARK),
        foreground=QColor(Colors.TEXT_SECONDARY),
        antialias=True,
        useOpenGL=False,
    )


def _stagger_labels(shifts: list[float], min_gap: float) -> list[int]:
    """
    Assign vertical tier (0, 1, 2) to each label to avoid overlap.
    shifts must be sorted descending (for inverted x-axis).
    Returns list of tier indices matching len(shifts).
    """
    if not shifts:
        return []
    tiers = [0] * len(shifts)
    # Sort by shift value for collision detection, then map back
    indexed = sorted(enumerate(shifts), key=lambda t: t[1])
    for i in range(1, len(indexed)):
        orig_idx, s = indexed[i]
        prev_orig, prev_s = indexed[i - 1]
        if abs(s - prev_s) < min_gap:
            tiers[orig_idx] = (tiers[prev_orig] + 1) % 3
    return tiers


class SpectrumPanel(QWidget):
    """
    Tabbed panel for spectral plot display.

    Tabs: ¹H NMR | ¹³C NMR | IR | UV-Vis

    Signals:
        peak_clicked: Emitted when user clicks on a peak (shift, nucleus)
        ir_band_clicked: Emitted when user clicks an IR band (wavenumber, assignment)
    """

    peak_clicked = pyqtSignal(float, str)
    ir_band_clicked = pyqtSignal(float, str)   # wavenumber, assignment

    def __init__(self, parent=None):
        super().__init__(parent)
        _configure_pyqtgraph()

        # Track peaks for click detection
        self._h1_peaks: list[float] = []
        self._c13_peaks: list[float] = []
        self._ir_bands: list[tuple[float, str]] = []   # (wavenumber, assignment)
        # Highlight markers
        self._h1_highlight_items: list = []
        self._c13_highlight_items: list = []
        self._ir_highlight_items: list = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget for different spectra
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create plot tabs
        self.h1_tab = self._create_plot_tab("¹H NMR", "Chemical Shift (δ ppm)", inverted_x=True)
        self.c13_tab = self._create_plot_tab("¹³C NMR", "Chemical Shift (δ ppm)", inverted_x=True)
        self.ir_tab = self._create_plot_tab("IR", "Wavenumber (cm⁻¹)", inverted_x=True)
        self.uv_tab = self._create_plot_tab("UV-Vis", "Wavelength (nm)", inverted_x=False)

        self.tabs.addTab(self.h1_tab["widget"], "¹H NMR")
        self.tabs.addTab(self.c13_tab["widget"], "¹³C NMR")
        self.tabs.addTab(self.ir_tab["widget"], "IR")
        self.tabs.addTab(self.uv_tab["widget"], "UV-Vis")

        # Connect plot click signals
        if _HAS_PYQTGRAPH:
            if self.h1_tab["plot"]:
                self.h1_tab["plot"].scene().sigMouseClicked.connect(
                    lambda evt: self._on_plot_clicked(evt, self.h1_tab, "1H")
                )
            if self.c13_tab["plot"]:
                self.c13_tab["plot"].scene().sigMouseClicked.connect(
                    lambda evt: self._on_plot_clicked(evt, self.c13_tab, "13C")
                )
            if self.ir_tab["plot"]:
                self.ir_tab["plot"].scene().sigMouseClicked.connect(
                    lambda evt: self._on_ir_clicked(evt)
                )

    def _create_plot_tab(self, title: str, x_label: str,
                          inverted_x: bool = True) -> dict:
        """Create a plot tab with controls."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        if not _HAS_PYQTGRAPH:
            placeholder = QLabel(
                f"📦 pyqtgraph not installed — {title} plot unavailable.\n"
                "Install with: pip install pyqtgraph"
            )
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 40px;")
            layout.addWidget(placeholder)
            return {"widget": widget, "plot": None, "view": None}

        # Plot widget
        plot_widget = pg.PlotWidget()
        plot_item = plot_widget.getPlotItem()
        plot_item.setLabel("bottom", x_label)
        plot_item.setLabel("left", "Intensity")
        plot_item.showGrid(x=True, y=True, alpha=0.15)

        if inverted_x:
            plot_item.invertX(True)

        # Style axes
        for axis_name in ["bottom", "left"]:
            axis = plot_item.getAxis(axis_name)
            axis.setStyle(tickFont=QFont(FONT_FAMILY, 9))
            axis.setPen(pg.mkPen(Colors.TEXT_TERTIARY, width=1))

        layout.addWidget(plot_widget)

        # Controls bar
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.setContentsMargins(4, 4, 4, 4)

        zoom_fit = QPushButton("Fit View")
        zoom_fit.setMaximumWidth(90)
        zoom_fit.setCursor(Qt.PointingHandCursor)
        zoom_fit.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                border-color: {Colors.BORDER_ACTIVE};
            }}
        """)
        zoom_fit.clicked.connect(lambda: plot_item.autoRange())
        controls.addWidget(zoom_fit)

        controls.addStretch()

        info_label = QLabel("")
        info_label.setObjectName("secondaryLabel")
        controls.addWidget(info_label)

        layout.addLayout(controls)

        return {
            "widget": widget,
            "plot": plot_widget,
            "view": plot_item,
            "info": info_label,
        }

    # ── Plot rendering methods ────────────────────────────────────────────────

    def plot_h1_nmr(self, nmr_data: NMRData):
        """Render ¹H NMR with filled Lorentzian envelope and stick markers."""
        tab = self.h1_tab
        if tab["plot"] is None or not _HAS_NUMPY:
            return

        view = tab["view"]
        view.clear()
        self._h1_peaks = [p.chemical_shift for p in nmr_data.peaks]
        self._h1_highlight_items = []

        if not nmr_data.peaks:
            return

        accent = QColor(Colors.PLOT_H1)

        # ── Lorentzian envelope (filled) ──────────────────────────────────────
        try:
            from ..core.nmr_data import NMRSpectrum
            spectrum = NMRSpectrum.from_nmr_data(nmr_data, num_points=6000, line_width=1.2)
            if spectrum.x_ppm and spectrum.y_intensity:
                x_arr = np.array(spectrum.x_ppm)
                y_arr = np.array(spectrum.y_intensity)
                max_int = max(
                    (p.integration for p in nmr_data.peaks if p.integration > 0),
                    default=1.0,
                )
                y_arr = y_arr * max_int

                # Filled envelope
                fill_color = QColor(accent)
                fill_color.setAlpha(28)
                fill = pg.FillBetweenItem(
                    pg.PlotDataItem(x_arr, y_arr),
                    pg.PlotDataItem(x_arr, np.zeros_like(y_arr)),
                    brush=pg.mkBrush(fill_color),
                )
                fill.setZValue(-2)
                view.addItem(fill)

                # Envelope outline
                env_color = QColor(accent)
                env_color.setAlpha(140)
                view.plot(x_arr, y_arr, pen=pg.mkPen(env_color, width=1.5))
        except Exception:
            pass

        # ── Stick peaks ───────────────────────────────────────────────────────
        for peak in nmr_data.peaks:
            intensity = peak.integration if peak.integration > 0 else 1.0
            # Gradient stick: stronger colour at top
            stick_color = QColor(accent)
            stick_color.setAlpha(200)
            x = [peak.chemical_shift, peak.chemical_shift]
            y = [0, intensity]
            view.plot(x, y, pen=pg.mkPen(stick_color, width=2))

            # Small dot at peak tip
            dot = pg.ScatterPlotItem(
                [peak.chemical_shift], [intensity],
                size=6, pen=pg.mkPen(None),
                brush=pg.mkBrush(accent),
            )
            dot.setZValue(5)
            view.addItem(dot)

        # ── Smart labels (staggered to avoid overlap) ─────────────────────────
        shifts = [p.chemical_shift for p in nmr_data.peaks]
        integ = [p.integration if p.integration > 0 else 1.0 for p in nmr_data.peaks]
        tiers = _stagger_labels(shifts, min_gap=0.25)
        offsets = [0.08, 0.22, 0.36]  # Y-offset per tier (fraction of max)
        max_y = max(integ) if integ else 1.0

        for i, peak in enumerate(nmr_data.peaks):
            intensity = integ[i]
            tier = tiers[i]
            y_off = intensity + offsets[tier] * max_y

            mult_str = f" ({peak.multiplicity})" if peak.multiplicity and peak.multiplicity != "s" else ""
            label_str = f"δ {peak.chemical_shift:.2f}{mult_str}"

            text = pg.TextItem(
                label_str,
                color=Colors.TEXT_SECONDARY,
                anchor=(0.5, 1.0),
            )
            text.setFont(QFont(FONT_FAMILY, 8))
            text.setPos(peak.chemical_shift, y_off)
            text.setZValue(6)
            view.addItem(text)

        # ── Region shading ────────────────────────────────────────────────────
        self._add_region(view, 6.0, 9.5, Colors.REGION_AROMATIC, "Aromatic")
        self._add_region(view, 0.0, 4.5, Colors.REGION_ALIPHATIC, "Aliphatic")

        view.autoRange()
        # Add a little padding top
        y_range = view.viewRange()[1]
        view.setYRange(y_range[0], y_range[1] * 1.35, padding=0)

        tab["info"].setText(
            f"{nmr_data.peak_count} peaks | {nmr_data.frequency} MHz | {nmr_data.solvent}"
        )
        self.tabs.setCurrentIndex(0)

    def plot_c13_nmr(self, nmr_data: NMRData):
        """Render ¹³C NMR with filled envelope and stick markers."""
        tab = self.c13_tab
        if tab["plot"] is None or not _HAS_NUMPY:
            return

        view = tab["view"]
        view.clear()
        self._c13_peaks = [p.chemical_shift for p in nmr_data.peaks]
        self._c13_highlight_items = []

        if not nmr_data.peaks:
            return

        accent = QColor(Colors.PLOT_C13)

        # ── Lorentzian envelope ───────────────────────────────────────────────
        try:
            from ..core.nmr_data import NMRSpectrum
            spectrum = NMRSpectrum.from_nmr_data(nmr_data, num_points=6000, line_width=2.0)
            if spectrum.x_ppm and spectrum.y_intensity:
                x_arr = np.array(spectrum.x_ppm)
                y_arr = np.array(spectrum.y_intensity)

                fill_color = QColor(accent)
                fill_color.setAlpha(22)
                fill = pg.FillBetweenItem(
                    pg.PlotDataItem(x_arr, y_arr),
                    pg.PlotDataItem(x_arr, np.zeros_like(y_arr)),
                    brush=pg.mkBrush(fill_color),
                )
                fill.setZValue(-2)
                view.addItem(fill)

                env_color = QColor(accent)
                env_color.setAlpha(120)
                view.plot(x_arr, y_arr, pen=pg.mkPen(env_color, width=1.5))
        except Exception:
            pass

        # ── Stick peaks ───────────────────────────────────────────────────────
        for peak in nmr_data.peaks:
            stick_color = QColor(accent)
            stick_color.setAlpha(200)
            view.plot(
                [peak.chemical_shift, peak.chemical_shift],
                [0, 1.0],
                pen=pg.mkPen(stick_color, width=2),
            )
            dot = pg.ScatterPlotItem(
                [peak.chemical_shift], [1.0],
                size=5, pen=pg.mkPen(None), brush=pg.mkBrush(accent),
            )
            dot.setZValue(5)
            view.addItem(dot)

        # ── Smart labels ──────────────────────────────────────────────────────
        shifts = [p.chemical_shift for p in nmr_data.peaks]
        tiers = _stagger_labels(shifts, min_gap=3.0)
        offsets = [1.06, 1.18, 1.30]

        for i, peak in enumerate(nmr_data.peaks):
            tier = tiers[i]
            text = pg.TextItem(
                f"{peak.chemical_shift:.1f}",
                color=Colors.TEXT_SECONDARY,
                anchor=(0.5, 1.0),
            )
            text.setFont(QFont(FONT_FAMILY, 7))
            text.setPos(peak.chemical_shift, offsets[tier])
            text.setZValue(6)
            view.addItem(text)

        # Region shading
        self._add_region(view, 100, 160, Colors.REGION_AROMATIC, "Aromatic")
        self._add_region(view, 0, 80, Colors.REGION_ALIPHATIC, "Aliphatic")
        self._add_region(view, 160, 220, Colors.REGION_CARBONYL, "Carbonyl")

        view.autoRange()
        y_range = view.viewRange()[1]
        view.setYRange(y_range[0], y_range[1] * 1.25, padding=0)

        tab["info"].setText(
            f"{nmr_data.peak_count} peaks | {nmr_data.frequency} MHz | {nmr_data.solvent}"
        )

    def plot_ir(self, ir_data: IRData):
        """Render IR absorption spectrum with envelope and functional group labels."""
        tab = self.ir_tab
        if tab["plot"] is None:
            return

        view = tab["view"]
        view.clear()
        self._ir_bands = [(a.wavenumber, a.assignment) for a in ir_data.absorptions]
        self._ir_highlight_items = []

        if not ir_data.absorptions:
            return

        accent = QColor(Colors.PLOT_IR)

        # ── Synthetic Lorentzian envelope ─────────────────────────────────────
        if _HAS_NUMPY and ir_data.absorptions:
            wns = [a.wavenumber for a in ir_data.absorptions]
            x_min = min(wns) - 200
            x_max = max(wns) + 200
            x_arr = np.linspace(x_min, x_max, 4000)
            y_arr = np.zeros_like(x_arr)
            lw = 15.0  # ~15 cm-1 line width
            for ab in ir_data.absorptions:
                y_arr += (lw ** 2) / ((x_arr - ab.wavenumber) ** 2 + lw ** 2)
            if y_arr.max() > 0:
                y_arr = y_arr / y_arr.max()

            fill_color = QColor(accent)
            fill_color.setAlpha(25)
            fill = pg.FillBetweenItem(
                pg.PlotDataItem(x_arr, y_arr),
                pg.PlotDataItem(x_arr, np.zeros_like(y_arr)),
                brush=pg.mkBrush(fill_color),
            )
            fill.setZValue(-2)
            view.addItem(fill)

            env_color = QColor(accent)
            env_color.setAlpha(140)
            view.plot(x_arr, y_arr, pen=pg.mkPen(env_color, width=1.5))

        # ── Sticks + labels ───────────────────────────────────────────────────
        shifts = [a.wavenumber for a in ir_data.absorptions]
        tiers = _stagger_labels(shifts, min_gap=60.0)
        offsets = [1.06, 1.18, 1.30]

        for i, absorption in enumerate(ir_data.absorptions):
            stick_color = QColor(accent)
            stick_color.setAlpha(200)
            view.plot(
                [absorption.wavenumber, absorption.wavenumber],
                [0, 1.0],
                pen=pg.mkPen(stick_color, width=2),
            )
            dot = pg.ScatterPlotItem(
                [absorption.wavenumber], [1.0],
                size=5, pen=pg.mkPen(None), brush=pg.mkBrush(accent),
            )
            dot.setZValue(5)
            view.addItem(dot)

            tier = tiers[i]
            label_str = f"{absorption.wavenumber:.0f}"
            if absorption.assignment:
                label_str += f" ({absorption.assignment})"
            text = pg.TextItem(
                label_str,
                color=Colors.TEXT_SECONDARY,
                anchor=(0.5, 1.0),
            )
            text.setFont(QFont(FONT_FAMILY, 7))
            text.setPos(absorption.wavenumber, offsets[tier])
            text.setZValue(6)
            view.addItem(text)

        view.autoRange()
        y_range = view.viewRange()[1]
        view.setYRange(y_range[0], y_range[1] * 1.25, padding=0)
        tab["info"].setText(f"{ir_data.band_count} bands | {ir_data.method}")

    def clear_all(self):
        """Clear all spectrum plots."""
        for tab in [self.h1_tab, self.c13_tab, self.ir_tab, self.uv_tab]:
            if tab.get("view"):
                tab["view"].clear()
            if tab.get("info"):
                tab["info"].setText("")
        self._h1_peaks = []
        self._c13_peaks = []
        self._ir_bands = []
        self._h1_highlight_items = []
        self._c13_highlight_items = []
        self._ir_highlight_items = []

    def _add_region(self, view, x_min, x_max, color_str, label=""):
        """Add a semi-transparent region overlay."""
        if not _HAS_PYQTGRAPH:
            return
        try:
            region = pg.LinearRegionItem(
                [x_min, x_max],
                movable=False,
                brush=pg.mkBrush(color_str),
            )
            region.setZValue(-10)
            view.addItem(region)
        except Exception:
            pass

    # ── Peak click detection ──────────────────────────────────────────────────

    def _on_plot_clicked(self, event, tab: dict, nucleus: str):
        """Handle click on a spectrum plot — find nearest peak and emit signal."""
        if not _HAS_PYQTGRAPH or tab["view"] is None:
            return
        pos = event.scenePos()
        mouse_point = tab["view"].vb.mapSceneToView(pos)
        click_x = mouse_point.x()

        peaks = self._h1_peaks if nucleus == "1H" else self._c13_peaks
        if not peaks:
            # Click on empty plot — clear any lingering highlights
            self.clear_peak_highlights()
            return

        tolerance = 0.3 if nucleus == "1H" else 2.0
        best_shift = None
        best_dist = float("inf")
        for shift in peaks:
            dist = abs(shift - click_x)
            if dist < best_dist:
                best_dist = dist
                best_shift = shift

        if best_shift is not None and best_dist <= tolerance:
            # Clear old highlights before emitting new click
            self.clear_peak_highlights()
            self.peak_clicked.emit(best_shift, nucleus)
        else:
            # Clicked on background (not near a peak) — clear highlights
            self.clear_peak_highlights()

    def _on_ir_clicked(self, event):
        """Handle click on IR spectrum — find nearest band and emit signal."""
        if not _HAS_PYQTGRAPH or self.ir_tab["view"] is None:
            return
        pos = event.scenePos()
        mouse_point = self.ir_tab["view"].vb.mapSceneToView(pos)
        click_x = mouse_point.x()

        if not self._ir_bands:
            self.clear_peak_highlights()
            return

        tolerance = 50.0
        best = None
        best_dist = float("inf")
        for wn, assign in self._ir_bands:
            dist = abs(wn - click_x)
            if dist < best_dist:
                best_dist = dist
                best = (wn, assign)

        if best is not None and best_dist <= tolerance:
            self.clear_peak_highlights()
            self.ir_band_clicked.emit(best[0], best[1])
        else:
            self.clear_peak_highlights()

    # ── Peak highlight (for correlation) ──────────────────────────────────────

    def highlight_peak(self, shift: float, nucleus: str, color: str = "#EC4899"):
        """
        Highlight a peak on the spectrum with a soft glow band.
        """
        if not _HAS_PYQTGRAPH or not _HAS_NUMPY:
            return

        if nucleus == "1H":
            tab = self.h1_tab
            items = self._h1_highlight_items
            self.tabs.setCurrentIndex(0)
            band_width = 0.12
        elif nucleus == "13C":
            tab = self.c13_tab
            items = self._c13_highlight_items
            self.tabs.setCurrentIndex(1)
            band_width = 1.5
        else:
            return

        if tab["view"] is None:
            return
        view = tab["view"]

        # Soft glow band (narrow Gaussian fill region)
        x_band = np.linspace(shift - band_width * 4, shift + band_width * 4, 200)
        y_range = view.viewRange()[1]
        y_max = y_range[1] if y_range[1] > 0 else 1.0
        y_band = y_max * np.exp(-0.5 * ((x_band - shift) / band_width) ** 2)

        glow_color = QColor(color)
        glow_color.setAlpha(50)
        fill = pg.FillBetweenItem(
            pg.PlotDataItem(x_band, y_band),
            pg.PlotDataItem(x_band, np.zeros_like(y_band)),
            brush=pg.mkBrush(glow_color),
        )
        fill.setZValue(8)
        view.addItem(fill)
        items.append(fill)

        # Thin solid center line
        line_color = QColor(color)
        line_color.setAlpha(180)
        line = pg.InfiniteLine(pos=shift, angle=90, pen=pg.mkPen(line_color, width=1.5))
        line.setZValue(9)
        view.addItem(line)
        items.append(line)

        # Inverted-triangle marker at top
        marker = pg.ScatterPlotItem(
            [shift], [y_max * 0.97],
            size=10, symbol='t',
            pen=pg.mkPen(color, width=1.5),
            brush=pg.mkBrush(color),
        )
        marker.setZValue(12)
        view.addItem(marker)
        items.append(marker)

    def highlight_ir_band(self, wavenumber: float, color: str = "#F59E0B"):
        """Highlight an IR band with a glow marker."""
        if not _HAS_PYQTGRAPH or not _HAS_NUMPY:
            return

        tab = self.ir_tab
        if tab["view"] is None:
            return
        view = tab["view"]
        self.tabs.setCurrentIndex(2)

        band_width = 20.0
        x_band = np.linspace(wavenumber - band_width * 4, wavenumber + band_width * 4, 200)
        y_range = view.viewRange()[1]
        y_max = y_range[1] if y_range[1] > 0 else 1.0
        y_band = y_max * np.exp(-0.5 * ((x_band - wavenumber) / band_width) ** 2)

        glow_color = QColor(color)
        glow_color.setAlpha(50)
        fill = pg.FillBetweenItem(
            pg.PlotDataItem(x_band, y_band),
            pg.PlotDataItem(x_band, np.zeros_like(y_band)),
            brush=pg.mkBrush(glow_color),
        )
        fill.setZValue(8)
        view.addItem(fill)
        self._ir_highlight_items.append(fill)

        line_color = QColor(color)
        line_color.setAlpha(180)
        line = pg.InfiniteLine(pos=wavenumber, angle=90, pen=pg.mkPen(line_color, width=1.5))
        line.setZValue(9)
        view.addItem(line)
        self._ir_highlight_items.append(line)

        marker = pg.ScatterPlotItem(
            [wavenumber], [y_max * 0.97],
            size=10, symbol='t',
            pen=pg.mkPen(color, width=1.5),
            brush=pg.mkBrush(color),
        )
        marker.setZValue(12)
        view.addItem(marker)
        self._ir_highlight_items.append(marker)

    def clear_peak_highlights(self):
        """Remove all peak highlight markers."""
        if not _HAS_PYQTGRAPH:
            return
        self._clear_highlight_items(self._h1_highlight_items, self.h1_tab)
        self._h1_highlight_items = []
        self._clear_highlight_items(self._c13_highlight_items, self.c13_tab)
        self._c13_highlight_items = []
        self._clear_highlight_items(self._ir_highlight_items, self.ir_tab)
        self._ir_highlight_items = []

    def _clear_highlight_items(self, items: list, tab: dict):
        if tab.get("view") is None:
            return
        for item in items:
            try:
                tab["view"].removeItem(item)
            except Exception:
                pass
