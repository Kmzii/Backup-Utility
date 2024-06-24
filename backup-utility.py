import sys
import os
import shutil
import json
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QMessageBox, QFileDialog, QProgressBar
from PyQt5.QtCore import QSize, Qt, QThread, pyqtSignal

class WorkerThread(QThread):
    progressChanged = pyqtSignal(int)

    def __init__(self, source_folder, dest_folder):
        super().__init__()
        self.source_folder = source_folder
        self.dest_folder = dest_folder

    def run(self):
        files_detected = 0
        files_copied = 0
        files_skipped = 0

        total_files = sum(len(files) for _, _, files in os.walk(self.source_folder))

        for root, _, files in os.walk(self.source_folder):
            for file in files:
                source_path = os.path.join(root, file)
                dest_path = os.path.join(self.dest_folder, file)

                files_detected += 1

                if not os.path.exists(dest_path) or os.path.getmtime(source_path) > os.path.getmtime(dest_path):
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    files_copied += 1
                    logging.info(f"Copied {source_path} to {dest_path}")
                else:
                    files_skipped += 1

                # Calculate progress percentage
                progress = int((files_detected / total_files) * 100)
                self.progressChanged.emit(progress)

        logging.info(f"Detected {files_detected} files in {self.source_folder}, copied {files_copied}, skipped {files_skipped}")

class BackupUtility(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backup Utility")
        self.setFixedSize(700, 500)  # Setting fixed window size
        self.folder_list = []
        self.destination = ''
        self.last_folder = ''

        self.init_ui()
        self.load_config()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='.venv/backup.log',
            filemode='w'
        )

    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Top layout for list of folders and total folders label
        top_layout = QHBoxLayout()

        # Label for list of folders
        label_folders = QLabel("List of Folders:")
        label_folders.setStyleSheet("font-size: 16px;")  # Set font size
        top_layout.addWidget(label_folders)

        # Total folders label
        self.total_folders_label = QLabel(f"Total Folders: {len(self.folder_list)}")
        self.total_folders_label.setStyleSheet("font-size: 16px;")  # Set font size
        self.total_folders_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Align text to the right
        top_layout.addWidget(self.total_folders_label)

        main_layout.addLayout(top_layout)

        # List widget for folders
        self.listbox = QListWidget()
        self.listbox.setStyleSheet("font-size: 16px;")  # Set font size
        main_layout.addWidget(self.listbox)

        # Horizontal layout for buttons and destination label
        buttons_layout = QHBoxLayout()

        # Buttons
        self.add_button = QPushButton("Add Folder")
        self.remove_button = QPushButton("Remove Folder")
        self.destination_button = QPushButton("Set Destination")
        self.backup_button = QPushButton("Backup")

        # Set larger icon size for buttons
        icon_size = QSize(32, 32)  # Icon size in pixels
        self.add_button.setIconSize(icon_size)
        self.remove_button.setIconSize(icon_size)
        self.destination_button.setIconSize(icon_size)
        self.backup_button.setIconSize(icon_size)

        # Set font size for buttons
        self.add_button.setStyleSheet("font-size: 16px;")
        self.remove_button.setStyleSheet("font-size: 16px;")
        self.destination_button.setStyleSheet("font-size: 16px;")
        self.backup_button.setStyleSheet("font-size: 16px;")

        # Add buttons to the horizontal layout
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.addWidget(self.destination_button)
        buttons_layout.addWidget(self.backup_button)

        # Add the horizontal layout to the main layout
        main_layout.addLayout(buttons_layout)

        # Destination label
        self.destination_label = QLabel(f"Destination: {self.destination if self.destination else 'Not set'}")
        self.destination_label.setStyleSheet("font-size: 16px;")  # Set font size
        main_layout.addWidget(self.destination_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Connect button signals
        self.add_button.clicked.connect(self.add_folder)
        self.remove_button.clicked.connect(self.remove_folder)
        self.destination_button.clicked.connect(self.set_destination)
        self.backup_button.clicked.connect(self.backup_folders)

        self.setCentralWidget(main_widget)

    def load_config(self):
        try:
            with open('.venv/config.json', 'r') as file:
                config = json.load(file)
                self.folder_list = config.get('folders', [])
                self.destination = config.get('destination', '')
                self.last_folder = config.get('last_folder', '')
                self.update_listbox()
                self.update_destination_label()
                self.update_total_folders_label()
        except FileNotFoundError:
            pass

    def save_config(self):
        config = {
            'folders': self.folder_list,
            'destination': self.destination,
            'last_folder': self.last_folder
        }
        with open('.venv/config.json', 'w') as file:
            json.dump(config, file)

    def add_folder(self):
        try:
            initialdir = os.path.dirname(self.last_folder) if self.last_folder else None
            selected_folder = QFileDialog.getExistingDirectory(self, "Select Folder", directory=initialdir)
            if selected_folder:
                if selected_folder in self.folder_list:
                    QMessageBox.warning(self, "Folder Already Added", f"The folder '{selected_folder}' is already in the list.")
                else:
                    self.folder_list.append(selected_folder)
                    self.update_listbox()
                    self.last_folder = selected_folder
                    self.update_total_folders_label()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add folder: {str(e)}")

    def remove_folder(self):
        selected_items = self.listbox.selectedItems()
        if selected_items:
            selected_folder = selected_items[0].text()
            self.folder_list.remove(selected_folder)
            self.update_listbox()
            self.update_total_folders_label()

    def set_destination(self):
        try:
            dest = QFileDialog.getExistingDirectory(self, "Select Destination Folder", directory=self.destination)
            if dest:
                self.destination = dest
                self.update_destination_label()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set destination folder: {str(e)}")

    def backup_folders(self):
        if not self.destination:
            QMessageBox.warning(self, "No Destination", "Please set a destination folder first.")
            return

        try:
            for folder_path in self.folder_list:
                folder_name = os.path.basename(folder_path)
                dest_folder = os.path.join(self.destination, folder_name)

                if not os.path.exists(dest_folder):
                    shutil.copytree(folder_path, dest_folder)
                    logging.info(f"Created new folder: {dest_folder}")

                    # Log initial file count
                    self.copy_files(folder_path, dest_folder)

                else:
                    self.copy_files(folder_path, dest_folder)

            QMessageBox.information(self, "Backup Completed", "Backup completed successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during backup: {str(e)}")
            logging.error(f"Backup failed: {str(e)}")

    def copy_files(self, source_folder, dest_folder):
        try:
            worker_thread = WorkerThread(source_folder, dest_folder)
            worker_thread.progressChanged.connect(self.update_progress)
            worker_thread.start()
            worker_thread.wait()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during copying files: {str(e)}")
            logging.error(f"Error occurred during copying files: {str(e)}")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_listbox(self):
        self.listbox.clear()
        for folder in self.folder_list:
            self.listbox.addItem(folder)

    def update_destination_label(self):
        self.destination_label.setText(f"Destination: {self.destination if self.destination else 'Not set'}")

    def update_total_folders_label(self):
        self.total_folders_label.setText(f"Total Folders: {len(self.folder_list)}")

    def closeEvent(self, event):
        try:
            self.save_config()
            event.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = BackupUtility()
    mainWindow.show()
    sys.exit(app.exec_())
