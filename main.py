import sys

from PyQt6.QtWidgets import QApplication

from ImageViewer.MainWindow import MainWindow

if __name__ == '__main__':
    # The main application
    app = QApplication(sys.argv)

    # Check for command line arguments
    if len(sys.argv) > 1:
        # Send the argument to the Main Window
        label = sys.argv[1]
    else:
        # Indicate that there are no arguments
        label = 'No Args'

    # Create the main window
    window = MainWindow(label)

    # Get the screen size
    windowRect = app.primaryScreen().availableGeometry()

    # Set the window position and size
    # window.setGeometry(0, 0, windowRect.width(), windowRect.height())
    window.setGeometry(300, 100, 1024, 768)

    # Call Set Labels to get the thumbnails
    window.SetLabels()

    # Show the window
    # window.showFullScreen()
    window.show()

    # Run the application loop
    sys.exit(app.exec())
