from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QSlider,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt

from ImageViewer.FullImage import FullImage

class SliderDialog(QDialog):
    def __init__(self, fullImage: FullImage, parent: Optional[QWidget] = None, f: Qt.WindowFlags = Qt.Dialog) -> None:
        super().__init__(parent, f)

        # Create a class member for FullImage
        self._fullImage = fullImage

        # Create an overall VBoxLayout
        self._vBoxLayout = QVBoxLayout()

        # Create a grid layout for the sliders and their labels
        self._gridLayout = QGridLayout()

        # Create the sliders
        self._colourSlider = QSlider(Qt.Orientation.Horizontal)
        self._contrastSlider = QSlider(Qt.Orientation.Horizontal)
        self._brightnessSlider = QSlider(Qt.Orientation.Horizontal)

        # Set the colour slider options
        self._colourSlider.setTracking(True)
        self._colourSlider.setMinimum(-10)
        self._colourSlider.setMaximum(10)
        self._colourSlider.valueChanged.connect(self._fullImage.SliderColourChanged) # type: ignore

        # Set the contrast slider options
        self._contrastSlider.setTracking(True)
        self._contrastSlider.setMinimum(-10)
        self._contrastSlider.setMaximum(10)
        self._contrastSlider.valueChanged.connect(self._fullImage.SliderContrastChanged) # type: ignore

        # Set the brightness slider options
        self._brightnessSlider.setTracking(True)
        self._brightnessSlider.setMinimum(-10)
        self._brightnessSlider.setMaximum(10)
        self._brightnessSlider.valueChanged.connect(self._fullImage.SliderBrightnessChanged) # type: ignore

        # Add the colour label and slider
        self._gridLayout.addWidget(QLabel('Colour'), 0, 0)
        self._gridLayout.addWidget(self._colourSlider, 0, 1)

        # Add the contrast label and slider
        self._gridLayout.addWidget(QLabel('Contrast'), 1, 0)
        self._gridLayout.addWidget(self._contrastSlider, 1, 1)

        # Add the brightness label and slider
        self._gridLayout.addWidget(QLabel('Brightness'), 2, 0)
        self._gridLayout.addWidget(self._brightnessSlider, 2, 1)

        # Add the grid layout to the vbox layout
        self._vBoxLayout.addLayout(self._gridLayout)

        # Create the OK and Cancel buttons
        self._dialogButtonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # Connect the OK and Cancel buttons
        self._dialogButtonBox.accepted.connect(self._accepted) # type: ignore
        self._dialogButtonBox.rejected.connect(self._rejected) # type: ignore

        # Add the OK and Cancel buttons to the vbox layout
        self._vBoxLayout.addWidget(self._dialogButtonBox)

        # Add the vbox layout to the dialog
        self.setLayout(self._vBoxLayout)

    def _accepted(self) -> None:
        self._fullImage.Colour(factor=(self._colourSlider.value() / 10) + 1.0)
        self._fullImage.Contrast(factor=(self._contrastSlider.value() / 10) + 1.0)
        self._fullImage.Brightness(factor=(self._brightnessSlider.value() / 10) + 1.0)

        self.close()

    def _rejected(self) -> None:
        self._fullImage.UpdatePixmap()
        self.close()
