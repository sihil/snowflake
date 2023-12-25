import copy
import logging
import threading
import inputs

logger = logging.getLogger(__name__)

# Analogues controls
# ABS_X = main stick left/right (left = 0, centre = 512, right = 1023)
# ABS_Y = main stick up/down (top = 0, centre = 512, bottom = 1023)
# ABS_RZ = main stick rotate (anti-clockwise = 0, rest = 128, clockwise = 255)
# ABS_Z = throttle lever (forwards = 0, rest = 128, back = 255)
# ABS_THROTTLE = left/right button behind ABS_Z lever (left = 0, rest = 128, right = 255)

# Digital controls
# stick
# BTN_TRIGGER = 1 main trigger
# BTN_THUMB = 2 thumb button
# BTN_THUMB2 = 3 right hand button
# BTN_TOP = 4 top right button

# hat (Absolute)
# ABS_HAT0X = hat left/right (left = -1, rest = 0, right = 1)
# ABS_HAT0Y = hat up/down (top = -1, rest = 0, bottom = 1)

# throttle
# BTN_TOP2 = 5 top button on throttle front
# BTN_PINKIE = 6 button on throttle front
# BTN_BASE = 7 button on throttle front
# BTN_BASE2 = 8 button on throttle front
# BTN_BASE3 = 9 button on throttle back
# BTN_BASE4 = 10 button on throttle back

# base
# BTN_BASE5 = SE button
# BTN_BASE6 = ST button

# Create a state object to store joystick data, assuming we start at rest


class Joystick:

    def __init__(self):
        self._joystick_state = {
            "ABS_X": 512,
            "ABS_Y": 512,
            "ABS_Z": 128,
        }
        self.lock = threading.Lock()

    def latest_state(self):
        with self.lock:
            return copy.deepcopy(self._joystick_state)

    def read_event_loop(self, exit_event):
        # Get the list of available devices
        devices = inputs.devices.gamepads

        # Check if there is at least one joystick/gamepad connected
        if not devices:
            logger.error("No joystick found.")
            return

        # Get the first joystick/gamepad
        joystick = inputs.devices.gamepads[0]

        event_feed = (event
                      for events in joystick
                      for event in events
                      if event.ev_type in {'Absolute', 'Key'})

        logger.info(f"Joystick: Initialising event loop for {joystick.name}")

        try:
            for event in event_feed:
                if exit_event.is_set():
                    logger.info("Exiting joystick input.")
                    break
                with self.lock:
                    self._joystick_state[event.code] = event.state

        except KeyboardInterrupt:
            pass
        finally:
            logger.info("Closing joystick input.")
