import logging
import threading
from enum import Enum

import drawcore_serial

logger = logging.getLogger(__name__)


MAX_FEED_RATE_PEN_UP_MM_MIN = 8000
MAX_FEED_RATE_PEN_DOWN_MM_MIN = 2000


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
        self._lock = threading.Lock()
        self.sleep_count = 0
        self.width_mm = None
        self.height_mm = None

    @property
    def exclusive(self):
        """
        A context manager that should be used to secure exclusive use of the plotter
        """
        return self._lock

    def execute_if_idle(self, f):
        """
        Execute the given function if the plotter is idle (i.e. not locked exclusively using the above context manager)
        """
        if self._lock.acquire(blocking=False):
            try:
                f()
            finally:
                self._lock.release()

    def query_configuration(self):
        """Query the plotter's configuration including device dimensions"""
        # Query the device settings
        response = drawcore_serial.query(self.serial_port, "$$\r")  # Get all settings

        # Parse the response to get width and height
        settings = {}
        for line in response.split('\n'):
            if '=' in line:
                setting_num, value = line.split('=')
                settings[setting_num] = float(value.strip())

        # Get width and height from settings $130 and $131
        if '$130' in settings:
            self.width_mm = settings['$130']
            logger.info(f"Device width: {self.width_mm}mm")

        if '$131' in settings:
            self.height_mm = settings['$131'] 
            logger.info(f"Device height: {self.height_mm}mm")

    def initialise(self):
        """
        Initialise the plotter.
        """
        logger.info("Initialising plotter...")
        self.serial_port = drawcore_serial.open_port()
        if self.serial_port is None:
            raise Exception("Failed to find plotter.")
        version = drawcore_serial.query_version(self.serial_port)
        logger.info(f"Connected to DrawCore version {version} on {self.serial_port.name}")
        
        # Query the device configuration
        self.query_configuration()

    def home(self):
        # Home the plotter, this uses the micro-switches to find the top left corner
        drawcore_serial.command(self.serial_port, "$H\r")
        self.reset_sleep()

    def centre(self):
        # Move to the centre of the plotter from the top left corner
        if self.width_mm is not None and self.height_mm is not None:
            # Use the actual device dimensions
            x_centre = self.width_mm / 2
            y_centre = -self.height_mm / 2  # Negative because Y is inverted
            drawcore_serial.command(self.serial_port, f"G1G91X{x_centre:.3f}Y{y_centre:.3f}F5000\r\r")
        else:
            # Fallback to hardcoded values
            drawcore_serial.command(self.serial_port, "G1G91X147.463Y-210F5000\r\r")
        self.reset_sleep()

    def set_origin(self):
        # Set the current position as the origin
        drawcore_serial.command(self.serial_port, "G92X0Y0\r\r")
        self.x = 0
        self.y = 0

    def is_at_origin(self) -> bool:
        return self.x == 0 and self.y == 0

    def move_to(self, x, y, feed_rate):
        # Move to the given location at the given feed rate
        drawcore_serial.command(self.serial_port, f"G1G90X{x:.3f}Y{y:.3f}F{feed_rate}\r")
        self.x = x
        self.y = y
        self.reset_sleep()

    def pen_down(self):
        # Lower the pen
        drawcore_serial.command(self.serial_port, "G1G90Z5.0F5000\r")
        self.z = 5.0
        self.reset_sleep()

    def pen_up(self):
        # Raise the pen
        drawcore_serial.command(self.serial_port, "G1G90Z0.5F5000\r")
        self.z = 0.5
        self.reset_sleep()

    def is_pen_down(self) -> bool:
        return self.pen_state() == PenState.DOWN

    def is_pen_up(self) -> bool:
        return self.pen_state() == PenState.UP

    def pen_state(self) -> PenState:
        return PenState.DOWN if self.z > 1.0 else PenState.UP

    def reset_sleep(self):
        self.sleep_count = 0

    def check_sleep(self):
        if self.sleep_count < 50:
            self.sleep_count += 1
        elif self.is_pen_up() and self.sleep_count == 50:
            with self.exclusive:
                self.sleep()
            logger.info("Plotter sleeping")
            self.sleep_count += 1

    def sleep(self):
        drawcore_serial.command(self.serial_port, "$SLP\r")
