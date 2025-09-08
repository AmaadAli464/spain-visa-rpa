import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
from workflows.main import run_main_workflow

class WorkerThread(QThread):
    log_signal = pyqtSignal(str)

    def run(self):
        try:
            self.log_signal.emit("Starting Spain Visa RPA Workflow...")
            run_main_workflow()
            self.log_signal.emit("Workflow finished successfully.")
        except Exception as e:
            self.log_signal.emit(f"Error: {str(e)}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spain Visa RPA Bot")
        self.setGeometry(400, 400, 700, 600)

        layout = QVBoxLayout()

        self.label = QLabel("Spain Visa RPA Automation")
        layout.addWidget(self.label)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.button = QPushButton("Start Workflow")
        self.button.clicked.connect(self.start_workflow)
        layout.addWidget(self.button)

        self.setLayout(layout)
        self.worker = None

    def start_workflow(self):
        self.button.setEnabled(False)
        self.log_area.append("▶ Running workflow...")
        self.worker = WorkerThread()
        self.worker.log_signal.connect(self.update_log)
        self.worker.finished.connect(lambda: self.button.setEnabled(True))
        self.worker.start()

    def update_log(self, message: str):
        self.log_area.append(message)
