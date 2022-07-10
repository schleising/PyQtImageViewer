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
}

# Full list of supported extensions
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# Amount to skip video by
VIDEO_SKIP_AMOUNT = 5000

# Amount to adjust audio volume by
AUDIO_ADJUST_AMOUNT = 0.1

# Video UI margin
VIDEO_UI_MARGIN = 100

# Video position line size
VIDEO_POSITION_LINE_SIZE = 10

# Video UI Timeout
VIDEO_UI_TIMEOUT = 500
