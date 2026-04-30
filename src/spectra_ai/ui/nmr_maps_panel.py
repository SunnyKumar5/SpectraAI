"""
NMRMapsPanel -- 2D NMR correlation maps (predicted COSY, HSQC, HMBC).

Each experiment type is rendered as a pyqtgraph scatter-plot + data table
inside a tabbed interface.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFrame, QSizePolicy, QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QBrush

from .styles.colors import Colors, FONT_FAMILY, FONT_MONO

try:
    import pyqtgraph as pg
    _HAS_PG = True
except ImportError:
    _HAS_PG = False

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

from ..chem.nmr_correlations import Correlation, CorrelationMap


# ======================================================================
#  CorrelationPlot
# ======================================================================

class CorrelationPlot(QWidget):
    """pyqtgraph-based 2D scatter plot for one experiment type."""

    correlation_clicked = pyqtSignal(object)   # Correlation
    correlation_hovered = pyqtSignal(object)   # Correlation | None

    def __init__(self, corr_type: str = "COSY", parent=None):
        super().__init__(parent)
        self._corr_type = corr_type
        self._correlations: list[Correlation] = []
        self._scatter: object = None
        self._selected_idx: int = -1
        self._ref_lines: list = []
        self._highlight_item: object = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _HAS_PG:
            self._pw = pg.PlotWidget()
            self._pw.setBackground(QColor(Colors.BG_DARK))
            self._pw.getAxis("bottom").setTextPen(QColor(Colors.TEXT_SECONDARY))
            self._pw.getAxis("left").setTextPen(QColor(Colors.TEXT_SECONDARY))
            self._pw.getAxis("bottom").setPen(QColor(Colors.BORDER))
            self._pw.getAxis("left").setPen(QColor(Colors.BORDER))
            self._pw.showGrid(x=True, y=True, alpha=0.15)
            self._pw.setLabel("bottom", "")
            self._pw.setLabel("left", "")
            self._pw.scene().sigMouseMoved.connect(self._on_mouse_moved)
            layout.addWidget(self._pw)
        else:
            lbl = QLabel("pyqtgraph required for 2D NMR maps")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            layout.addWidget(lbl)
            self._pw = None

        # Tooltip overlay
        self._tooltip = QLabel(self)
        self._tooltip.setStyleSheet(f"""
            QLabel {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.ACCENT_CYAN};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                color: {Colors.TEXT_PRIMARY};
                font-family: '{FONT_MONO}';
            }}
        """)
        self._tooltip.hide()
        self._tooltip.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Legend overlay
        self._legend = QLabel(self)
        self._legend.setStyleSheet(f"""
            QLabel {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 9px;
                color: {Colors.TEXT_SECONDARY};
                font-family: '{FONT_FAMILY}';
            }}
        """)
        self._legend.hide()
        self._update_legend()

        # Empty-state label
        self._empty_label = QLabel(self)
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 13px; padding: 40px;"
        )
        self._empty_label.hide()

    def set_correlations(self, correlations: list[Correlation],
                         h_range: tuple, y_range: tuple,
                         h_label: str, y_label: str):
        self._correlations = correlations
        if not self._pw:
            return

        self._pw.clear()
        self._ref_lines.clear()
        self._selected_idx = -1

        if not correlations:
            return

        self._pw.setLabel("bottom", h_label)
        self._pw.setLabel("left", y_label)

        # Axis ranges (inverted for NMR)
        if h_range[0] > h_range[1]:
            self._pw.invertX(True)
        if y_range[0] > y_range[1]:
            self._pw.invertY(True)

        # Reference lines
        self._draw_reference_lines(correlations)

        # Build scatter data grouped by visual style
        groups = self._group_by_style(correlations)
        for style_key, indices in groups.items():
            xs = [correlations[i].h_shift for i in indices]
            ys = [correlations[i].x_shift for i in indices]
            symbol, size, brush_color, pen_color, pen_w = style_key

            spots = []
            for k, i in enumerate(indices):
                c = correlations[i]
                alpha = self._confidence_alpha(c.confidence)
                br = QColor(brush_color)
                br.setAlpha(alpha)
                pn = pg.mkPen(color=pen_color, width=pen_w)
                spots.append({
                    "pos": (c.h_shift, c.x_shift),
                    "size": size,
                    "symbol": symbol,
                    "brush": br,
                    "pen": pn,
                    "data": i,
                })

            scatter = pg.ScatterPlotItem(spots)
            scatter.sigClicked.connect(self._on_scatter_clicked)
            self._pw.addItem(scatter)

        self._pw.autoRange()
        self._update_legend()
        self._legend.show()
        self._position_legend()

    def show_empty(self, message: str):
        self._empty_label.setText(message)
        self._empty_label.show()
        self._empty_label.setGeometry(0, 0, self.width(), self.height())
        self._legend.hide()
        if self._pw:
            self._pw.clear()

    def hide_empty(self):
        self._empty_label.hide()

    def highlight_by_shift(self, h_shift: float, x_shift: float):
        """Externally highlight a correlation near (h_shift, x_shift)."""
        if not self._pw or not _HAS_PG:
            return
        tol_h = 0.3
        tol_x = 2.0 if self._corr_type != "COSY" else 0.3
        for i, c in enumerate(self._correlations):
            if abs(c.h_shift - h_shift) <= tol_h and abs(c.x_shift - x_shift) <= tol_x:
                self._selected_idx = i
                self._draw_highlight(c.h_shift, c.x_shift)
                break

    def _draw_highlight(self, hx: float, hy: float):
        """Draw a pulsing ring around the highlighted point."""
        if not self._pw or not _HAS_PG:
            return
        # Remove previous highlight
        if hasattr(self, "_highlight_item") and self._highlight_item is not None:
            self._pw.removeItem(self._highlight_item)
        ring = pg.ScatterPlotItem(
            [hx], [hy], size=22, symbol="o",
            pen=pg.mkPen(color=QColor(Colors.ACCENT_CYAN), width=2),
            brush=pg.mkBrush(0, 0, 0, 0),
        )
        self._pw.addItem(ring)
        self._highlight_item = ring

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_legend()
        if self._empty_label.isVisible():
            self._empty_label.setGeometry(0, 0, self.width(), self.height())

    # -- internals --

    def _draw_reference_lines(self, correlations: list[Correlation]):
        if not self._pw:
            return
        pen = pg.mkPen(color=QColor(Colors.BORDER), width=1, style=Qt.DashLine)

        if self._corr_type == "COSY":
            # Diagonal y=x
            shifts = [c.h_shift for c in correlations]
            if shifts:
                lo, hi = min(shifts) - 1, max(shifts) + 1
                line = pg.PlotDataItem([lo, hi], [lo, hi], pen=pg.mkPen(
                    color=QColor(Colors.TEXT_MUTED), width=1, style=Qt.DashLine
                ))
                self._pw.addItem(line)
                self._ref_lines.append(line)
        else:
            # Grid lines at each unique shift
            h_shifts = sorted(set(c.h_shift for c in correlations))
            y_shifts = sorted(set(c.x_shift for c in correlations))
            for s in h_shifts:
                line = pg.InfiniteLine(pos=s, angle=90, pen=pen)
                self._pw.addItem(line)
                self._ref_lines.append(line)
            for s in y_shifts:
                line = pg.InfiniteLine(pos=s, angle=0, pen=pen)
                self._pw.addItem(line)
                self._ref_lines.append(line)

    def _group_by_style(self, correlations: list[Correlation]) -> dict:
        """Group correlation indices by their visual style key."""
        groups: dict[tuple, list[int]] = {}
        for i, c in enumerate(correlations):
            key = self._style_for(c)
            groups.setdefault(key, []).append(i)
        return groups

    def _style_for(self, c: Correlation) -> tuple:
        """Return (symbol, size, brush_color, pen_color, pen_width)."""
        if c.corr_type == "COSY":
            if c.is_diagonal:
                return ("o", 14, Colors.ACCENT_CYAN, Colors.ACCENT_CYAN, 1.5)
            return ("o", 10, Colors.ACCENT_BLUE, Colors.ACCENT_BLUE, 1.0)
        elif c.corr_type == "HSQC":
            return ("s", 10, Colors.ACCENT_GREEN, Colors.ACCENT_GREEN, 1.0)
        else:  # HMBC
            if c.bond_path == 2:
                return ("t", 10, Colors.ACCENT_AMBER, Colors.ACCENT_AMBER, 1.2)
            return ("t1", 10, Colors.ACCENT_PURPLE, Colors.ACCENT_PURPLE, 1.2)

    @staticmethod
    def _confidence_alpha(confidence: str) -> int:
        return {"High": 204, "Medium": 128, "Low": 64}.get(confidence, 128)

    def _on_scatter_clicked(self, scatter_item, points, ev=None):
        if points is None or len(points) == 0:
            return
        pt = points[0]
        idx = pt.data()
        if idx is not None and 0 <= idx < len(self._correlations):
            self._selected_idx = idx
            self.correlation_clicked.emit(self._correlations[idx])

    def _on_mouse_moved(self, scene_pos):
        if not self._pw or not self._correlations:
            self._tooltip.hide()
            return

        vb = self._pw.plotItem.vb
        mouse_point = vb.mapSceneToView(scene_pos)
        mx, my = mouse_point.x(), mouse_point.y()

        # Find nearest correlation within tolerance
        best_i, best_dist = -1, float("inf")
        # Scale tolerance to axis range
        x_range = self._pw.viewRange()[0]
        y_range = self._pw.viewRange()[1]
        tol_x = (x_range[1] - x_range[0]) * 0.03 if x_range[1] != x_range[0] else 0.5
        tol_y = (y_range[1] - y_range[0]) * 0.03 if y_range[1] != y_range[0] else 0.5

        for i, c in enumerate(self._correlations):
            dx = (c.h_shift - mx) / tol_x if tol_x else 0
            dy = (c.x_shift - my) / tol_y if tol_y else 0
            d = dx * dx + dy * dy
            if d < best_dist:
                best_dist = d
                best_i = i

        if best_i >= 0 and best_dist < 1.0:
            c = self._correlations[best_i]
            self._tooltip.setText(self._tooltip_text(c))
            self._tooltip.adjustSize()
            # Position near the mouse in widget coords
            widget_pos = self._pw.mapFromScene(scene_pos)
            tx = min(widget_pos.x() + 14, self.width() - self._tooltip.width() - 4)
            ty = max(widget_pos.y() - self._tooltip.height() - 4, 4)
            self._tooltip.move(int(tx), int(ty))
            self._tooltip.show()
        else:
            self._tooltip.hide()

    def _tooltip_text(self, c: Correlation) -> str:
        lines = []
        if self._corr_type == "COSY":
            lines.append(f"{c.h_label} ({c.h_shift:.2f}) \u2194 {c.x_label} ({c.x_shift:.2f})")
            if c.is_diagonal:
                lines.append("Diagonal peak")
            else:
                lines.append("Cross-peak (vicinal coupling)")
        elif self._corr_type == "HSQC":
            lines.append(f"{c.h_label} ({c.h_shift:.2f}) \u2192 {c.x_label} ({c.x_shift:.1f})")
            lines.append("Direct 1-bond C\u2013H")
        else:
            lines.append(f"{c.h_label} ({c.h_shift:.2f}) \u2192 {c.x_label} ({c.x_shift:.1f})")
            lines.append(f"{c.bond_path}-bond long-range")
        lines.append(f"Confidence: {c.confidence}")
        return "\n".join(lines)

    def _update_legend(self):
        if self._corr_type == "COSY":
            self._legend.setText(
                "<span style='color:%s'>&#9679;</span> Diagonal  "
                "<span style='color:%s'>&#9679;</span> Coupling"
                % (Colors.ACCENT_CYAN, Colors.ACCENT_BLUE)
            )
        elif self._corr_type == "HSQC":
            self._legend.setText(
                "<span style='color:%s'>&#9632;</span> 1-bond C-H"
                % Colors.ACCENT_GREEN
            )
        else:
            self._legend.setText(
                "<span style='color:%s'>&#9650;</span> 2-bond  "
                "<span style='color:%s'>&#9660;</span> 3-bond"
                % (Colors.ACCENT_AMBER, Colors.ACCENT_PURPLE)
            )

    def _position_legend(self):
        self._legend.adjustSize()
        self._legend.move(self.width() - self._legend.width() - 8, 8)


# ======================================================================
#  CorrelationTable
# ======================================================================

class CorrelationTable(QWidget):
    """Tabular display of correlations for one experiment type."""

    row_clicked = pyqtSignal(object)  # Correlation

    def __init__(self, corr_type: str = "COSY", parent=None):
        super().__init__(parent)
        self._corr_type = corr_type
        self._correlations: list[Correlation] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Filter row
        filt = QHBoxLayout()
        filt.setContentsMargins(4, 2, 4, 2)
        for conf_name in ("High", "Medium", "Low"):
            cb = QCheckBox(conf_name)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
            cb.stateChanged.connect(self._apply_filter)
            filt.addWidget(cb)
            setattr(self, f"_filt_{conf_name.lower()}", cb)
        filt.addStretch()
        layout.addLayout(filt)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {Colors.BG_DARK};
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BORDER};
                font-size: 11px;
            }}
            QTableWidget::item:selected {{
                background: {Colors.ACCENT_BLUE}30;
            }}
            QHeaderView::section {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                padding: 3px;
                font-size: 11px;
            }}
        """)
        self._table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self._table)

        self._setup_columns()

    def _setup_columns(self):
        if self._corr_type == "COSY":
            self._table.setColumnCount(5)
            self._table.setHorizontalHeaderLabels([
                "1H (ppm)", "Partner 1H", "H Label", "Partner", "Conf."
            ])
        elif self._corr_type == "HSQC":
            self._table.setColumnCount(5)
            self._table.setHorizontalHeaderLabels([
                "1H (ppm)", "13C (ppm)", "H Label", "C Label", "Conf."
            ])
        else:  # HMBC
            self._table.setColumnCount(6)
            self._table.setHorizontalHeaderLabels([
                "1H (ppm)", "13C (ppm)", "H Label", "C Label", "Bonds", "Conf."
            ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSortingEnabled(True)

    def set_correlations(self, correlations: list[Correlation]):
        self._correlations = correlations
        self._populate()

    def _populate(self):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        visible_conf = set()
        if self._filt_high.isChecked():
            visible_conf.add("High")
        if self._filt_medium.isChecked():
            visible_conf.add("Medium")
        if self._filt_low.isChecked():
            visible_conf.add("Low")

        filtered = [
            c for c in self._correlations
            if c.confidence in visible_conf and not c.is_diagonal
        ]

        self._table.setRowCount(len(filtered))
        conf_colors = {
            "High": Colors.ACCENT_GREEN,
            "Medium": Colors.ACCENT_AMBER,
            "Low": Colors.ACCENT_RED,
        }

        for row, c in enumerate(filtered):
            col = 0
            self._set_cell(row, col, f"{c.h_shift:.2f}"); col += 1
            self._set_cell(row, col, f"{c.x_shift:.2f}" if self._corr_type != "COSY"
                           else f"{c.x_shift:.2f}"); col += 1
            self._set_cell(row, col, c.h_label); col += 1
            self._set_cell(row, col, c.x_label); col += 1
            if self._corr_type == "HMBC":
                self._set_cell(row, col, str(c.bond_path)); col += 1

            # Confidence badge
            item = QTableWidgetItem(c.confidence[:3])
            item.setTextAlignment(Qt.AlignCenter)
            color = conf_colors.get(c.confidence, Colors.TEXT_SECONDARY)
            item.setForeground(QBrush(QColor(color)))
            self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)

    def _set_cell(self, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self._table.setItem(row, col, item)

    def _apply_filter(self, _state=None):
        self._populate()

    def _on_row_clicked(self, row: int, _col: int):
        # Map displayed row back to original correlation
        visible_conf = set()
        if self._filt_high.isChecked():
            visible_conf.add("High")
        if self._filt_medium.isChecked():
            visible_conf.add("Medium")
        if self._filt_low.isChecked():
            visible_conf.add("Low")
        filtered = [
            c for c in self._correlations
            if c.confidence in visible_conf and not c.is_diagonal
        ]
        if 0 <= row < len(filtered):
            self.row_clicked.emit(filtered[row])


# ======================================================================
#  NMRMapsPanel  (the outer container)
# ======================================================================

class NMRMapsPanel(QWidget):
    """
    Full 2D NMR correlation maps panel: COSY / HSQC / HMBC tabs.

    Signals
    -------
    correlation_clicked(Correlation)
        For 3D viewer wiring.
    """

    correlation_clicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._maps: dict[str, CorrelationMap] = {}
        self._plots: dict[str, CorrelationPlot] = {}
        self._tables: dict[str, CorrelationTable] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Info banner (shown when no data)
        self._info_banner = QLabel(
            "Run analysis to generate predicted COSY, HSQC, and HMBC maps.\n"
            "Predictions are based on molecular structure + 1D NMR assignments."
        )
        self._info_banner.setAlignment(Qt.AlignCenter)
        self._info_banner.setWordWrap(True)
        self._info_banner.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-style: italic;
                padding: 20px;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self._info_banner)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {Colors.BORDER};
                background: {Colors.BG_DARK};
            }}
            QTabBar::tab {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                padding: 6px 14px;
                border: 1px solid {Colors.BORDER};
                border-bottom: none;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background: {Colors.BG_DARK};
                color: {Colors.TEXT_PRIMARY};
                border-bottom: 2px solid {Colors.ACCENT_CYAN};
            }}
        """)
        layout.addWidget(self._tabs)
        self._tabs.hide()

        self._help_labels: dict[str, QLabel] = {}

        _HELP_TEXT = {
            "COSY": (
                "<b>COSY (1H\u20131H Correlation Spectroscopy)</b> shows which protons are "
                "coupled to each other (typically 2\u20133 bonds apart). "
                "<span style='color:%s'>\u25CF Diagonal peaks</span> mark each proton's own "
                "chemical shift. <span style='color:%s'>\u25CF Cross-peaks</span> reveal "
                "coupling partners \u2014 if two protons share a cross-peak, they are on "
                "adjacent carbons. Higher confidence = stronger expected coupling."
                % (Colors.ACCENT_CYAN, Colors.ACCENT_BLUE)
            ),
            "HSQC": (
                "<b>HSQC (1H\u201313C Single-Quantum Coherence)</b> maps each proton to "
                "the carbon it is directly bonded to (1-bond correlation). "
                "<span style='color:%s'>\u25A0 Each point</span> pairs a 1H shift (x) "
                "with a 13C shift (y). Use this to assign carbons to their attached "
                "protons and distinguish CH, CH2, and CH3 groups."
                % Colors.ACCENT_GREEN
            ),
            "HMBC": (
                "<b>HMBC (Heteronuclear Multiple-Bond Correlation)</b> shows long-range "
                "1H\u201313C correlations across 2\u20133 bonds, connecting protons to "
                "nearby quaternary carbons and heteroatoms. "
                "<span style='color:%s'>\u25B2 2-bond</span> and "
                "<span style='color:%s'>\u25BC 3-bond</span> paths help piece together "
                "the carbon skeleton beyond direct attachments."
                % (Colors.ACCENT_AMBER, Colors.ACCENT_PURPLE)
            ),
        }

        for corr_type, tab_label in [
            ("COSY", "COSY  1H-1H"),
            ("HSQC", "HSQC  1H-13C"),
            ("HMBC", "HMBC  Long-range"),
        ]:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.setSpacing(0)

            splitter = QSplitter(Qt.Horizontal)
            splitter.setStyleSheet(
                f"QSplitter::handle {{ background: {Colors.BORDER}; width: 1px; }}"
            )

            plot = CorrelationPlot(corr_type)
            plot.correlation_clicked.connect(self._on_plot_clicked)
            table = CorrelationTable(corr_type)
            table.row_clicked.connect(self._on_table_clicked)

            splitter.addWidget(plot)
            splitter.addWidget(table)
            splitter.setSizes([700, 300])

            tab_layout.addWidget(splitter, stretch=1)

            # "What does this mean?" toggle + help text
            help_row = QHBoxLayout()
            help_row.setContentsMargins(6, 2, 6, 0)
            help_btn = QPushButton("What does this mean?")
            help_btn.setFlat(True)
            help_btn.setCursor(Qt.PointingHandCursor)
            help_btn.setStyleSheet(
                f"color: {Colors.ACCENT_CYAN}; font-size: 10px; text-decoration: underline;"
                f" border: none; padding: 2px 0;"
            )
            help_row.addWidget(help_btn)
            help_row.addStretch()
            tab_layout.addLayout(help_row)

            help_label = QLabel(_HELP_TEXT[corr_type])
            help_label.setWordWrap(True)
            help_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; padding: 6px 10px;"
                f" background: {Colors.BG_ELEVATED}; border-top: 1px solid {Colors.BORDER};"
            )
            help_label.hide()
            tab_layout.addWidget(help_label)
            self._help_labels[corr_type] = help_label

            help_btn.clicked.connect(
                lambda checked, lbl=help_label: lbl.setVisible(not lbl.isVisible())
            )

            self._tabs.addTab(tab, tab_label)
            self._plots[corr_type] = plot
            self._tables[corr_type] = table

    # -- Public API --

    def load_maps(self, maps: dict[str, CorrelationMap]):
        self._maps = maps
        self._info_banner.hide()
        self._tabs.show()

        for corr_type in ("COSY", "HSQC", "HMBC"):
            cmap = maps.get(corr_type)
            plot = self._plots[corr_type]
            table = self._tables[corr_type]

            if cmap is None or (not cmap.correlations and cmap.message):
                plot.show_empty(cmap.message if cmap else "No data")
                table.set_correlations([])
            else:
                plot.hide_empty()
                plot.set_correlations(
                    cmap.correlations, cmap.h_range, cmap.y_range,
                    cmap.h_axis_label, cmap.y_axis_label,
                )
                table.set_correlations(cmap.correlations)

        # Update tab labels with counts
        for i, corr_type in enumerate(("COSY", "HSQC", "HMBC")):
            cmap = maps.get(corr_type)
            n = len(cmap.correlations) if cmap else 0
            base_labels = ["COSY  1H-1H", "HSQC  1H-13C", "HMBC  Long-range"]
            label = f"{base_labels[i]}  ({n})" if n else base_labels[i]
            self._tabs.setTabText(i, label)

    def clear(self):
        self._maps = {}
        for plot in self._plots.values():
            plot.show_empty("")
        for table in self._tables.values():
            table.set_correlations([])
        self._tabs.hide()
        self._info_banner.show()
        for i, lbl in enumerate(["COSY  1H-1H", "HSQC  1H-13C", "HMBC  Long-range"]):
            self._tabs.setTabText(i, lbl)

    def highlight_correlation(self, h_shift: float, x_shift: float,
                               corr_type: str):
        """Externally highlight a correlation in the given tab."""
        plot = self._plots.get(corr_type)
        if plot:
            plot.highlight_by_shift(h_shift, x_shift)
        # Switch to that tab
        type_to_idx = {"COSY": 0, "HSQC": 1, "HMBC": 2}
        idx = type_to_idx.get(corr_type, -1)
        if idx >= 0:
            self._tabs.setCurrentIndex(idx)

    def find_correlations_for_atom(self, atom_idx: int) -> list[Correlation]:
        """Find all correlations involving a given atom index."""
        results = []
        for cmap in self._maps.values():
            if not cmap:
                continue
            for c in cmap.correlations:
                if c.h_atom_idx == atom_idx or c.x_atom_idx == atom_idx:
                    results.append(c)
        return results

    # -- internals --

    def _on_plot_clicked(self, corr: Correlation):
        self._cross_highlight(corr)
        self.correlation_clicked.emit(corr)

    def _on_table_clicked(self, corr: Correlation):
        # Highlight in own plot
        plot = self._plots.get(corr.corr_type)
        if plot:
            plot.highlight_by_shift(corr.h_shift, corr.x_shift)
        self._cross_highlight(corr)
        self.correlation_clicked.emit(corr)

    def _cross_highlight(self, corr: Correlation):
        """Highlight related correlations in sibling tabs (same atom)."""
        atoms = set()
        if corr.h_atom_idx is not None:
            atoms.add(corr.h_atom_idx)
        if corr.x_atom_idx is not None:
            atoms.add(corr.x_atom_idx)
        if not atoms:
            return

        for ctype, cmap in self._maps.items():
            if ctype == corr.corr_type or cmap is None:
                continue
            plot = self._plots.get(ctype)
            if not plot:
                continue
            for c in cmap.correlations:
                if c.h_atom_idx in atoms or c.x_atom_idx in atoms:
                    plot.highlight_by_shift(c.h_shift, c.x_shift)
                    break  # highlight first match per tab
