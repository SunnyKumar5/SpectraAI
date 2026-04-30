"""
BatchPanel -- Session-mode panel showing all compounds as cards.

Full-width panel for the Session tab of the ModeNavigator.
Card-based layout with sort/filter, stats bar, and leaderboard.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QScrollArea, QFrame, QSizePolicy,
    QFileDialog, QMessageBox, QProgressBar,
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve

from .styles.colors import Colors, FONT_FAMILY, ANIM_MEDIUM
from .widgets.compound_card import CompoundCard


class BatchPanel(QWidget):
    """
    Session panel showing all compounds as scrollable cards.

    Signals
    -------
    compound_selected(str)                 compound_id clicked
    compare_requested(str, str)            id_a, id_b
    batch_analyse_requested(list[str])     list of compound_ids to analyse
    add_current_requested()                add the active compound to session
    """

    compound_selected = pyqtSignal(str)
    compare_requested = pyqtSignal(str, str)
    batch_analyse_requested = pyqtSignal(list)
    add_current_requested = pyqtSignal()

    # Legacy signal kept for back-compat with old main_window wiring
    analyze_batch_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, CompoundCard] = {}   # id -> card
        self._active_id: str | None = None
        self._sort_key = "recent"
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        # -- Action bar -------------------------------------------------------
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self._add_btn = self._make_btn("+ Add Current")
        self._add_btn.clicked.connect(self.add_current_requested.emit)
        action_row.addWidget(self._add_btn)

        self._import_btn = self._make_btn("Import CSV")
        self._import_btn.clicked.connect(self._import_csv)
        action_row.addWidget(self._import_btn)

        self._analyse_btn = self._make_btn("Analyse All")
        self._analyse_btn.setEnabled(False)
        self._analyse_btn.clicked.connect(self._analyse_all)
        action_row.addWidget(self._analyse_btn)

        action_row.addStretch()
        root.addLayout(action_row)

        # -- Sort / filter bar ------------------------------------------------
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)

        filter_row.addWidget(QLabel("Sort:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Recent", "Name", "Score"])
        self._sort_combo.setMaximumWidth(90)
        self._sort_combo.setStyleSheet(self._combo_style())
        self._sort_combo.currentTextChanged.connect(self._on_sort_changed)
        filter_row.addWidget(self._sort_combo)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search...")
        self._search.setMaximumWidth(180)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {Colors.BG_DARK}; color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; border-radius: 4px;
                padding: 3px 8px; font-size: 11px;
            }}
        """)
        self._search.textChanged.connect(self._on_search)
        filter_row.addWidget(self._search)
        filter_row.addStretch()

        self._count_label = QLabel("0 compounds")
        self._count_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px;"
        )
        filter_row.addWidget(self._count_label)
        root.addLayout(filter_row)

        # -- Scrollable card list ---------------------------------------------
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent; border: none;
            }}
            QScrollBar:vertical {{
                background: {Colors.BG_DARK}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER_ACTIVE}; border-radius: 4px;
                min-height: 30px;
            }}
        """)

        self._card_container = QWidget()
        self._card_container.setStyleSheet("background: transparent;")
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(0, 0, 0, 0)
        self._card_layout.setSpacing(6)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._card_container)
        root.addWidget(self._scroll, stretch=1)

        # -- Placeholder (empty state) ----------------------------------------
        self._placeholder = QLabel(
            "<div style='text-align:center; padding:40px;'>"
            "<span style='font-size:28px;'>&#129514;</span><br><br>"
            "<b>No compounds yet</b><br><br>"
            "<span style='color:" + Colors.TEXT_MUTED + ";'>"
            "Analyse a compound to add it to the session,<br>"
            "or import compounds from a CSV file.</span></div>"
        )
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;"
        )
        root.addWidget(self._placeholder)
        self._placeholder.show()

        # -- Stats bar --------------------------------------------------------
        self._stats_bar = QLabel("")
        self._stats_bar.setAlignment(Qt.AlignCenter)
        self._stats_bar.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; padding: 4px 0;"
        )
        self._stats_bar.hide()
        root.addWidget(self._stats_bar)

        # -- Leaderboard toggle -----------------------------------------------
        self._lb_btn = QPushButton("Leaderboard")
        self._lb_btn.setCheckable(True)
        self._lb_btn.setStyleSheet(self._make_btn_style())
        self._lb_btn.clicked.connect(self._toggle_leaderboard)
        self._lb_btn.hide()
        root.addWidget(self._lb_btn)

        self._lb_widget = QLabel("")
        self._lb_widget.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 10px;"
            f" background: {Colors.BG_DARK}; border-radius: 6px; padding: 8px;"
        )
        self._lb_widget.setWordWrap(True)
        self._lb_widget.hide()
        root.addWidget(self._lb_widget)

    # ── Public API ───────────────────────────────────────────────────────────

    def add_compound(self, compound_id: str, name: str, formula: str,
                     score: int | None, status: str, svg: str | None = None):
        """Add a compound card to the list."""
        if compound_id in self._cards:
            # Update existing
            card = self._cards[compound_id]
            card.set_score(score)
            card.set_status(status)
            self._update_stats()
            return

        card = CompoundCard(compound_id, name, formula, score, status, svg)
        card.clicked.connect(self._on_card_clicked)
        card.remove_requested.connect(self._on_card_remove)
        card.compare_requested.connect(self._on_card_compare)

        self._cards[compound_id] = card
        # Insert before the stretch
        idx = self._card_layout.count() - 1  # before stretch
        self._card_layout.insertWidget(idx, card)

        self._placeholder.hide()
        self._update_stats()

    def remove_compound(self, compound_id: str):
        card = self._cards.pop(compound_id, None)
        if card:
            self._card_layout.removeWidget(card)
            card.deleteLater()
        if not self._cards:
            self._placeholder.show()
        self._update_stats()

    def set_active(self, compound_id: str):
        self._active_id = compound_id
        for cid, card in self._cards.items():
            card.set_active(cid == compound_id)

    def update_compound(self, compound_id: str, score: int | None = None,
                        status: str | None = None):
        card = self._cards.get(compound_id)
        if card:
            if score is not None:
                card.set_score(score)
            if status is not None:
                card.set_status(status)
        self._update_stats()

    def clear(self):
        for card in list(self._cards.values()):
            self._card_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._active_id = None
        self._placeholder.show()
        self._stats_bar.hide()
        self._lb_btn.hide()
        self._lb_widget.hide()
        self._count_label.setText("0 compounds")

    # Also keep the old API for compat
    def set_compounds(self, compounds: list):
        """Legacy: load Molecule list into batch cards."""
        self.clear()
        for mol in compounds:
            cid = mol.compound_id or mol.name or f"cmp_{id(mol)}"
            self.add_compound(cid, mol.name or "", mol.formula or "", None, "Pending")

    def update_row(self, index: int, status: str, score: float, result: str):
        """Legacy: update by row index."""
        keys = list(self._cards.keys())
        if 0 <= index < len(keys):
            self.update_compound(keys[index], score=int(score), status=status)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _on_card_clicked(self, compound_id: str):
        self.set_active(compound_id)
        self.compound_selected.emit(compound_id)

    def _on_card_remove(self, compound_id: str):
        self.remove_compound(compound_id)

    def _on_card_compare(self, compound_id: str):
        if self._active_id and self._active_id != compound_id:
            self.compare_requested.emit(self._active_id, compound_id)

    def _on_sort_changed(self, text: str):
        self._sort_key = text.lower()
        self._resort_cards()

    def _on_search(self, text: str):
        q = text.lower().strip()
        for cid, card in self._cards.items():
            visible = not q or q in cid.lower() or q in card._name.lower() or q in card._formula.lower()
            card.setVisible(visible)

    def _resort_cards(self):
        # Remove all cards from layout (except the stretch)
        cards_list = list(self._cards.values())
        for card in cards_list:
            self._card_layout.removeWidget(card)

        if self._sort_key == "name":
            cards_list.sort(key=lambda c: c._name.lower())
        elif self._sort_key == "score":
            cards_list.sort(key=lambda c: (c._score or -1), reverse=True)
        # else "recent" -> original insertion order (dict preserves it)

        for i, card in enumerate(cards_list):
            self._card_layout.insertWidget(i, card)

    def _update_stats(self):
        n = len(self._cards)
        self._count_label.setText(f"{n} compound{'s' if n != 1 else ''}")
        self._analyse_btn.setEnabled(
            any(c._status == "Pending" for c in self._cards.values())
        )

        if n >= 2:
            scores = [c._score for c in self._cards.values() if c._score is not None]
            if scores:
                avg = sum(scores) / len(scores)
                best_card = max(
                    (c for c in self._cards.values() if c._score is not None),
                    key=lambda c: c._score,
                    default=None,
                )
                best_name = best_card._name if best_card else "?"
                best_score = best_card._score if best_card else 0
                self._stats_bar.setText(
                    f"{n} compounds  |  Avg score: {avg:.0f}  |  "
                    f"Best: {best_name} ({best_score})"
                )
            else:
                self._stats_bar.setText(f"{n} compounds")
            self._stats_bar.show()
        else:
            self._stats_bar.hide()

        if n >= 3:
            self._lb_btn.show()
            self._update_leaderboard()
        else:
            self._lb_btn.hide()
            self._lb_widget.hide()

    def _toggle_leaderboard(self, checked: bool):
        self._lb_widget.setVisible(checked)
        if checked:
            self._update_leaderboard()

    def _update_leaderboard(self):
        scored = [
            (c._name, c._score, c._compound_id)
            for c in self._cards.values() if c._score is not None
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        lines = []
        for rank, (name, score, cid) in enumerate(scored, 1):
            bar_len = int(score / 100 * 16) if score else 0
            bar = "\u2588" * bar_len + "\u2591" * (16 - bar_len)
            if score >= 80:
                clr = Colors.ACCENT_GREEN
            elif score >= 50:
                clr = Colors.ACCENT_AMBER
            else:
                clr = Colors.ACCENT_RED
            lines.append(
                f"<span style='color:{clr}'>#{rank}  {name}  {score}  {bar}</span>"
            )
        self._lb_widget.setText("<br>".join(lines) if lines else "No scores yet")

    def _import_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not filepath:
            return
        try:
            from ..parsers.csv_parser import parse_compound_csv
            molecules = parse_compound_csv(filepath)
            for mol in molecules:
                cid = mol.compound_id or mol.name or f"csv_{id(mol)}"
                self.add_compound(cid, mol.name or "", mol.formula or "", None, "Pending")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not import CSV:\n{e}")

    def _analyse_all(self):
        pending = [cid for cid, c in self._cards.items() if c._status == "Pending"]
        if pending:
            self.batch_analyse_requested.emit(pending)

    # ── Styling helpers ──────────────────────────────────────────────────────

    def _make_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setStyleSheet(self._make_btn_style())
        return btn

    def _make_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; border-radius: 4px;
                padding: 2px 10px; font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_BLUE}40;
                border-color: {Colors.ACCENT_BLUE};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_MUTED};
                border-color: {Colors.BORDER};
            }}
        """

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {Colors.BG_DARK}; color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; border-radius: 4px;
                padding: 2px 6px; font-size: 11px;
            }}
        """
