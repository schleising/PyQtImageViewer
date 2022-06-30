from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
import logging

from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtGui import (
    QPixmap,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QFontMetrics,
    QPalette,
    QBitmap,
)
from PySide6.QtCore import Qt, Signal

from PIL import Image
from PIL.ImageQt import ImageQt

# This seems to be necessary to ensure webp images can be loaded at startup
import PIL.WebPImagePlugin as _

from ImageViewer.Constants import DODGER_BLUE, DODGER_BLUE_50PC

class PixmapLabel(QLabel):
    def __init__(self):
        super().__init__()

        # Indicate whether the thumbnail containing this pixmap is highlighted
        self.highlighted = False

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        if self.highlighted:
            # Create a QPainter
            painter = QPainter()

            # Get the pixmap rect
            rect = self.pixmap().rect()

            # Move the rect to the centre of the label
            rect.moveCenter(self.rect().center())

            if self.pixmap().hasAlpha():
                # If the image has an alpha channel use this as a mask
                mask = self.pixmap().mask()
            else:
                # Otherwose leave the mask set to None
                mask = None

            # Initialise the painter
            painter.begin(self)

            if mask is not None:
                # If there is a mask, use this to clip the paint operation
                painter.setClipRegion(mask)

            # Set the fill to Dodger Blue 50% opaque
            painter.setBrush(DODGER_BLUE_50PC)

            # Set the pen to Dodger Blue too
            painter.setPen(DODGER_BLUE_50PC)

            # Draw this colour over the whole pixmap rect
            painter.drawRect(rect)

            # End the paint
            painter.end()

