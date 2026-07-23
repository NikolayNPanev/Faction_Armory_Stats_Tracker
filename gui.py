import sys
import json
import os
from datetime import datetime
from pathlib import Path
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QSpinBox, QLabel, QPushButton, QFileDialog, QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont


class ArmoryViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.items_data = {}
        self.thresholds = {}
        self.output_dir = os.path.join(os.getcwd(), "OUTPUT")
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

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        reload_btn = QPushButton("Reload Latest Data")
        reload_btn.clicked.connect(self.load_latest_data)
        button_layout.addWidget(reload_btn)

        save_btn = QPushButton("Save Thresholds")
        save_btn.clicked.connect(self.save_thresholds)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)
        central_widget.setLayout(layout)

    def load_latest_data(self):
        """Load the latest JSON export files from OUTPUT directory."""
        if not os.path.exists(self.output_dir):
            print(f"Output directory not found: {self.output_dir}")
            return

        pattern = re.compile(r"^(?P<category>.+)_(?P<timestamp>\d{8}_\d{6})\.json$")
        latest_files = {}

        for filename in os.listdir(self.output_dir):
            match = pattern.match(filename)
            if not match:
                continue

            category = match.group("category")
            timestamp_text = match.group("timestamp")
            timestamp = datetime.strptime(timestamp_text, "%Y%m%d_%H%M%S")

            if category not in latest_files or timestamp > latest_files[category]["datetime"]:
                latest_files[category] = {
                    "filename": filename,
                    "datetime": timestamp,
                    "path": os.path.join(self.output_dir, filename),
                }

        self.items_data = {}
        for category, file_info in latest_files.items():
            with open(file_info["path"], "r") as f:
                data = json.load(f)

            if isinstance(data, dict):
                for _, value in data.items():
                    if isinstance(value, list):
                        for item in value:
                            item_name = item.get("name", item.get("ID", "Unknown"))
                            self.items_data[item_name] = {
                                "ID": item.get("ID"),
                                "category": category,
                                "total": item.get("quantity", 0),
                                "available": item.get("available", 0),
                                "loaned": item.get("loaned", 0),
                            }

        self.load_thresholds()
        self.populate_table()

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
            table = QTableWidget()
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
                available = item_info["available"]
                is_below_threshold = available < threshold

                name_item = QTableWidgetItem(item_name)
                if is_below_threshold:
                    name_item.setBackground(QColor(255, 200, 200))

                total_item = QTableWidgetItem(str(item_info["total"]))
                if is_below_threshold:
                    total_item.setBackground(QColor(255, 200, 200))

                available_item = QTableWidgetItem(str(available))
                if is_below_threshold:
                    available_item.setBackground(QColor(255, 100, 100))
                available_item.setFont(QFont())
                available_item.font().setBold(available < threshold)

                loaned_item = QTableWidgetItem(str(item_info["loaned"]))
                if is_below_threshold:
                    loaned_item.setBackground(QColor(255, 200, 200))

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
                table.setItem(row, 2, available_item)
                table.setItem(row, 3, loaned_item)
                table.setCellWidget(row, 4, threshold_spinbox)
                table.setItem(row, 5, status_item)

            self.tab_widget.addTab(table, category.capitalize())

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
