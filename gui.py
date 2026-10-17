import sys
import json
import os
from datetime import datetime
from pathlib import Path
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QSpinBox, QLabel, QPushButton, QFileDialog,
    QTabWidget, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter, QPalette, QPen


def _extract_items(data):
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [
            item
            for value in data.values()
            if isinstance(value, list)
            for item in value
            if isinstance(item, dict)
        ]
    return []


class UsageChart(QWidget):
    def __init__(self):
        super().__init__()
        self.category = ""
        self.item_name = ""
        self.points = []
        self.setMinimumSize(600, 360)

    def set_series(self, category, item_name, points):
        self.category = category
        self.item_name = item_name
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        if not self.points:
            painter.setPen(QColor("#606770"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No usage history available")
            return

        chart = self.rect().adjusted(78, 42, -28, -68)
        quantities = [quantity for _, quantity in self.points]
        maximum = max(quantities) or 1
        painter.setPen(QColor("#252a31"))
        painter.drawText(20, 24, f"{self.category.capitalize()} - {self.item_name}")

        for tick in range(5):
            y = chart.bottom() - chart.height() * tick / 4
            value = maximum * tick / 4
            painter.setPen(QPen(QColor("#e2e6e9"), 1))
            painter.drawLine(chart.left(), round(y), chart.right(), round(y))
            painter.setPen(QColor("#606770"))
            painter.drawText(12, round(y) + 5, f"{value:g}")

        painter.setPen(QColor("#606770"))
        painter.drawText(12, chart.top() - 12, "Quantity")
        painter.drawText(chart.left(), chart.bottom() + 52, "Snapshot time")

        denominator = max(1, len(self.points) - 1)
        coordinates = []
        for index, (timestamp, quantity) in enumerate(self.points):
            x = chart.left() + chart.width() * index / denominator
            y = chart.bottom() - chart.height() * quantity / maximum
            coordinates.append((round(x), round(y)))

        painter.setPen(QPen(QColor("#087e8b"), 3))
        for start, end in zip(coordinates, coordinates[1:]):
            painter.drawLine(*start, *end)
        painter.setBrush(QColor("#087e8b"))
        for x, y in coordinates:
            painter.drawEllipse(x - 4, y - 4, 8, 8)

        label_font = QFont(painter.font())
        label_font.setPointSize(9)
        painter.setFont(label_font)
        label_metrics = QFontMetrics(label_font)
        painter.setPen(QColor("#174a51"))
        for (timestamp, quantity), (x, y) in zip(self.points, coordinates):
            label = f"{quantity:g}"
            label_x = max(
                2,
                min(self.width() - label_metrics.horizontalAdvance(label) - 2,
                    x - label_metrics.horizontalAdvance(label) // 2),
            )
            painter.drawText(label_x, max(16, y - 9), label)

        label_indexes = sorted(set(
            round(index * (len(self.points) - 1) / min(4, len(self.points) - 1))
            for index in range(min(4, len(self.points) - 1) + 1)
        )) if len(self.points) > 1 else [0]
        painter.setPen(QColor("#606770"))
        for index in label_indexes:
            timestamp = self.points[index][0]
            x = coordinates[index][0]
            painter.drawText(x - 42, chart.bottom() + 22, timestamp.strftime("%m-%d %H:%M"))


class ArmoryViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.items_data = {}
        self.thresholds = {}
        self.usage_history = {}
        self.organized_crimes = []
        self.faction_inventory = None
        self.project_dir = Path(__file__).resolve().parent
        self.output_dir = str(self.project_dir / "OUTPUT")
        self.refresh_process = None
        self.init_ui()
        self.load_latest_data()

    def init_ui(self):
        self.setWindowTitle("Faction Armory Stats Viewer")
        self.setGeometry(100, 100, 1200, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        title = QLabel("Faction Armory Items")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.data_warning = QLabel()
        warning_font = QFont()
        warning_font.setPointSize(16)
        warning_font.setBold(True)
        self.data_warning.setFont(warning_font)
        self.data_warning.setStyleSheet(
            "background-color: #8b1e1e; color: white; padding: 10px;"
        )
        self.data_warning.setWordWrap(True)
        self.data_warning.hide()
        layout.addWidget(self.data_warning)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        reload_btn = QPushButton("Reload Latest Data")
        reload_btn.clicked.connect(self.run_data_refresh)
        self.reload_btn = reload_btn
        button_layout.addWidget(reload_btn)

        save_btn = QPushButton("Save Thresholds")
        save_btn.clicked.connect(self.save_thresholds)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)
        central_widget.setLayout(layout)

    def run_data_refresh(self):
        """Run FAST.py, then load the new exports when it finishes."""
        self.reload_btn.setEnabled(False)
        self.refresh_process = QProcess(self)
        self.refresh_process.setWorkingDirectory(str(self.project_dir))
        self.refresh_process.finished.connect(self._on_data_refresh_finished)
        self.refresh_process.errorOccurred.connect(self._on_data_refresh_error)
        self.refresh_process.start(sys.executable, [str(self.project_dir / "FAST.py")])

    def _on_data_refresh_finished(self, exit_code, exit_status):
        self.reload_btn.setEnabled(True)
        self.refresh_process = None
        if exit_code == 0 and exit_status == QProcess.NormalExit:
            self.load_latest_data()
        else:
            QMessageBox.critical(
                self,
                "Data refresh failed",
                f"FAST.py exited with status {exit_code}.",
            )

    def _on_data_refresh_error(self, error):
        if error == QProcess.FailedToStart:
            self.reload_btn.setEnabled(True)
            self.refresh_process = None
            QMessageBox.critical(
                self,
                "Data refresh failed",
                "Could not start FAST.py. Check that Python is available.",
            )

    def load_latest_data(self):
        """Load the latest JSON export files from OUTPUT directory."""
        if not os.path.exists(self.output_dir):
            print(f"Output directory not found: {self.output_dir}")
            return

        pattern = re.compile(r"^(?P<category>.+)_(?P<timestamp>\d{8}_\d{6})\.json$")
        files_by_category = {}

        for root, _, files in os.walk(self.output_dir):
            for filename in files:
                match = pattern.match(filename)
                if not match:
                    continue

                category = match.group("category")
                if category == "usage_report":
                    continue
                timestamp_text = match.group("timestamp")
                timestamp = datetime.strptime(timestamp_text, "%Y%m%d_%H%M%S")
                file_path = os.path.join(root, filename)

                files_by_category.setdefault(category, []).append({
                    "filename": filename,
                    "datetime": timestamp,
                    "path": file_path,
                })

        self.items_data = {}
        outdated_categories = []
        for category, file_infos in files_by_category.items():
            file_infos.sort(key=lambda item: item["datetime"], reverse=True)
            newest_timestamp = file_infos[0]["datetime"]
            selected_file = None
            selected_items = []

            for file_info in file_infos:
                try:
                    with open(file_info["path"], "r") as f:
                        data = json.load(f)
                except (OSError, json.JSONDecodeError):
                    continue

                items = _extract_items(data)

                if items:
                    selected_file = file_info
                    selected_items = items
                    break

            if selected_file is None:
                continue

            if selected_file["datetime"] < newest_timestamp:
                outdated_categories.append(
                    f"{category.capitalize()}: using {selected_file['datetime']:%Y-%m-%d %H:%M:%S}"
                )

            for item in selected_items:
                item_name = item.get("name", item.get("ID", "Unknown"))
                self.items_data[item_name] = {
                    "ID": item.get("ID"),
                    "category": category,
                    "total": item.get("quantity", 0),
                    "available": item.get("available", 0),
                    "loaned": item.get("loaned", 0),
                }

        if outdated_categories:
            self.data_warning.setText(
                "WARNING: OUTDATED DATA IN USE\n" + "\n".join(outdated_categories)
            )
            self.data_warning.show()
        else:
            self.data_warning.hide()

        self.load_usage_history()
        self.load_thresholds()
        self.load_organized_crimes()
        self.populate_table()

    def load_organized_crimes(self):
        """Load the cached Torn organized-crime catalogue."""
        definitions_file = os.path.join(self.output_dir, "organized_crime_definitions.json")
        try:
            with open(definitions_file, "r") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.organized_crimes = []
            return

        self.organized_crimes = data.get("organizedcrimes", []) if isinstance(data, dict) else []

        inventory_file = os.path.join(self.output_dir, "faction_inventory.json")
        try:
            with open(inventory_file, "r") as handle:
                inventory_data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.faction_inventory = None
        else:
            inventory = inventory_data.get("inventory") if isinstance(inventory_data, dict) else None
            self.faction_inventory = inventory if isinstance(inventory, list) else None

    def load_usage_history(self):
        """Load timestamped item quantities for the Usage tab."""
        pattern = re.compile(r"^(?P<category>.+)_(?P<timestamp>\d{8}_\d{6})\.json$")
        snapshots_by_category = {}

        for root, _, files in os.walk(self.output_dir):
            for filename in files:
                match = pattern.match(filename)
                if not match:
                    continue

                if match.group("category") == "usage_report":
                    continue

                timestamp = datetime.strptime(match.group("timestamp"), "%Y%m%d_%H%M%S")
                try:
                    with open(os.path.join(root, filename), "r") as f:
                        items = _extract_items(json.load(f))
                except (OSError, json.JSONDecodeError):
                    continue

                if not items:
                    continue

                quantities = {}
                for item in items:
                    name = item.get("name") or item.get("ID") or "Unknown"
                    try:
                        quantities[name] = float(item.get("quantity", 0) or 0)
                    except (TypeError, ValueError):
                        quantities[name] = 0

                category = match.group("category")
                snapshots_by_category.setdefault(category, []).append((timestamp, quantities))

        self.usage_history = {}
        for category, snapshots in snapshots_by_category.items():
            snapshots.sort(key=lambda snapshot: snapshot[0])
            item_names = set().union(*(quantities.keys() for _, quantities in snapshots))
            self.usage_history[category] = {
                name: [
                    (timestamp, quantities.get(name, 0))
                    for timestamp, quantities in snapshots
                ]
                for name in item_names
            }

    def load_thresholds(self):
        """Load thresholds from a config file if it exists."""
        thresholds_file = os.path.join(self.output_dir, "thresholds.json")
        if os.path.exists(thresholds_file):
            with open(thresholds_file, "r") as f:
                self.thresholds = json.load(f)
        else:
            self.thresholds = {}
        
        for item in self.items_data:
            if item not in self.thresholds:
                self.thresholds[item] = 10

    def save_thresholds(self):
        """Save thresholds to a config file."""
        thresholds_file = os.path.join(self.output_dir, "thresholds.json")
        with open(thresholds_file, "w") as f:
            json.dump(self.thresholds, f, indent=4)
        print(f"Thresholds saved to {thresholds_file}")

    def populate_table(self):
        """Populate tabs with item data organized by category."""
        self.tab_widget.clear()
        
        categories = {}
        for item_name, item_info in self.items_data.items():
            category = item_info["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append((item_name, item_info))

        for category in sorted(categories.keys()):
            use_total_only = category in {"medical", "drugs", "boosters"}
            table = QTableWidget()
            if use_total_only:
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(
                    ["Item Name", "Total", "Min Threshold", "Status"]
                )
                table.setColumnWidth(0, 200)
                table.setColumnWidth(1, 80)
                table.setColumnWidth(2, 120)
                table.setColumnWidth(3, 150)
            else:
                table.setColumnCount(6)
                table.setHorizontalHeaderLabels(
                    ["Item Name", "Total", "Available", "Loaned", "Min Threshold", "Status"]
                )
                table.setColumnWidth(0, 200)
                table.setColumnWidth(1, 80)
                table.setColumnWidth(2, 100)
                table.setColumnWidth(3, 100)
                table.setColumnWidth(4, 120)
                table.setColumnWidth(5, 150)

            for item_name, item_info in sorted(categories[category]):
                row = table.rowCount()
                table.insertRow(row)

                threshold = self.thresholds.get(item_name, 10)
                if use_total_only:
                    compare_value = item_info["total"]
                    is_below_threshold = compare_value < threshold
                else:
                    available = item_info["available"]
                    compare_value = available
                    is_below_threshold = available < threshold

                name_item = QTableWidgetItem(item_name)
                if is_below_threshold:
                    name_item.setBackground(QColor(255, 200, 200))

                total_item = QTableWidgetItem(str(item_info["total"]))
                if is_below_threshold:
                    total_item.setBackground(QColor(255, 200, 200))

                threshold_spinbox = QSpinBox()
                threshold_spinbox.setValue(threshold)
                threshold_spinbox.setMinimum(0)
                threshold_spinbox.setMaximum(10000)
                threshold_spinbox.valueChanged.connect(
                    lambda value, name=item_name: self.update_threshold(name, value)
                )

                status_item = QTableWidgetItem("LOW" if is_below_threshold else "OK")
                status_item.setFont(QFont())
                status_item.font().setBold(True)
                if is_below_threshold:
                    status_item.setForeground(QColor(255, 0, 0))
                    status_item.setBackground(QColor(255, 200, 200))
                else:
                    status_item.setForeground(QColor(0, 150, 0))

                table.setItem(row, 0, name_item)
                table.setItem(row, 1, total_item)
                if use_total_only:
                    table.setCellWidget(row, 2, threshold_spinbox)
                    table.setItem(row, 3, status_item)
                else:
                    available_item = QTableWidgetItem(str(item_info["available"]))
                    if is_below_threshold:
                        available_item.setBackground(QColor(255, 100, 100))
                    available_item.setFont(QFont())
                    available_item.font().setBold(item_info["available"] < threshold)

                    loaned_item = QTableWidgetItem(str(item_info["loaned"]))
                    if is_below_threshold:
                        loaned_item.setBackground(QColor(255, 200, 200))

                    table.setItem(row, 2, available_item)
                    table.setItem(row, 3, loaned_item)
                    table.setCellWidget(row, 4, threshold_spinbox)
                    table.setItem(row, 5, status_item)

            self.tab_widget.addTab(table, category.capitalize())

        self.tab_widget.addTab(self._build_usage_tab(), "Usage")
        self.tab_widget.addTab(self._build_oc_items_tab(), "OC items")

    def _build_oc_items_tab(self):
        """Show required items and available armory stock for each OC."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        if not self.organized_crimes:
            layout.addWidget(QLabel(
                "Organized-crime requirements are not cached. Use Reload Latest Data to fetch them."
            ))
            return tab

        if self.faction_inventory is not None:
            available_by_id = {}
            for inventory_item in self.faction_inventory:
                item_id = inventory_item.get("id")
                if item_id is None or inventory_item.get("loaned") is not None:
                    continue
                key = str(item_id)
                available_by_id[key] = available_by_id.get(key, 0) + inventory_item.get("amount", 0)
        else:
            available_by_id = {
                str(item_info["ID"]): item_info.get("available", item_info.get("total", 0))
                for item_info in self.items_data.values()
                if item_info.get("ID") is not None
            }
        requirements_by_crime = []
        item_names = {}
        for crime in self.organized_crimes:
            requirements = {}
            for slot in crime.get("slots", []):
                required_item = slot.get("required_item")
                if not isinstance(required_item, dict) or required_item.get("id") is None:
                    continue
                item_id = str(required_item["id"])
                requirements[item_id] = requirements.get(item_id, 0) + 1
                item_names[item_id] = required_item.get("name", f"Item {item_id}")
            requirements_by_crime.append((crime, requirements))

        item_ids = sorted(item_names, key=lambda item_id: item_names[item_id].casefold())
        table = QTableWidget(len(item_ids), len(requirements_by_crime) + 1)
        table.setHorizontalHeaderLabels(
            ["Item"] + [
                f"{crime.get('name', 'Unknown')}"
                + (f"\nDifficulty {crime['difficulty']}" if crime.get("difficulty") is not None else "")
                for crime, _ in requirements_by_crime
            ]
        )
        table.setColumnWidth(0, 220)
        table.verticalHeader().setVisible(False)
        for column in range(1, table.columnCount()):
            table.setColumnWidth(column, 170)

        for row, item_id in enumerate(item_ids):
            item_cell = QTableWidgetItem(item_names[item_id])
            table.setItem(row, 0, item_cell)
            row_missing = False
            for column, (_, requirements) in enumerate(requirements_by_crime, 1):
                needed = requirements.get(item_id, 0)
                cell = QTableWidgetItem()
                cell.setTextAlignment(Qt.AlignCenter)
                if needed:
                    if self.faction_inventory is None and item_id not in available_by_id:
                        cell.setText(f"? / {needed}")
                        cell.setToolTip("Full faction inventory is unavailable for this item.")
                    else:
                        available = available_by_id.get(item_id, 0)
                        cell.setText(f"{available} / {needed}")
                        row_missing = row_missing or available < needed
                        cell.setToolTip(
                            f"{item_names[item_id]}: {available} available, {needed} needed"
                        )
                if column % 2 == 1:
                    cell.setBackground(QColor("#f0f2f3"))
                table.setItem(row, column, cell)
            if row_missing:
                for column in range(table.columnCount()):
                    table.item(row, column).setBackground(QColor("#f4cccc"))

        highlighted_items = []
        selection_color = QColor("#a6a6a6")
        table_palette = table.palette()
        table_palette.setColor(QPalette.Highlight, selection_color)
        table_palette.setColor(QPalette.HighlightedText, QColor("#111111"))
        table.setPalette(table_palette)

        def highlight_selection(row, column, previous_row, previous_column):
            for item, original_background in highlighted_items:
                item.setBackground(original_background)
            highlighted_items.clear()
            if row < 0 or column < 0:
                return

            targets = [table.item(row, current_column)
                       for current_column in range(table.columnCount())]
            targets.extend(
                table.item(current_row, column)
                for current_row in range(table.rowCount())
                if current_row != row
            )
            targets.append(table.horizontalHeaderItem(column))
            for item in targets:
                if item is not None:
                    highlighted_items.append((item, item.background()))
                    item.setBackground(selection_color)

        table.currentCellChanged.connect(highlight_selection)

        layout.addWidget(table)
        return tab

    def _build_usage_tab(self):
        usage_tab = QWidget()
        layout = QVBoxLayout(usage_tab)
        selector_layout = QHBoxLayout()

        selector_layout.addWidget(QLabel("Category"))
        self.usage_category_combo = QComboBox()
        self.usage_category_combo.addItems(sorted(self.usage_history))
        self.usage_category_combo.currentTextChanged.connect(self._update_usage_items)
        selector_layout.addWidget(self.usage_category_combo)

        selector_layout.addWidget(QLabel("Item"))
        self.usage_item_combo = QComboBox()
        self.usage_item_combo.currentTextChanged.connect(self._update_usage_chart)
        selector_layout.addWidget(self.usage_item_combo, 1)

        layout.addLayout(selector_layout)
        self.usage_chart = UsageChart()
        layout.addWidget(self.usage_chart, 1)
        self._update_usage_items(self.usage_category_combo.currentText())
        return usage_tab

    def _update_usage_items(self, category):
        self.usage_item_combo.clear()
        self.usage_item_combo.addItems(sorted(self.usage_history.get(category, {})))

    def _update_usage_chart(self, item_name):
        category = self.usage_category_combo.currentText()
        points = self.usage_history.get(category, {}).get(item_name, [])
        self.usage_chart.set_series(category, item_name, points)

    def update_threshold(self, item_name, value):
        """Update the threshold for an item."""
        self.thresholds[item_name] = value
        self.populate_table()


def main():
    app = QApplication(sys.argv)
    viewer = ArmoryViewer()
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
