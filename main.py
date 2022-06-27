from datetime import datetime
from pathlib import Path
import sys
import logging
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFileOpenEvent
from PySide6.QtCore import QEvent, SignalInstance

from ImageViewer.MainWindow import MainWindow

class PyQtImageViewer(QApplication):
    def __init__(self, argv: list[str]):
        # Create a signal instance for the file opened event (actual Signal in MainWindow)
        self.fileOpenedSignal: Optional[SignalInstance] = None
        super().__init__(argv)

    def event(self, event: QEvent) -> bool:
        # Log each event
        logging.log(logging.DEBUG, f'{event.type()}')

        # If this is a file open event, send the file path to the Main Window
        if isinstance(event, QFileOpenEvent):
            # Log that we have received a file open event along with the filename
            logging.log(logging.DEBUG, f'**** Application Received QFileOpenEvent: {event.file()}')

            # Ensure the signal exists
            if self.fileOpenedSignal is not None:
                # Log that we are emitting the signal (this will fail if the data type isn't set properly on the signal)
                logging.log(logging.DEBUG, 'App: Signal Emitting')

                # Emit the signal with the file path
                self.fileOpenedSignal.emit(Path(event.file()))

                # Log that the signal was emitted successfully
                logging.log(logging.DEBUG, 'App: Signal Emitted')
            else:
                # Log that we couldn't emit the signal
                logging.log(logging.DEBUG, 'App: Signal Not Emitted')

        return super().event(event)

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(
        filename=Path.home() / f'.PyQtImageViewer {datetime.now().strftime("%y-%m-%d %H.%M.%S")}.txt',
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )

    # Log that the application has started
    logging.log(logging.INFO, f'Application started: {sys.argv}')

    # The main application
    app = PyQtImageViewer(sys.argv)

    # Create the main window
    window = MainWindow()

    # Get the file opened signal
    app.fileOpenedSignal = window.fileOpenedSignal

    # Run the application loop
    exitCode = app.exec()

    # Log that we are exiting the application
    logging.log(logging.INFO, f'Exiting application with code: {exitCode}')

    # Exit the application
    sys.exit(exitCode)

#TODO: Better image transitions
#TODO: Crop images
#TODO: Implement filters
#TODO: Keyboard filebrowser navigation
#TODO: Implement menu
#TODO: Implement help
#TODO: More text as thumbnails get bigger
#TODO: Set minimum window size
