from datetime import datetime
import logging
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import QEvent

class TrialWindow(QMainWindow):
    def __init__(self, parent = None) -> None:
        super().__init__(parent)
        self.label = QLabel()
        self.setCentralWidget(self.label)

    def event(self, event: QEvent) -> bool:
        logging.log(logging.DEBUG, f'{event.type()}')
        print(event.type())
        return super().event(event)

logging.basicConfig(
    filename=Path.home() / f'trialWindow {datetime.now().time()}.txt',
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

logging.log(logging.DEBUG, f'argv: {sys.argv}')

app = QApplication()

window = TrialWindow()
window.label.setText(str(sys.argv))

window.show()

sys.exit(app.exec_())
# print('Hello')
