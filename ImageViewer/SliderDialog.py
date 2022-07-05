from typing import Callable, Optional

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QSlider,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal

class SliderDialog(QDialog):
    colourContrastBrightnessSignal = Signal(float, float, float)
    acceptedSignal = Signal()
    rejectedSignal = Signal()

    def __init__(
        self,
        sliderChangedFunc: Callable[[float, float, float], None],
        acceptedFunc: Callable[[], None],
        rejectedFunc: Callable[[], None],
        parent: Optional[QWidget] = None,
        f: Qt.WindowFlags = Qt.Dialog) -> None:
        super().__init__(parent, f)

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
        self._colourSlider.setMinimum(0)
        self._colourSlider.setMaximum(20)
        self._colourSlider.setValue(10)
        self._colourSlider.valueChanged.connect(self._sliderChanged) # type: ignore

        # Set the contrast slider options
        self._contrastSlider.setTracking(True)
        self._contrastSlider.setMinimum(0)
        self._contrastSlider.setMaximum(20)
        self._contrastSlider.setValue(10)
        self._contrastSlider.valueChanged.connect(self._sliderChanged) # type: ignore

        # Set the brightness slider options
        self._brightnessSlider.setTracking(True)
        self._brightnessSlider.setMinimum(0)
        self._brightnessSlider.setMaximum(20)
        self._brightnessSlider.setValue(10)
        self._brightnessSlider.valueChanged.connect(self._sliderChanged) # type: ignore

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
        self._dialogButtonBox.accepted.connect(self.accept) # type: ignore
        self._dialogButtonBox.rejected.connect(self.reject) # type: ignore

        # Add the OK and Cancel buttons to the vbox layout
        self._vBoxLayout.addWidget(self._dialogButtonBox)

        # Connect the colour, contrast and brightness changed signal
        self.colourContrastBrightnessSignal.connect(sliderChangedFunc)

        # Connect accept and reject to the accepted and rejected functions
        self.acceptedSignal.connect(acceptedFunc)
        self.rejectedSignal.connect(rejectedFunc)

        # Add the vbox layout to the dialog
        self.setLayout(self._vBoxLayout)

    def _sliderChanged(self) -> None:
        # Scale the colour, contrast and brightness values
        colourValue = self._colourSlider.value() / 10
        contrastValue = self._contrastSlider.value() / 10
        brightnessValue = self._brightnessSlider.value() / 10

        # Send the values to the image
        self.colourContrastBrightnessSignal.emit(colourValue, contrastValue, brightnessValue)

    def accept(self) -> None:
        # Send the accepted signal
        self.acceptedSignal.emit()

        # Close the dialog
        super().accept()

    def reject(self) -> None:
        # Send the rejected signal, this function is also called when pressing escape
        self.rejectedSignal.emit()

        # Close the dialog
        super().reject()
