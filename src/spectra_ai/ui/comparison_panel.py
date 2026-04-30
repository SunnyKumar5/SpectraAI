"""
ComparisonPanel -- Full-width comparison view for two compounds.

Shows dual 3D viewers, spectral overlay with delta brackets,
and dual validation radar overlay.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QTabWidget, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal

from .styles.colors import Colors, FONT_FAMILY

try:
    import pyqtgraph as pg
    _HAS_PG = True
except ImportError:
    _HAS_PG = False


class ComparisonPanel(QWidget):
    """
    Full comparison view for two compounds side by side.

    Signals
    -------
    exit_requested()
    swap_requested()
    compare_requested(str, str)   kept for legacy compat
    """

    exit_requested = pyqtSignal()
    swap_requested = pyqtSignal()
    compare_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._record_a = None
        self._record_b = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Header -----------------------------------------------------------
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)

        self._exit_btn = QPushButton("Exit Comparison")
        self._exit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {Colors.TEXT_SECONDARY};
                border: none; font-size: 13px; padding: 4px 12px;
            }}
            QPushButton:hover {{ color: {Colors.TEXT_PRIMARY}; }}
        """)
        self._exit_btn.clicked.connect(self.exit_requested.emit)
        hl.addWidget(self._exit_btn)

        hl.addStretch()

        self._name_a_label = QLabel("")
        self._name_a_label.setStyleSheet(
            f"color: {Colors.ACCENT_CYAN}; font-weight: 600; font-size: 14px;"
            f" border: none; background: transparent;"
        )
        hl.addWidget(self._name_a_label)

        vs = QLabel("  vs  ")
        vs.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 14px; border: none; background: transparent;"
        )
        hl.addWidget(vs)

        self._name_b_label = QLabel("")
        self._name_b_label.setStyleSheet(
            f"color: {Colors.ACCENT_PINK}; font-weight: 600; font-size: 14px;"
            f" border: none; background: transparent;"
        )
        hl.addWidget(self._name_b_label)

        hl.addStretch()

        self._swap_btn = QPushButton("Swap A/B")
        self._swap_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER}; border-radius: 4px;
                font-size: 12px; padding: 4px 12px;
            }}
            QPushButton:hover {{ color: {Colors.TEXT_PRIMARY}; border-color: {Colors.ACCENT_BLUE}; }}
        """)
        self._swap_btn.clicked.connect(self._on_swap)
        hl.addWidget(self._swap_btn)

        root.addWidget(header)

        # -- Body splitter (vertical) -----------------------------------------
        body_splitter = QSplitter(Qt.Vertical)
        body_splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER}; height: 2px; }}"
        )

        # -- Dual 3D viewers --------------------------------------------------
        viewer_row = QWidget()
        vr_layout = QHBoxLayout(viewer_row)
        vr_layout.setContentsMargins(0, 0, 0, 0)
        vr_layout.setSpacing(0)

        # Viewer A placeholder
        self._viewer_a_container = self._viewer_placeholder("A", Colors.ACCENT_CYAN)
        vr_layout.addWidget(self._viewer_a_container, 1)

        # Viewer B placeholder
        self._viewer_b_container = self._viewer_placeholder("B", Colors.ACCENT_PINK)
        vr_layout.addWidget(self._viewer_b_container, 1)

        body_splitter.addWidget(viewer_row)

        # -- Spectral overlay tabs --------------------------------------------
        self._spec_tabs = QTabWidget()
        self._spec_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-top: none;
            }}
            QTabBar::tab {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                padding: 6px 16px; font-size: 12px;
                border: 1px solid {Colors.BORDER};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background: {Colors.BG_DARK};
                color: {Colors.TEXT_PRIMARY};
                border-bottom: 2px solid {Colors.ACCENT_BLUE};
            }}
        """)

        for tab_name in ["H NMR", "13C NMR", "IR"]:
            tab = self._build_overlay_tab(tab_name)
            self._spec_tabs.addTab(tab, tab_name)

        body_splitter.addWidget(self._spec_tabs)

        # -- Validation comparison --------------------------------------------
        validation_row = QWidget()
        val_layout = QHBoxLayout(validation_row)
        val_layout.setContentsMargins(12, 8, 12, 8)
        val_layout.setSpacing(16)

        # Score comparison
        self._score_a_label = QLabel("")
        self._score_a_label.setAlignment(Qt.AlignCenter)
        self._score_a_label.setStyleSheet(
            f"color: {Colors.ACCENT_CYAN}; font-size: 24px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        val_layout.addWidget(self._score_a_label, 1)

        vs2 = QLabel("vs")
        vs2.setAlignment(Qt.AlignCenter)
        vs2.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 16px; border: none; background: transparent;"
        )
        val_layout.addWidget(vs2)

        self._score_b_label = QLabel("")
        self._score_b_label.setAlignment(Qt.AlignCenter)
        self._score_b_label.setStyleSheet(
            f"color: {Colors.ACCENT_PINK}; font-size: 24px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        val_layout.addWidget(self._score_b_label, 1)

        # Radar placeholder
        self._radar_container = QLabel("Radar overlay")
        self._radar_container.setAlignment(Qt.AlignCenter)
        self._radar_container.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 12px;"
            f" background: {Colors.BG_DARK}; border-radius: 8px;"
            f" min-height: 200px; border: none;"
        )
        val_layout.addWidget(self._radar_container, 2)

        body_splitter.addWidget(validation_row)
        body_splitter.setSizes([300, 300, 200])

        root.addWidget(body_splitter, 1)

        # -- Delta summary ----------------------------------------------------
        self._delta_summary = QLabel("")
        self._delta_summary.setAlignment(Qt.AlignRight)
        self._delta_summary.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; padding: 4px 12px;"
        )
        root.addWidget(self._delta_summary)

    # ── Public API ───────────────────────────────────────────────────────────

    def load_comparison(self, record_a, record_b):
        """Load two CompoundRecords and populate all sub-panels."""
        self._record_a = record_a
        self._record_b = record_b

        self._name_a_label.setText(record_a.display_name())
        self._name_b_label.setText(record_b.display_name())

        sa = record_a.overall_score()
        sb = record_b.overall_score()
        self._score_a_label.setText(f"{sa}" if sa is not None else "-")
        self._score_b_label.setText(f"{sb}" if sb is not None else "-")

        # Load 3D viewers
        self._load_viewer(self._viewer_a_container, record_a, Colors.ACCENT_CYAN)
        self._load_viewer(self._viewer_b_container, record_b, Colors.ACCENT_PINK)

        # Spectral overlay
        self._overlay_spectra(record_a, record_b)

        # Radar overlay
        self._overlay_radar(record_a, record_b)

    def clear(self):
        self._record_a = None
        self._record_b = None
        self._name_a_label.setText("")
        self._name_b_label.setText("")
        self._score_a_label.setText("")
        self._score_b_label.setText("")
        self._delta_summary.setText("")

    # Legacy API for back-compat
    def set_compound_list(self, names: list[str]):
        pass

    def set_comparison(self, left_html: str, right_html: str, diff_html: str):
        pass

    # ── Internal ─────────────────────────────────────────────────────────────

    def _on_swap(self):
        if self._record_a and self._record_b:
            self._record_a, self._record_b = self._record_b, self._record_a
            self.load_comparison(self._record_a, self._record_b)
            self.swap_requested.emit()

    def _viewer_placeholder(self, label: str, color: str) -> QWidget:
        w = QWidget()
        w.setMinimumHeight(200)
        w.setStyleSheet(f"""
            QWidget {{
                background: {Colors.BG_DARK};
                border-top: 2px solid {color};
            }}
        """)
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(f"3D Viewer {label}")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 14px; border: none; background: transparent;"
        )
        vl.addWidget(lbl)
        return w

    def _load_viewer(self, container: QWidget, record, color: str):
        """Load a MolecularViewer into the container for the given record."""
        # Clear existing
        layout = container.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        try:
            from .viewer.molecular_viewer import MolecularViewer
            viewer = MolecularViewer()
            layout.addWidget(viewer)
            if record.molecule and record.molecule.smiles:
                viewer.load_smiles(record.molecule.smiles)
        except Exception:
            lbl = QLabel("3D viewer unavailable")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: 12px; border: none; background: transparent;"
            )
            layout.addWidget(lbl)

    def _build_overlay_tab(self, tab_name: str) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)

        if _HAS_PG:
            plot = pg.PlotWidget()
            plot.setBackground(Colors.BG_DARK)
            plot.showGrid(x=True, y=True, alpha=0.15)
            plot.getAxis("bottom").setPen(Colors.TEXT_MUTED)
            plot.getAxis("left").setPen(Colors.TEXT_MUTED)
            if "H" in tab_name or "C" in tab_name:
                plot.invertX(True)
            plot.setLabel("bottom", "ppm" if "NMR" in tab_name or "H" in tab_name or "C" in tab_name else "cm-1")
            vl.addWidget(plot)
            # Store reference for later overlay
            setattr(self, f"_plot_{tab_name.replace(' ', '_')}", plot)
        else:
            lbl = QLabel("pyqtgraph not available for spectral overlay")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; border: none;")
            vl.addWidget(lbl)

        return w

    def _overlay_spectra(self, record_a, record_b):
        """Plot both compounds' spectral data on the same axes."""
        if not _HAS_PG:
            return

        # H1 NMR overlay
        plot = getattr(self, "_plot_H_NMR", None)
        if plot:
            plot.clear()
            self._plot_sticks(plot, record_a.h1_data, Colors.ACCENT_CYAN, "A")
            self._plot_sticks(plot, record_b.h1_data, Colors.ACCENT_PINK, "B")

        # C13 NMR overlay
        plot = getattr(self, "_plot_13C_NMR", None)
        if plot:
            plot.clear()
            self._plot_sticks(plot, record_a.c13_data, Colors.ACCENT_CYAN, "A")
            self._plot_sticks(plot, record_b.c13_data, Colors.ACCENT_PINK, "B")

        # IR overlay
        plot = getattr(self, "_plot_IR", None)
        if plot:
            plot.clear()
            self._plot_ir(plot, record_a.ir_data, Colors.ACCENT_CYAN)
            self._plot_ir(plot, record_b.ir_data, Colors.ACCENT_PINK)

        self._compute_delta_summary(record_a, record_b)

    def _plot_sticks(self, plot, nmr_data, color: str, label: str):
        """Plot NMR peaks as sticks on a pyqtgraph PlotWidget."""
        if not nmr_data or not hasattr(nmr_data, "peaks") or not nmr_data.peaks:
            return
        shifts = []
        heights = []
        max_int = 1.0
        for p in nmr_data.peaks:
            s = p.chemical_shift if hasattr(p, "chemical_shift") else p.get("shift", 0)
            h = p.integration if hasattr(p, "integration") else p.get("integration", 1)
            shifts.append(s)
            heights.append(h if h and h > 0 else 1.0)
            max_int = max(max_int, heights[-1])
        # Normalise
        heights = [h / max_int for h in heights]
        pen = pg.mkPen(color=color, width=2)
        for s, h in zip(shifts, heights):
            plot.plot([s, s], [0, h], pen=pen)

    def _plot_ir(self, plot, ir_data, color: str):
        if not ir_data:
            return
        bands = []
        if hasattr(ir_data, "peaks") and ir_data.peaks:
            for p in ir_data.peaks:
                w = p.wavenumber if hasattr(p, "wavenumber") else p.get("wavenumber", 0)
                bands.append(w)
        pen = pg.mkPen(color=color, width=2)
        for w in bands:
            plot.plot([w, w], [0, 1], pen=pen)

    def _compute_delta_summary(self, ra, rb):
        """Compute and display delta summary for matched peaks."""
        if not ra.h1_data or not rb.h1_data:
            self._delta_summary.setText("")
            return

        def get_shifts(data):
            if not data or not hasattr(data, "peaks"):
                return []
            return [
                p.chemical_shift if hasattr(p, "chemical_shift") else p.get("shift", 0)
                for p in data.peaks
            ]

        shifts_a = get_shifts(ra.h1_data)
        shifts_b = get_shifts(rb.h1_data)

        matched = 0
        max_delta = 0.0
        tol = 0.3
        for sa in shifts_a:
            for sb in shifts_b:
                if abs(sa - sb) <= tol:
                    matched += 1
                    max_delta = max(max_delta, abs(sa - sb))
                    break

        if matched:
            self._delta_summary.setText(
                f"1H: {matched} matched peaks, max delta = {max_delta:.2f} ppm"
            )
        else:
            self._delta_summary.setText("No matching peaks found within 0.3 ppm tolerance")

    def _overlay_radar(self, record_a, record_b):
        """Replace the radar placeholder with a DualRadarChart if available."""
        layout = self._radar_container.parent().layout()
        if layout is None:
            return

        try:
            from .widgets.dual_radar_chart import DualRadarChart
            # Remove placeholder
            idx = layout.indexOf(self._radar_container)
            if idx >= 0:
                layout.removeWidget(self._radar_container)
                self._radar_container.hide()

                chart = DualRadarChart()
                data_a = {}
                data_b = {}
                if record_a.validation_report and hasattr(record_a.validation_report, "radar_data"):
                    data_a = record_a.validation_report.radar_data or {}
                if record_b.validation_report and hasattr(record_b.validation_report, "radar_data"):
                    data_b = record_b.validation_report.radar_data or {}

                if data_a or data_b:
                    chart.set_data(
                        data_a, data_b,
                        record_a.display_name(), record_b.display_name(),
                    )
                    layout.insertWidget(idx, chart, 2)
                    self._radar_container = chart
        except ImportError:
            pass  # DualRadarChart not yet created
