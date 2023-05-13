from typing import Optional

from PySide6.QtWidgets import QDialog, QWidget, QLabel, QGridLayout, QPushButton
from PySide6.QtCore import Qt

class ImageInfoDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], info: dict[str, str], f: Qt.WindowType = Qt.WindowType.Dialog) -> None:
        # Call the base initialiser adding the frameless window hint
        super().__init__(parent, f | Qt.WindowType.FramelessWindowHint)

        # Create a grid layout
        self._layout = QGridLayout(self)

        # Set the layout to be fixed size
        self._layout.setSizeConstraint(QGridLayout.SizeConstraint.SetFixedSize)

        # initialse the row number to 0
        rowNumber = 0

        # Iterate over the items in the info dict
        for label, data in info.items():
            # Add a widget for the label
            self._layout.addWidget(QLabel(label), rowNumber, 0)

            # Create a widget for the date
            dataLabel = QLabel(data)

            # Right align the data
            dataLabel.setAlignment(Qt.AlignmentFlag.AlignRight)

            # Add the data widget to the layout
            self._layout.addWidget(dataLabel, rowNumber, 1)

            # Increment the row number
            rowNumber += 1

        # Create a close button
        closeButton = QPushButton('Close', self)

        # Connect the button to the close function
        closeButton.clicked.connect(self.close) # type: ignore

        # Add the button to the last row in the layout
        self._layout.addWidget(closeButton, rowNumber, 1)

        # Add the layout to the dialog
        self.setLayout(self._layout)
