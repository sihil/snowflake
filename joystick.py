import copy
import logging
import threading
import inputs

logger = logging.getLogger(__name__)


class Joystick:

    def __init__(self):
        # the rest state for my joystick
        self._joystick_state = {
            "ABS_X": 512,  # main stick left/right (left = 0, centre = 512, right = 1023)
            "ABS_Y": 512,  # main stick up/down (top = 0, centre = 512, bottom = 1023)
            "ABS_Z": 128,  # throttle lever (forwards = 0, rest = 128, back = 255)
            "ABS_RZ": 128,  # main stick rotate (anti-clockwise = 0, rest = 128, clockwise = 255)
            "ABS_THROTTLE": 128,  # left/right button behind ABS_Z lever (left = 0, rest = 128, right = 255)
            "BTN_TRIGGER": 0,  # 1 main trigger
            "BTN_THUMB": 0,  # 2 thumb button
            "BTN_THUMB2": 0,  # 3 right hand button
            "BTN_TOP": 0,  # 4 top right button
            "ABS_HAT0X": 0,  # hat left/right (left = -1, rest = 0, right = 1)
            "ABS_HAT0Y": 0,  # hat up/down (top = -1, rest = 0, bottom = 1)
            "BTN_TOP2": 0,  # 5 top button on throttle front
            "BTN_PINKIE": 0,  # 6 button on throttle front
            "BTN_BASE": 0,  # 7 button on throttle front
            "BTN_BASE2": 0,  # 8 button on throttle front
            "BTN_BASE3": 0,  # 9 button on throttle back
            "BTN_BASE4": 0,  # 10 button on throttle back
            "BTN_BASE5": 0,  # SE button
            "BTN_BASE6": 0,  # ST button
        }
        self._button_callbacks = {}
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
                callbacks = []
                with self.lock:
                    # line up any callbacks for button presses or releases
                    if (event.code, event.state) in self._button_callbacks:
                        # only add the callback if the state has changed to the value we're interested in
                        if event.state != self._joystick_state[event.code]:
                            callbacks.append(self._button_callbacks[(event.code, event.state)])
                    self._joystick_state[event.code] = event.state
                # run all the callbacks outside the lock
                for callback in callbacks:
                    callback()

        except KeyboardInterrupt:
            pass
        finally:
            logger.info("Closing joystick input.")

    def register_button_callback(self, button, value, callback):
        """
        Register a callback for a button press or release event.

        :param button: The button to register the callback for.
        :param value: The value of the button to register the callback for (0 or 1).
        :param callback: The callback function to call when the button is pressed or released.
        """
        logger.info("Registering callback for button {} with value {}".format(button, value))
        self._button_callbacks[(button, value)] = callback
