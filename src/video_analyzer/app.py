from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QSettings, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v"}
SETTINGS_ORGANIZATION = "VideoAnalyzer"
SETTINGS_APPLICATION = "VideoAnalyzer"
SETTINGS_WATCH_FOLDER_KEY = "watch_folder"
RESULT_COLUMNS = [
    "No.",
    "検出日時",
    "動画ファイル",
    "状態",
    "長さ",
    "解析値A",
    "解析値B",
    "パス",
    "備考",
]

APP_STYLE = """
QMainWindow,
QDialog {
    background: #f6f8fb;
    color: #172033;
    font-family: "Segoe UI", "Yu Gothic UI", "Meiryo";
    font-size: 10pt;
}

QMenuBar {
    background: #ffffff;
    border-bottom: 1px solid #dfe5ef;
    padding: 4px 8px;
}

QMenuBar::item {
    border-radius: 6px;
    padding: 6px 10px;
}

QMenuBar::item:selected {
    background: #edf3ff;
    color: #1d4ed8;
}

QMenu {
    background: #ffffff;
    border: 1px solid #d8e0eb;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    border-radius: 6px;
    padding: 8px 28px 8px 12px;
}

QMenu::item:selected {
    background: #edf3ff;
    color: #1d4ed8;
}

QWidget#appHeader,
QWidget#folderBar,
QWidget#resultsPanel,
QWidget#sidePanel,
QWidget#videoPanel {
    background: #ffffff;
    border: 1px solid #dfe5ef;
    border-radius: 8px;
}

QLabel#appTitle {
    color: #111827;
    font-size: 20pt;
    font-weight: 700;
}

QLabel#appSubtitle,
QLabel#guidanceLabel,
QLabel#videoPathLabel {
    color: #667085;
}

QLabel#sectionTitle {
    color: #172033;
    font-size: 13pt;
    font-weight: 700;
}

QLineEdit {
    background: #f9fbff;
    border: 1px solid #cfd8e6;
    border-radius: 8px;
    color: #172033;
    min-height: 34px;
    padding: 0 12px;
    selection-background-color: #bfdbfe;
}

QLineEdit:focus {
    border: 1px solid #2563eb;
    background: #ffffff;
}

QPushButton {
    background: #ffffff;
    border: 1px solid #cfd8e6;
    border-radius: 8px;
    color: #344054;
    font-weight: 600;
    min-height: 34px;
    padding: 0 14px;
}

QPushButton:hover {
    background: #f3f6fb;
    border-color: #b8c4d6;
}

QPushButton:pressed {
    background: #e8eef7;
}

QPushButton[variant="primary"] {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
}

QPushButton[variant="primary"]:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}

QPushButton[variant="danger"] {
    background: #ffffff;
    border-color: #fecaca;
    color: #b42318;
}

QPushButton[variant="danger"]:hover {
    background: #fff1f2;
    border-color: #fda4af;
}

QGroupBox {
    background: #ffffff;
    border: 1px solid #dfe5ef;
    border-radius: 8px;
    color: #172033;
    font-weight: 700;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QTableWidget {
    background: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #dfe5ef;
    border-radius: 8px;
    gridline-color: #edf1f7;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
}

QTableWidget::item {
    border-bottom: 1px solid #edf1f7;
    padding: 8px;
}

QHeaderView::section {
    background: #f1f5f9;
    border: 0;
    border-bottom: 1px solid #dfe5ef;
    color: #475467;
    font-weight: 700;
    min-height: 36px;
    padding: 8px;
}

QSplitter::handle {
    background: transparent;
    width: 10px;
}

QStatusBar {
    background: #ffffff;
    border-top: 1px solid #dfe5ef;
    color: #667085;
}

QSlider::groove:horizontal {
    background: #dfe5ef;
    border-radius: 3px;
    height: 6px;
}

QSlider::sub-page:horizontal {
    background: #2563eb;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #2563eb;
    border-radius: 8px;
    height: 14px;
    margin: -5px 0;
    width: 14px;
}
"""


