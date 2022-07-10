from PySide6.QtGui import QColor

ZOOM_SCALE_FACTOR = 1.05

START_X = 300
START_Y = 100
START_WIDTH = 1024
START_HEIGHT = 768
MIN_WIDTH = START_WIDTH

DODGER_BLUE = QColor(30, 144, 255, 255)
DODGER_BLUE_50PC = QColor(30, 144, 255, 128)

# List of supported image extensions
IMAGE_EXTENSIONS = {
    'Graphics Interchange Format': '.gif',
    'JPG Image': '.jpg',
    'JPEG Image': '.jpeg',
    'Portable Network Graphic': '.png',
    'WEBP': '.webp',
}

# List of supported video extensions
VIDEO_EXTENSIONS = {
    'MP4': '.mp4',
    'MKV': '.mkv',
}

# Full list of supported extensions
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
