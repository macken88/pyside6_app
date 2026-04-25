from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QTimer, Qt, QUrl
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
RESULT_COLUMNS = [
    "No.",
    "検出日時",
    "動画ファイル",
    "状態",
    "長さ",
    "解析値A",
    "解析値B",
    "パス",
]


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
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        controls = QHBoxLayout()
        controls.addWidget(play_button)
        controls.addWidget(pause_button)
        controls.addWidget(stop_button)
        controls.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(self.video_widget, stretch=1)
        layout.addWidget(self.position_slider)
        layout.addLayout(controls)
        layout.addWidget(self.path_label)

        container = QWidget()
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

        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self._handle_directory_changed)

        self._build_actions()
        self._build_menu()
        self._build_ui()
        self._connect_signals()

        status_bar = QStatusBar(self)
        status_bar.showMessage("監視フォルダを選択してください")
        self.setStatusBar(status_bar)

    def _build_actions(self) -> None:
        self.choose_folder_action = QAction("監視フォルダを選択", self)
        self.choose_folder_action.triggered.connect(self.choose_watch_folder)

        self.scan_action = QAction("再スキャン", self)
        self.scan_action.triggered.connect(self.scan_watch_folder)

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
        file_menu.addAction(self.scan_action)

        result_menu = self.menuBar().addMenu("結果")
        result_menu.addAction(self.copy_action)
        result_menu.addAction(self.clear_results_action)
        result_menu.addAction(self.open_video_action)

    def _build_ui(self) -> None:
        self.folder_path_input = QLineEdit()
        self.folder_path_input.setReadOnly(True)
        self.folder_path_input.setPlaceholderText("監視する動画フォルダを選択")

        choose_button = QPushButton("選択")
        choose_button.clicked.connect(self.choose_watch_folder)

        scan_button = QPushButton("再スキャン")
        scan_button.clicked.connect(self.scan_watch_folder)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("監視フォルダ"))
        folder_row.addWidget(self.folder_path_input, stretch=1)
        folder_row.addWidget(choose_button)
        folder_row.addWidget(scan_button)

        self.result_table = QTableWidget(0, len(RESULT_COLUMNS))
        self.result_table.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSortingEnabled(False)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.horizontalHeader().setStretchLastSection(True)

        copy_button = QPushButton("結果をコピー")
        copy_button.clicked.connect(self.copy_results_to_clipboard)

        clear_button = QPushButton("結果をクリア")
        clear_button.clicked.connect(self.clear_results)

        open_video_button = QPushButton("動画を開く")
        open_video_button.clicked.connect(self.open_selected_video)

        table_actions = QHBoxLayout()
        table_actions.addWidget(copy_button)
        table_actions.addWidget(clear_button)
        table_actions.addWidget(open_video_button)
        table_actions.addStretch()

        results_panel = QWidget()
        results_layout = QVBoxLayout()
        results_layout.addWidget(QLabel("解析結果"))
        results_layout.addWidget(self.result_table, stretch=1)
        results_layout.addLayout(table_actions)
        results_panel.setLayout(results_layout)

        self.selected_file_label = QLabel("未選択")
        self.selected_file_label.setWordWrap(True)
        self.selected_status_label = QLabel("-")
        self.detected_count_label = QLabel("0")
        self.watch_status_label = QLabel("未開始")

        summary_box = QGroupBox("状態")
        summary_form = QFormLayout()
        summary_form.addRow("監視", self.watch_status_label)
        summary_form.addRow("検出数", self.detected_count_label)
        summary_form.addRow("選択動画", self.selected_file_label)
        summary_form.addRow("解析状態", self.selected_status_label)
        summary_box.setLayout(summary_form)

        guidance = QLabel(
            "フォルダに動画が追加または更新されると、解析中の行として表に追加されます。"
            "解析値は後続実装用の仮置きです。"
        )
        guidance.setWordWrap(True)

        side_panel = QWidget()
        side_layout = QVBoxLayout()
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
        root_layout.addLayout(folder_row)
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

    def set_watch_folder(self, folder: Path) -> None:
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())

        self.watch_folder = folder
        self.folder_path_input.setText(str(folder))
        self.watcher.addPath(str(folder))
        self.watch_status_label.setText("監視中")
        self.statusBar().showMessage(f"監視中: {folder}")
        self.scan_watch_folder()

    def scan_watch_folder(self) -> None:
        if self.watch_folder is None:
            QMessageBox.information(self, "監視フォルダ未設定", "先に監視フォルダを選択してください。")
            return

        for video_path in sorted(self.watch_folder.iterdir()):
            if video_path.is_file() and video_path.suffix.lower() in VIDEO_EXTENSIONS:
                self._upsert_video_result(video_path)

        self._update_counts()

    def _handle_directory_changed(self, _folder: str) -> None:
        self.statusBar().showMessage("フォルダ更新を検出しました。確認中...")
        QTimer.singleShot(500, self.scan_watch_folder)

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


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