class Thumbnail(QWidget):
    # Class variables

    # Has this class been inintialised
    _initialised = False

    # Default loading icon image
    _defaultImagePath = 'ImageViewer/Resources/Loading Icon.png'

    # Default folder image
    _folderImagePath = 'ImageViewer/Resources/285658_blue_folder_icon.png'

    # QPixmap for default loading image
    _defaultImage: Optional[QPixmap] = None

    # ImageQt for folder image
    _folderImage: Optional[ImageQt] = None

    # Threads for loading the images
    _executor = ThreadPoolExecutor()

    # Default the thumbnail size to 0
    _thumbnailSize = 0

    # Signal emitted when this widget is clicked
    clicked = Signal()

    # Signal emitted when the image is fully loaded to set opacity back to 100%
    loaded = Signal()

    def __init__(self, imagePath: Path, parent: Optional[QWidget]=None):
        super().__init__(parent=parent)

        # Get labels for the image and filename and a layout to contain them
        self._thumbnailImage = PixmapLabel()
        self._thumbnailText = QLabel()
        self._layout = QVBoxLayout()

        # Set the minimum size of this widget
        self._thumbnailImage.setMinimumSize(self._thumbnailSize, self._thumbnailSize)

        # Set the layout margins to 0 so they don't add to the grid margins
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Add the image and text labels to the layout
        self._layout.addWidget(self._thumbnailImage, alignment=Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._thumbnailText, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Add the layout to this widget
        self.setLayout(self._layout)

        # Set the path of this image or folder
        self.ImagePath = imagePath

        # Set the current image to None
        self._currentImage: Optional[QPixmap] = None

        # The actual image
        self._qtImage: Optional[ImageQt] = None
        
        # Set the default image, withe loading or a folder
        self.SetDefaultImage()

        # Indicate whether this thumbnail is highlighted
        self._highlighted = False

    @classmethod
    def InitialiseDefaultImage(cls, thumbnailSize: int) -> None:
        # Only do this is the class has not yet been initialised
        if not cls._initialised:
            # Set the thumbnail size of all thumbnails
            cls.UpdateThumbnailSize(thumbnailSize)

            # Read in the default image, using Pillow as it is quicker, and convert to a QPixmap
            pilImage = Image.open(cls._defaultImagePath)
            qtImage = ImageQt(pilImage)
            defaultPixmap = QPixmap()
            defaultPixmap.convertFromImage(qtImage)

            # Scale the pixmap to the thumbnail size
            cls._defaultImage = defaultPixmap.scaled(cls._thumbnailSize, cls._thumbnailSize, aspectMode=Qt.AspectRatioMode.KeepAspectRatio)

            # Read in the folder image, using Pillow as it is quicker, and convert to a QPixmap
            pilImage = Image.open(cls._folderImagePath)
            cls._folderImage = ImageQt(pilImage)

            # Show that the class is now initialised
            cls._initialised = True

    @classmethod
    def UpdateThumbnailSize(cls, thumbnailSize: int) -> None:
        # Set the thumbnail size
        cls._thumbnailSize = thumbnailSize

    @property
    def highlighted(self) -> bool:
        # Return the current highlighted value
        return self._highlighted

    @highlighted.setter
    def highlighted(self, highlighted: bool) -> None:
        # Set the intenal highlighted value
        self._highlighted = highlighted

        # Ensure that the image knows it is to be highlighted (or not)
        self._thumbnailImage.highlighted = self._highlighted

        if self._highlighted:
            # Get the palette
            palette = self._thumbnailText.palette()

            # Store away the old colour
            self._oldTextColour = palette.color(QPalette.WindowText)

            # Set the colour of the palette
            palette.setColor(QPalette.WindowText, DODGER_BLUE)

            # Apply the palette to the label
            self._thumbnailText.setPalette(palette)
        else:
            # Get the palette
            palette = self._thumbnailText.palette()

            # Set the colour of the palette
            palette.setColor(QPalette.WindowText, self._oldTextColour)

            # Apply the palette to the label
            self._thumbnailText.setPalette(palette)

        # Force a repaint of this widget
        self.repaint()

    def _ShortenLabelText(self, text: str) -> str:
        # Return elided text version of the filename (stem only) that fits in the thumbnail width
        fontMetrics = QFontMetrics(self._thumbnailText.font())
        return fontMetrics.elidedText(text, Qt.TextElideMode.ElideMiddle, self._thumbnailSize)

    def SetDefaultImage(self) -> None:
        if self.ImagePath.is_file():
            if self._defaultImage:
                # if this is a file, set the default loading image for now
                self._thumbnailImage.setPixmap(self._defaultImage)

                # Ensure the pixmap is aligned in the centre
                self._thumbnailImage.setAlignment(Qt.AlignmentFlag.AlignCenter)

                # Get an opacity effect
                opacityEffect = QGraphicsOpacityEffect(self)

                # Set the opacity to 20%
                opacityEffect.setOpacity(0.2)

                # Add this effect to the widget
                self.setGraphicsEffect(opacityEffect)

                # Connect the signal for the image load complete message
                self.loaded.connect(self.ImageLoaded)

                # Initiate the load of the actual image in another thread
                self._LoadImage()
        else:
            if self._folderImage:
                # if this is a folder, set the folder image
                folderPixmap = QPixmap()
                folderPixmap.convertFromImage(self._folderImage)

                # Scale the pixmap to the thumbnail size
                currentFolderImage = folderPixmap.scaled(self._thumbnailSize, self._thumbnailSize, aspectMode=Qt.AspectRatioMode.KeepAspectRatio)

                # Set the folder image as the current pixmap
                self._thumbnailImage.setPixmap(currentFolderImage)

                # Ensure the pixmap is aligned in the centre of the label
                self._thumbnailImage.setAlignment(Qt.AlignmentFlag.AlignCenter)

                # Set the folder image as the current image
                self._currentImage = currentFolderImage

        # Set the filename text
        self._thumbnailText.setText(self._ShortenLabelText(self.ImagePath.stem))

    def _LoadImage(self):
        # Load the image in a new thread
        self._executor.submit(self._LoadImageInThread)

    def _LoadImageInThread(self) -> None:
        # Log that the image load has started
        logging.log(logging.DEBUG, f'Loading Image {self.ImagePath}')

        # Use Pillow to open the image and convert to a QPixmap
        pilImage = Image.open(self.ImagePath)

        # Log that PIL the image load has completed
        logging.log(logging.DEBUG, f'PIL Loaded {self.ImagePath}')

        # Convert the PIL image to a QImage
        self._qtImage = ImageQt(pilImage)

        # Log that the QImage conversion has completed
        logging.log(logging.DEBUG, f'Qt Converted {self.ImagePath}')

        # Resize the image
        self.ResizeImage()

    def ResizeImage(self) -> None:
        pixmap = QPixmap()

        # Set the minimum size of this widget
        self._thumbnailImage.setMinimumSize(self._thumbnailSize, self._thumbnailSize)

        # Log that the image has been loaded and we are ready to resize it to fit the label
        logging.log(logging.DEBUG, f'Resizing Image {self.ImagePath}')

        # Check the Qt Image has been set
        if self._qtImage:
            # Convert the Qt Image into a QPixmap
            pixmap.convertFromImage(self._qtImage)
        elif self._folderImage:
            # Convert the Qt Image into a QPixmap
            pixmap.convertFromImage(self._folderImage)

        # Scale the image to the thumbnail size
        self._currentImage = pixmap.scaled(self._thumbnailSize, self._thumbnailSize, aspectMode=Qt.AspectRatioMode.KeepAspectRatio)

        if self._currentImage:
            # Set the image to be the label pixmap
            self._thumbnailImage.setPixmap(self._currentImage)

            # Emit signal to indicate that the image has loaded and the opacity can be reset to 100%
            self.loaded.emit()

            # Log that the load is complete
            logging.log(logging.DEBUG, f'Loaded Image {self.ImagePath}')

        # Set the filename text
        self._thumbnailText.setText(self._ShortenLabelText(self.ImagePath.stem))

    def ImageLoaded(self) -> None:
        # The image has been loaded so we can now reset the opacity to 100%
        opacityEffect = QGraphicsOpacityEffect(self)
        opacityEffect.setOpacity(1.0)

        # Set the new graohics effect on the widget
        self.setGraphicsEffect(opacityEffect)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        super().mousePressEvent(a0)

        # Send the clicked message back to the main window
        self.clicked.emit()
