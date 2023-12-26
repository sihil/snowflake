import logging

import drawcore_serial

logger = logging.getLogger(__name__)


# Coordinates are in mm
# +ve x is right
# +ve y is up

class Plotter:
    def __init__(self):
        self.serial_port = None

    def initialise(self):
        """
        Initialise the plotter.
        """
        logger.info("Initialising plotter...")
        self.serial_port = drawcore_serial.open_port()
        version = drawcore_serial.query_version(self.serial_port)
        logger.info(f"Connected to DrawCore version {version}")

    def home(self):
        # Home the plotter, this uses the micro-switches to find the top left corner
        drawcore_serial.command(self.serial_port, "$H\r")

    def centre(self):
        # Move to the centre of the plotter from the top left corner
        drawcore_serial.command(self.serial_port, "G1G91X147.463Y-210F5000\r\r")

    def set_origin(self):
        # Set the current position as the origin
        drawcore_serial.command(self.serial_port, "G92X0Y0\r\r")

    def move_to(self, x, y, feed_rate):
        # Move to the given location at the given feed rate
        logger.info("Moving to ({}, {}) at {} mm/min".format(x, y, feed_rate))
        drawcore_serial.command(self.serial_port, f"G1G90X{x:.3f}Y{y:.3f}F{feed_rate}\r")

    def pen_down(self):
        # Lower the pen
        drawcore_serial.command(self.serial_port, "G1G90Z5.0F5000\r")

    def pen_up(self):
        # Raise the pen
        drawcore_serial.command(self.serial_port, "G1G90Z0.5F5000\r")

    def sleep(self):
        drawcore_serial.command(self.serial_port, "$SLP\r")