class VideoWindow(QMainWindow):
    def __init__(self, video_path: Path) -> None:
        super().__init__()
        self.video_path: Path | None = None

        self.setWindowTitle("Video Preview")
        self.resize(900, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.video_widget = QVideoWidget(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.durationChanged.connect(self._update_duration)
        self.player.positionChanged.connect(self._update_position)

        play_button = QPushButton("再生")
        play_button.clicked.connect(self.player.play)

        pause_button = QPushButton("一時停止")
        pause_button.clicked.connect(self.player.pause)

        stop_button = QPushButton("停止")
        stop_button.clicked.connect(self.player.stop)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.player.setPosition)

        self.path_label = QLabel()
        self.path_label.setObjectName("videoPathLabel")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(play_button)
        controls.addWidget(pause_button)
        controls.addWidget(stop_button)
        controls.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.video_widget, stretch=1)
        layout.addWidget(self.position_slider)
        layout.addLayout(controls)
        layout.addWidget(self.path_label)

        container = QWidget()
        container.setObjectName("videoPanel")
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.load_video(video_path)

    def load_video(self, video_path: Path, *, auto_play: bool = True) -> None:
        self.video_path = video_path
        self.setWindowTitle(f"Video Preview - {video_path.name}")
        self.path_label.setText(str(video_path))
        self.position_slider.setValue(0)
        self.position_slider.setRange(0, 0)
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))

        if auto_play:
            self.player.play()

    def _update_duration(self, duration: int) -> None:
        self.position_slider.setRange(0, duration)

    def _update_position(self, position: int) -> None:
        if self.position_slider.isSliderDown():
            return

        self.position_slider.setValue(position)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.player.stop()
        self.player.setSource(QUrl())
        super().closeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Video Analyzer")
        self.resize(1280, 760)

        self.watch_folder: Path | None = None
        self.known_files: dict[Path, float] = {}
        self.video_window: VideoWindow | None = None
        self.is_monitoring = False
        self.settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self._handle_directory_changed)

        self._build_actions()
        self._build_menu()
        self._build_ui()
        self._connect_signals()

        status_bar = QStatusBar(self)
        status_bar.showMessage("監視フォルダを選択してください")
        self.setStatusBar(status_bar)
        self._restore_watch_folder()

    def _build_actions(self) -> None:
        self.choose_folder_action = QAction("監視フォルダを選択", self)
        self.choose_folder_action.triggered.connect(self.choose_watch_folder)

        self.scan_action = QAction("再スキャン", self)
        self.scan_action.triggered.connect(self.scan_watch_folder)

        self.toggle_watch_action = QAction("監視開始", self)
        self.toggle_watch_action.triggered.connect(self.toggle_monitoring)

        self.copy_action = QAction("結果をコピー", self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.triggered.connect(self.copy_results_to_clipboard)

        self.clear_results_action = QAction("結果をクリア", self)
        self.clear_results_action.triggered.connect(self.clear_results)

        self.open_video_action = QAction("動画を別ウィンドウで開く", self)
        self.open_video_action.triggered.connect(self.open_selected_video)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("ファイル")
        file_menu.addAction(self.choose_folder_action)
        file_menu.addAction(self.toggle_watch_action)
        file_menu.addAction(self.scan_action)

        result_menu = self.menuBar().addMenu("結果")
        result_menu.addAction(self.copy_action)
        result_menu.addAction(self.clear_results_action)
        result_menu.addAction(self.open_video_action)

    def _build_ui(self) -> None:
        app_title = QLabel("Video Analyzer")
        app_title.setObjectName("appTitle")

        app_subtitle = QLabel("監視フォルダに追加された動画を確認しながら、解析結果を表へ蓄積します。")
        app_subtitle.setObjectName("appSubtitle")

        header = QWidget()
        header.setObjectName("appHeader")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(2)
        header_layout.addWidget(app_title)
        header_layout.addWidget(app_subtitle)
        header.setLayout(header_layout)

        self.folder_path_input = QLineEdit()
        self.folder_path_input.setReadOnly(True)
        self.folder_path_input.setPlaceholderText("監視する動画フォルダを選択")

        choose_button = QPushButton("選択")
        choose_button.clicked.connect(self.choose_watch_folder)

        scan_button = QPushButton("再スキャン")
        scan_button.clicked.connect(self.scan_watch_folder)

        self.toggle_watch_button = QPushButton("監視開始")
        self.toggle_watch_button.setProperty("variant", "primary")
        self.toggle_watch_button.clicked.connect(self.toggle_monitoring)

        folder_bar = QWidget()
        folder_bar.setObjectName("folderBar")
        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(14, 12, 14, 12)
        folder_row.setSpacing(10)
        folder_row.addWidget(QLabel("監視フォルダ"))
        folder_row.addWidget(self.folder_path_input, stretch=1)
        folder_row.addWidget(choose_button)
        folder_row.addWidget(self.toggle_watch_button)
        folder_row.addWidget(scan_button)
        folder_bar.setLayout(folder_row)

        self.result_table = QTableWidget(0, len(RESULT_COLUMNS))
        self.result_table.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSortingEnabled(False)
        self.result_table.setShowGrid(False)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.verticalHeader().setDefaultSectionSize(42)

        copy_button = QPushButton("結果をコピー")
        copy_button.clicked.connect(self.copy_results_to_clipboard)

        clear_button = QPushButton("結果をクリア")
        clear_button.setProperty("variant", "danger")
        clear_button.clicked.connect(self.clear_results)

        open_video_button = QPushButton("動画を開く")
        open_video_button.clicked.connect(self.open_selected_video)

        table_actions = QHBoxLayout()
        table_actions.setSpacing(8)
        table_actions.addWidget(copy_button)
        table_actions.addWidget(clear_button)
        table_actions.addWidget(open_video_button)
        table_actions.addStretch()

        results_panel = QWidget()
        results_panel.setObjectName("resultsPanel")
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(16, 16, 16, 16)
        results_layout.setSpacing(12)
        section_title = QLabel("解析結果")
        section_title.setObjectName("sectionTitle")
        results_layout.addWidget(section_title)
        results_layout.addLayout(table_actions)
        results_layout.addWidget(self.result_table, stretch=1)
        results_panel.setLayout(results_layout)

        self.selected_file_label = QLabel("未選択")
        self.selected_file_label.setWordWrap(True)
        self.selected_status_label = QLabel("-")
        self.detected_count_label = QLabel("0")
        self.watch_status_label = QLabel("未開始")

        summary_box = QGroupBox("状態")
        summary_form = QFormLayout()
        summary_form.setContentsMargins(6, 8, 6, 6)
        summary_form.setHorizontalSpacing(12)
        summary_form.setVerticalSpacing(10)
        summary_form.addRow("監視", self.watch_status_label)
        summary_form.addRow("検出数", self.detected_count_label)
        summary_form.addRow("選択動画", self.selected_file_label)
        summary_form.addRow("解析状態", self.selected_status_label)
        summary_box.setLayout(summary_form)

        guidance = QLabel(
            "フォルダに動画が追加または更新されると、解析中の行として表に追加されます。"
            "解析値は後続実装用の仮置きです。"
        )
        guidance.setObjectName("guidanceLabel")
        guidance.setWordWrap(True)

        side_panel = QWidget()
        side_panel.setObjectName("sidePanel")
        side_layout = QVBoxLayout()
        side_layout.setContentsMargins(16, 16, 16, 16)
        side_layout.setSpacing(14)
        side_layout.addWidget(summary_box)
        side_layout.addWidget(guidance)
        side_layout.addStretch()
        side_panel.setLayout(side_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(results_panel)
        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)
        root_layout.addWidget(header)
        root_layout.addWidget(folder_bar)
        root_layout.addWidget(splitter, stretch=1)
        root.setLayout(root_layout)

        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.result_table.itemSelectionChanged.connect(self.update_selected_file_summary)
        self.result_table.itemDoubleClicked.connect(lambda _: self.open_selected_video())

    def choose_watch_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "監視フォルダを選択")
        if not folder:
            return

        self.set_watch_folder(Path(folder))

    def set_watch_folder(self, folder: Path, *, start_monitoring: bool = True) -> None:
        self.watch_folder = folder
        self.folder_path_input.setText(str(folder))
        self.settings.setValue(SETTINGS_WATCH_FOLDER_KEY, str(folder))

        if start_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def scan_watch_folder(self) -> None:
        if self.watch_folder is None:
            QMessageBox.information(self, "監視フォルダ未設定", "先に監視フォルダを選択してください。")
            return

        for video_path in sorted(self.watch_folder.iterdir()):
            if video_path.is_file() and video_path.suffix.lower() in VIDEO_EXTENSIONS:
                self._upsert_video_result(video_path)

        self._update_counts()

    def _handle_directory_changed(self, _folder: str) -> None:
        if not self.is_monitoring:
            return

        self.statusBar().showMessage("フォルダ更新を検出しました。確認中...")
        QTimer.singleShot(500, self.scan_watch_folder)

    def toggle_monitoring(self) -> None:
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self) -> None:
        if self.watch_folder is None:
            QMessageBox.information(self, "監視フォルダ未設定", "先に監視フォルダを選択してください。")
            return

        if not self.watch_folder.is_dir():
            QMessageBox.warning(self, "監視フォルダなし", f"監視フォルダが存在しません:\n{self.watch_folder}")
            return

        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())

        self.watcher.addPath(str(self.watch_folder))
        self.is_monitoring = True
        self._update_monitoring_controls()
        self.statusBar().showMessage(f"監視中: {self.watch_folder}")
        self.scan_watch_folder()

    def stop_monitoring(self) -> None:
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())

        self.is_monitoring = False
        self._update_monitoring_controls()
        if self.watch_folder is None:
            self.statusBar().showMessage("監視フォルダを選択してください")
        else:
            self.statusBar().showMessage(f"監視停止中: {self.watch_folder}")

    def _update_monitoring_controls(self) -> None:
        if self.is_monitoring:
            self.watch_status_label.setText("監視中")
            self.toggle_watch_action.setText("監視停止")
            self.toggle_watch_button.setText("監視停止")
            return

        self.watch_status_label.setText("停止中" if self.watch_folder else "未開始")
        self.toggle_watch_action.setText("監視開始")
        self.toggle_watch_button.setText("監視開始")

    def _restore_watch_folder(self) -> None:
        saved_folder = self.settings.value(SETTINGS_WATCH_FOLDER_KEY, "", str)
        if not saved_folder:
            self._update_monitoring_controls()
            return

        folder = Path(saved_folder)
        if not folder.is_dir():
            self._update_monitoring_controls()
            self.statusBar().showMessage(f"前回の監視フォルダが見つかりません: {folder}")
            return

        self.set_watch_folder(folder, start_monitoring=False)

    def _upsert_video_result(self, video_path: Path) -> None:
        modified_at = video_path.stat().st_mtime
        previous_modified_at = self.known_files.get(video_path)

        if previous_modified_at == modified_at:
            return

        self.known_files[video_path] = modified_at
        existing_row = self._find_row_by_path(video_path)

        if existing_row is None:
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
        else:
            row = existing_row

        status = "解析中"
        values = [
            str(row + 1),
            datetime.fromtimestamp(modified_at).strftime("%Y-%m-%d %H:%M:%S"),
            video_path.name,
            status,
            "-",
            "-",
            "-",
            str(video_path),
            "",
        ]

        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if column == 7:
                item.setData(Qt.ItemDataRole.UserRole, str(video_path))
            self.result_table.setItem(row, column, item)

        self._show_video_window(video_path)

    def _find_row_by_path(self, video_path: Path) -> int | None:
        target = str(video_path)
        for row in range(self.result_table.rowCount()):
            item = self.result_table.item(row, 7)
            if item and item.text() == target:
                return row
        return None

    def update_selected_file_summary(self) -> None:
        row = self._selected_row()
        if row is None:
            self.selected_file_label.setText("未選択")
            self.selected_status_label.setText("-")
            return

        self.selected_file_label.setText(self.result_table.item(row, 2).text())
        self.selected_status_label.setText(self.result_table.item(row, 3).text())

    def open_selected_video(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "動画未選択", "表から動画を選択してください。")
            return

        path_item = self.result_table.item(row, 7)
        if path_item is None:
            return

        video_path = Path(path_item.text())
        if not video_path.exists():
            QMessageBox.warning(self, "動画が見つかりません", f"動画ファイルが存在しません:\n{video_path}")
            return

        self._show_video_window(video_path)

    def _show_video_window(self, video_path: Path) -> None:
        if self.video_window is not None:
            self.video_window.load_video(video_path)
            self.video_window.show()
            self.video_window.raise_()
            self.video_window.activateWindow()
            return

        window = VideoWindow(video_path)
        window.destroyed.connect(lambda _obj=None: setattr(self, "video_window", None))
        window.show()
        self.video_window = window

    def copy_results_to_clipboard(self) -> None:
        if self.result_table.rowCount() == 0:
            QMessageBox.information(self, "コピー対象なし", "コピーできる解析結果がありません。")
            return

        lines = []
        for row in range(self.result_table.rowCount()):
            values = []
            for column in range(self.result_table.columnCount()):
                item = self.result_table.item(row, column)
                values.append(item.text() if item else "")
            lines.append("\t".join(values))

        QApplication.clipboard().setText("\n".join(lines))
        self.statusBar().showMessage("解析結果をクリップボードにコピーしました")

    def clear_results(self) -> None:
        self.result_table.setRowCount(0)
        self.known_files.clear()
        self.selected_file_label.setText("未選択")
        self.selected_status_label.setText("-")
        self._update_counts()
        self.statusBar().showMessage("解析結果をクリアしました")

    def _selected_row(self) -> int | None:
        selected_rows = self.result_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        return selected_rows[0].row()

    def _update_counts(self) -> None:
        self.detected_count_label.setText(str(self.result_table.rowCount()))
        self.statusBar().showMessage(f"{self.result_table.rowCount()} 件の動画を検出済み")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.video_window is not None:
            self.video_window.close()

        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    return app.exec()
