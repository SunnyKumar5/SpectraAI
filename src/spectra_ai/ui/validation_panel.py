"""
Validation Panel for SpectraAI.

Displays rule-based validation results with:
  - Confidence gauge (animated score 0–100)
  - Radar chart (per-category scores)
  - Check results table with color-coded status
  - Natural language summary
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTextBrowser, QSplitter, QHeaderView, QFrame,
    QGroupBox, QPushButton, QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon

from ..core.validation_report import ValidationReport, ValidationCheck, CheckStatus
from .widgets.confidence_gauge import ConfidenceGauge
from .widgets.radar_chart import RadarChart
from .styles.colors import Colors, FONT_FAMILY


class ValidationPanel(QWidget):
    """
    Panel displaying validation results, confidence metrics,
    and per-check details for the analyzed compound.

    Signals:
        revalidate_requested: Emitted when user clicks "Re-validate"
    """

    revalidate_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._report: ValidationReport | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # ── Header with title and re-validate button ──────────────────────────
        header = QHBoxLayout()
        title = QLabel("Validation Results")
        title.setFont(QFont(FONT_FAMILY, 14, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)

        self._status_label = QLabel("No data")
        self._status_label.setFont(QFont(FONT_FAMILY, 11))
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        header.addWidget(self._status_label)
        header.addStretch()

        self._revalidate_btn = QPushButton("⟳ Re-validate")
        self._revalidate_btn.setFixedWidth(130)
        self._revalidate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_BLUE};
                color: white;
            }}
        """)
        self._revalidate_btn.clicked.connect(self.revalidate_requested.emit)
        header.addWidget(self._revalidate_btn)

        layout.addLayout(header)

        # ── Top row: Gauge + Radar Chart (capped height so table is always visible) ──
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)

        # Confidence Gauge
        gauge_group = QGroupBox("Overall Confidence")
        gauge_group.setStyleSheet(self._group_style())
        gauge_group.setMaximumHeight(200)
        gauge_layout = QVBoxLayout(gauge_group)
        gauge_layout.setContentsMargins(4, 16, 4, 4)
        gauge_layout.setAlignment(Qt.AlignCenter)
        self._gauge = ConfidenceGauge(size=140)
        gauge_layout.addWidget(self._gauge, alignment=Qt.AlignCenter)
        self._gauge_detail = QLabel("—")
        self._gauge_detail.setAlignment(Qt.AlignCenter)
        self._gauge_detail.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        gauge_layout.addWidget(self._gauge_detail)
        metrics_row.addWidget(gauge_group)

        # Radar Chart
        radar_group = QGroupBox("Category Scores")
        radar_group.setStyleSheet(self._group_style())
        radar_group.setMaximumHeight(200)
        radar_layout = QVBoxLayout(radar_group)
        radar_layout.setContentsMargins(4, 16, 4, 4)
        radar_layout.setAlignment(Qt.AlignCenter)
        self._radar = RadarChart(size=160)
        radar_layout.addWidget(self._radar, alignment=Qt.AlignCenter)
        metrics_row.addWidget(radar_group)

        # Quick stats
        stats_group = QGroupBox("Quick Summary")
        stats_group.setStyleSheet(self._group_style())
        stats_group.setMaximumHeight(200)
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setContentsMargins(8, 16, 8, 4)
        stats_layout.setSpacing(4)
        stats_layout.setAlignment(Qt.AlignTop)
        self._stats_labels = {}
        for key in ["Total Checks", "Passed", "Warnings", "Failed", "Skipped"]:
            row = QHBoxLayout()
            lbl = QLabel(key + ":")
            lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
            val = QLabel("—")
            val.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 13px; font-weight: bold;")
            val.setAlignment(Qt.AlignRight)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            stats_layout.addLayout(row)
            self._stats_labels[key] = val
        metrics_row.addWidget(stats_group)

        layout.addLayout(metrics_row)

        # ── Separator ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        layout.addWidget(sep)

        # ── Bottom: Check results table + summary ─────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {Colors.BORDER}; width: 2px; }}")

        # Checks table
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        table_title = QLabel("Individual Checks")
        table_title.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        table_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        table_layout.addWidget(table_title)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Status", "Check Name", "Category", "Expected", "Observed", "Score"
        ])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_DARK};
                alternate-background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BORDER};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                font-size: 13px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.ACCENT_BLUE}30;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                padding: 7px 10px;
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        self._table.currentCellChanged.connect(self._on_row_selected)
        table_layout.addWidget(self._table)
        splitter.addWidget(table_container)

        # Detail / summary panel
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        summary_title = QLabel("Summary & Detail")
        summary_title.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        summary_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        detail_layout.addWidget(summary_title)

        self._detail_browser = QTextBrowser()
        self._detail_browser.setOpenExternalLinks(False)
        self._detail_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
            }}
        """)
        self._detail_browser.setHtml(self._placeholder_html())
        detail_layout.addWidget(self._detail_browser)
        splitter.addWidget(detail_container)

        splitter.setSizes([600, 400])
        layout.addWidget(splitter, stretch=1)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_report(self, report: ValidationReport, animated: bool = True):
        """
        Display a complete validation report.

        Args:
            report:   ValidationReport object with check results
            animated: Whether to animate gauge/radar transitions
        """
        self._report = report

        # Update gauge
        self._gauge.set_score(report.overall_score, animated=animated)
        self._gauge.set_label(report.overall_status_label)

        # Update radar
        if report.radar_data:
            self._radar.set_data(report.radar_data, animated=animated)

        # Update status label
        self._status_label.setText(report.overall_status_label)
        self._status_label.setStyleSheet(
            f"color: {report.overall_color}; font-size: 12px; font-weight: bold;"
        )

        # Update quick stats
        self._stats_labels["Total Checks"].setText(str(report.total_checks))
        self._stats_labels["Passed"].setText(str(report.pass_count))
        self._stats_labels["Passed"].setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: 13px; font-weight: bold;"
        )
        self._stats_labels["Warnings"].setText(str(report.warning_count))
        self._stats_labels["Warnings"].setStyleSheet(
            f"color: {Colors.WARNING}; font-size: 13px; font-weight: bold;"
        )
        self._stats_labels["Failed"].setText(str(report.fail_count))
        self._stats_labels["Failed"].setStyleSheet(
            f"color: {Colors.ERROR}; font-size: 13px; font-weight: bold;"
        )
        self._stats_labels["Skipped"].setText(str(report.skipped_count))

        # Update gauge detail text
        self._gauge_detail.setText(
            f"{report.pass_count} passed · {report.warning_count} warnings · "
            f"{report.fail_count} failed"
        )

        # Populate table
        self._populate_table(report.checks)

        # Show summary
        self._detail_browser.setHtml(self._summary_html(report))

    def clear_all(self):
        """Reset the panel to empty state."""
        self._report = None
        self._gauge.set_score(0, animated=False)
        self._gauge.set_label("—")
        self._status_label.setText("No data")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        for lbl in self._stats_labels.values():
            lbl.setText("—")
            lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 13px; font-weight: bold;")
        self._gauge_detail.setText("—")
        self._table.setRowCount(0)
        self._detail_browser.setHtml(self._placeholder_html())
        self._radar.set_data({}, animated=False)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _populate_table(self, checks: list[ValidationCheck]):
        """Fill the table with check results."""
        self._table.setRowCount(len(checks))

        for row, check in enumerate(checks):
            # Status icon
            status_item = QTableWidgetItem(check.icon)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor(check.color))
            self._table.setItem(row, 0, status_item)

            # Name
            name_item = QTableWidgetItem(check.name)
            name_item.setToolTip(check.explanation)
            self._table.setItem(row, 1, name_item)

            # Category
            self._table.setItem(row, 2, QTableWidgetItem(check.category))

            # Expected
            exp_item = QTableWidgetItem(check.expected)
            exp_item.setForeground(QColor(Colors.TEXT_SECONDARY))
            self._table.setItem(row, 3, exp_item)

            # Observed
            obs_item = QTableWidgetItem(check.observed)
            if check.is_failing:
                obs_item.setForeground(QColor(Colors.ERROR))
            elif check.is_warning:
                obs_item.setForeground(QColor(Colors.WARNING))
            else:
                obs_item.setForeground(QColor(Colors.SUCCESS))
            self._table.setItem(row, 4, obs_item)

            # Score
            score_item = QTableWidgetItem(f"{check.score:.0f}")
            score_item.setTextAlignment(Qt.AlignCenter)
            score_item.setForeground(QColor(check.color))
            self._table.setItem(row, 5, score_item)

        self._table.resizeColumnsToContents()

    def _on_row_selected(self, row, col, prev_row, prev_col):
        """Show detail for selected check row."""
        if self._report and 0 <= row < len(self._report.checks):
            check = self._report.checks[row]
            self._detail_browser.setHtml(self._check_detail_html(check))

    def _check_detail_html(self, check: ValidationCheck) -> str:
        """Build HTML detail view for a single check."""
        return f"""
        <div style="font-family: '{FONT_FAMILY}';">
            <h3 style="color: {check.color}; margin-bottom: 8px; font-size: 15px; font-weight: 700;">
                {check.icon} {check.name}
            </h3>
            <p style="color: #94A3B8; font-size: 12px; margin-bottom: 14px; letter-spacing: 0.3px;">
                Category: {check.category}  |  Score: <b style="color: {check.color};">{check.score:.0f}/100</b>
            </p>
            <table style="width:100%; margin-bottom:16px; font-size:13px; border-collapse:collapse;">
                <tr>
                    <td style="color:#94A3B8; padding: 6px 12px 6px 0; border-bottom: 1px solid #1E2D45;">Expected:</td>
                    <td style="color:#F1F5F9; padding: 6px 0; border-bottom: 1px solid #1E2D45;">{check.expected}</td>
                </tr>
                <tr>
                    <td style="color:#94A3B8; padding: 6px 12px 6px 0;">Observed:</td>
                    <td style="color:{check.color}; font-weight:700; padding: 6px 0;">{check.observed}</td>
                </tr>
            </table>
            <p style="color:#F1F5F9; font-size:13px; line-height:1.7;">
                {check.explanation}
            </p>
            {"<div style='margin-top:12px; padding: 8px 12px; background: rgba(245,158,11,0.08); border-left: 3px solid #F59E0B; border-radius: 6px;'><span style=\"color:#F59E0B; font-size:12px;\">" + check.suggestion + "</span></div>" if check.suggestion else ""}
        </div>
        """

    def _summary_html(self, report: ValidationReport) -> str:
        """Build HTML summary for the report."""
        return f"""
        <div style="font-family: '{FONT_FAMILY}';">
            <h3 style="color:{report.overall_color}; margin-bottom:10px; font-size:15px; font-weight:700;">
                Validation Summary
            </h3>
            <p style="color:#F1F5F9; font-size:13px; line-height:1.7;">
                {report.summary if report.summary else "Click a row in the table to see details for individual checks."}
            </p>
            <div style="height:1px; background: linear-gradient(90deg, transparent, #1E2D45, transparent); margin: 14px 0;"></div>
            <div style="display: flex; gap: 16px; font-size:12px;">
                <span style="color:#94A3B8;">
                    Score: <b style="color:{report.overall_color}; font-size: 14px;">{report.overall_score:.1f}</b>/100
                </span>
                <span style="color:#10B981; font-weight: 600;">{report.pass_count} passed</span>
                <span style="color:#F59E0B; font-weight: 600;">{report.warning_count} warnings</span>
                <span style="color:#EF4444; font-weight: 600;">{report.fail_count} failed</span>
            </div>
        </div>
        """

    def _placeholder_html(self) -> str:
        return f"""
        <div style="font-family: '{FONT_FAMILY}'; text-align:center; padding:50px 30px;">
            <p style="color:{Colors.TEXT_MUTED}; font-size:14px; line-height:1.6;">
                Enter compound data and click <b style="color:{Colors.ACCENT_BLUE};">Analyze</b> to see validation results.
            </p>
            <p style="color:{Colors.TEXT_MUTED}; font-size:12px; margin-top:8px;">
                Validation checks proton counts, carbon counts, symmetry, functional groups, and cross-spectral consistency.
            </p>
        </div>
        """

    def _group_style(self) -> str:
        return f"""
            QGroupBox {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1A2235, stop:1 #161D2E);
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 22px;
                font-size: 11px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: {Colors.TEXT_SECONDARY};
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
        """
