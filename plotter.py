import logging
from enum import Enum

import drawcore_serial

logger = logging.getLogger(__name__)


class PenState(Enum):
    UP = 0
    DOWN = 1


# Coordinates are in mm
# +ve x is right
# +ve y is up

class Plotter:
    def __init__(self):
        self.serial_port = None
        self.x = 0
        self.y = 0
        self.z = 0

    def initialise(self):
        """
        Initialise the plotter.
        """
        logger.info("Initialising plotter...")
        self.serial_port = drawcore_serial.open_port()
        if self.serial_port is None:
            raise Exception("Failed to find plotter.")
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
        self.x = 0
        self.y = 0

    def is_at_origin(self) -> bool:
        return self.x == 0 and self.y == 0

    def move_to(self, x, y, feed_rate):
        # Move to the given location at the given feed rate
        logger.info("Moving to ({}, {}) at {} mm/min".format(x, y, feed_rate))
        drawcore_serial.command(self.serial_port, f"G1G90X{x:.3f}Y{y:.3f}F{feed_rate}\r")
        self.x = x
        self.y = y

    def pen_down(self):
        # Lower the pen
        drawcore_serial.command(self.serial_port, "G1G90Z5.0F5000\r")
        self.z = 5.0

    def pen_up(self):
        # Raise the pen
        drawcore_serial.command(self.serial_port, "G1G90Z0.5F5000\r")
        self.z = 0.5

    def is_pen_down(self) -> bool:
        return self.pen_state() == PenState.DOWN

    def is_pen_up(self) -> bool:
        return self.pen_state() == PenState.UP

    def pen_state(self) -> PenState:
        return PenState.DOWN if self.z > 1.0 else PenState.UP

    def sleep(self):
        drawcore_serial.command(self.serial_port, "$SLP\r")
