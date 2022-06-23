import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ImageViewer.MainWindow import MainWindow

if __name__ == '__main__':
    # The main application
    app = QApplication(sys.argv)

    # Set the application to use OpenGL ES, seems to prevent a black screen when going to full screen
    # app.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

    # Check for command line arguments
    if len(sys.argv) > 1:
        # Send the argument to the Main Window
        args = sys.argv[1]
    else:
        # Indicate that there are no arguments
        args = None

    # Create the main window
    window = MainWindow(args)

    # Run the application loop
    sys.exit(app.exec())

#TODO: Handle command line arguments
#TODO: Better image transitions
#TODO: Crop images
#TODO: Implement filters
#TODO: Dim loading icons
#TODO: Keyboard filebrowser navigation
#TODO: ESC to quit, Up to go back to filebrowser
#TODO: Implement menu
#TODO: Implement help
#TODO: More text as thumbnails get bigger
#TODO: Set minimum window size
