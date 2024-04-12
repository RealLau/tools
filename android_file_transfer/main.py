import os.path
import subprocess
import sys

from PySide6.QtCore import QDir, QProcess, Qt
from PySide6.QtGui import QAction, QScreen
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QPushButton, QFileSystemModel, QMenu, QStatusBar, QWidget, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QStyle
from pathlib import Path

def clear_children(tree_item):
    while tree_item.childCount() > 0:
        child = tree_item.child(0)
        tree_item.removeChild(child)
class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.process = None
        self.setWindowTitle("Android File Manager")

        self.android_tree = QTreeWidget()
        self.android_tree.setHeaderLabel("/sdcard")
        self.android_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.android_tree.customContextMenuRequested.connect(self.show_android_context_menu)
        self.root = self.android_tree.invisibleRootItem()
        self.root.setData(0, Qt.UserRole, {"name": "/sdcard", "typ": "directory", "path": "/sdcard"})
        self.android_tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.pc_model = QFileSystemModel()
        self.pc_model.setRootPath(QDir.currentPath())
        self.pc_tree = QTreeView()
        self.pc_tree.setModel(self.pc_model)
        self.pc_tree.setRootIndex(self.pc_model.index(QDir.currentPath()))

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(lambda: self.populate_tree(self.root))

        self.setStatusBar(QStatusBar(self))

        layout = QHBoxLayout()
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.android_tree)
        layout.addWidget(self.pc_tree)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.default_dir = "/sdcard"
        self.setStatusBar(QStatusBar(self))

    def on_item_double_clicked(self, item):
        item_data = item.data(0, Qt.UserRole)
        if item_data.get("typ") == "directory":
            self.populate_tree(parent_node=item)

    def populate_tree(self, parent_node):
        parent_path = parent_node.data(0, Qt.UserRole).get("path")
        result = subprocess.run(["adb", "shell", f"cd {parent_path} && file *"], stdout=subprocess.PIPE, text=True)
        if "no devices/emulators" in result.stdout:
            self.statusBar().showMessage("no devices connected")
            return

        clear_children(parent_node)

        item_list = result.stdout.splitlines()
        for item in item_list:
            item = item.strip().split(":")
            name = item[0]
            typ = item[1].strip()
            sub_tree_item = QTreeWidgetItem(parent_node, [name])
            sub_tree_item.setIcon(0, QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon) if typ == "directory" else QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            current_path = parent_path + "/" + name
            sub_tree_item.setData(0, Qt.UserRole, {"name": name, "typ": typ, "path": current_path})

    def show_android_context_menu(self, point):
        item = self.android_tree.itemAt(point)
        if item is not None:
            item_data = item.data(0, Qt.UserRole)
            menu = QMenu()
            transfer_action = QAction("Transfer")
            transfer_action.triggered.connect(lambda: self.transfer_file(item_data.get("path")))
            menu.addAction(transfer_action)
            menu.exec(self.android_tree.viewport().mapToGlobal(point))

    def transfer_file(self, android_file_path):
        pc_index = self.pc_tree.currentIndex()
        pc_dir = self.pc_model.filePath(pc_index)
        if not os.path.isdir(pc_dir):
            self.statusBar().showMessage("Please choose a directory")
            return
        if pc_dir and android_file_path:
            self.statusBar().showMessage("Transferring...")
            file_name = Path(android_file_path).name
            new_file = os.path.join(pc_dir, file_name)
            self.process = QProcess(self)
            self.process.finished.connect(lambda: self.process_finished(new_file))
            self.process.start("adb", ["pull", android_file_path, pc_dir])

    def process_finished(self, image_path):
        self.statusBar().showMessage("Transfer completed.")
        self.process = None
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, image_path])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileManager()
    window.setGeometry(100, 100, 1200, 800)
    center = QScreen.availableGeometry(QApplication.primaryScreen()).center()
    geo = window.frameGeometry()
    geo.moveCenter(center)
    window.move(geo.topLeft())
    window.show()
    sys.exit(app.exec())
