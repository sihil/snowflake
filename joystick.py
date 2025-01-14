import copy
import logging
import threading
import pygame

logger = logging.getLogger(__name__)


class Joystick:
    def __init__(self):
        # Initialize pygame and joystick subsystem
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            logger.error("No joystick found.")
            raise RuntimeError("No joystick found")
            
        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()
        
        logger.info(f"Initialized joystick: {self._joystick.get_name()}")
        
        # the rest state for my joystick
        self._joystick_state = {
            "ABS_X": 0.0,  # main stick left/right (left = -1.0, centre = 0.0, right = 1.0)
            "ABS_Y": 0.0,  # main stick up/down (top = -1.0, centre = 0.0, bottom = 1.0)
            "ABS_Z": 0.0,  # throttle lever (forwards = -1.0, rest = 0.0, back = 1.0)
            "ABS_RZ": 0.0,  # main stick rotate (anti-clockwise = -1.0, rest = 0.0, clockwise = 1.0)
            "ABS_THROTTLE": 0.0,  # left/right button behind ABS_Z lever (left = -1.0, rest = 0.0, right = 1.0)
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
        self._exit_event = None

    def latest_state(self):
        with self.lock:
            return copy.deepcopy(self._joystick_state)

    def check_events(self):
        """Non-blocking event check"""
        for event in pygame.event.get():
            callbacks = []
            
            with self.lock:
                if event.type == pygame.JOYAXISMOTION:
                    if event.axis == 0:  # X axis
                        self._joystick_state["ABS_X"] = event.value
                    elif event.axis == 1:  # Y axis
                        self._joystick_state["ABS_Y"] = event.value
                    elif event.axis == 2:  # Throttle (Z)
                        self._joystick_state["ABS_Z"] = event.value
                    elif event.axis == 3:  # Rotation (RZ)
                        self._joystick_state["ABS_RZ"] = event.value
                    elif event.axis == 4:  # Throttle lever
                        self._joystick_state["ABS_THROTTLE"] = event.value
                
                elif event.type == pygame.JOYHATMOTION:
                    if event.hat == 0:  # Assuming first (and only) hat
                        x, y = event.value
                        old_x = self._joystick_state["ABS_HAT0X"]
                        old_y = self._joystick_state["ABS_HAT0Y"]
                        self._joystick_state["ABS_HAT0X"] = x
                        self._joystick_state["ABS_HAT0Y"] = -y  # Pygame uses opposite Y convention
                        
                        # Check for hat callbacks
                        if x != old_x and (("ABS_HAT0X", x) in self._button_callbacks):
                            callbacks.append(self._button_callbacks[("ABS_HAT0X", x)])
                        if -y != old_y and (("ABS_HAT0Y", -y) in self._button_callbacks):
                            callbacks.append(self._button_callbacks[("ABS_HAT0Y", -y)])
                
                elif event.type == pygame.JOYBUTTONDOWN:
                    button_mapping = {
                        0: "BTN_TRIGGER",
                        1: "BTN_THUMB",
                        2: "BTN_THUMB2",
                        3: "BTN_TOP",
                        4: "BTN_TOP2",
                        5: "BTN_PINKIE",
                        6: "BTN_BASE",
                        7: "BTN_BASE2",
                        8: "BTN_BASE3",
                        9: "BTN_BASE4",
                        10: "BTN_BASE5",
                        11: "BTN_BASE6"
                    }
                    if event.button in button_mapping:
                        button_name = button_mapping[event.button]
                        self._joystick_state[button_name] = 1
                        if (button_name, 1) in self._button_callbacks:
                            callbacks.append(self._button_callbacks[(button_name, 1)])
                
                elif event.type == pygame.JOYBUTTONUP:
                    button_mapping = {
                        0: "BTN_TRIGGER",
                        1: "BTN_THUMB",
                        2: "BTN_THUMB2",
                        3: "BTN_TOP",
                        4: "BTN_TOP2",
                        5: "BTN_PINKIE",
                        6: "BTN_BASE",
                        7: "BTN_BASE2",
                        8: "BTN_BASE3",
                        9: "BTN_BASE4",
                        10: "BTN_BASE5",
                        11: "BTN_BASE6"
                    }
                    if event.button in button_mapping:
                        button_name = button_mapping[event.button]
                        self._joystick_state[button_name] = 0
                        if (button_name, 0) in self._button_callbacks:
                            callbacks.append(self._button_callbacks[(button_name, 0)])

            # Execute callbacks outside the lock
            for callback in callbacks:
                callback()

    def read_event_loop(self, exit_event):
        """
        Main event loop that continuously checks for joystick events
        """
        self._exit_event = exit_event
        logger.info("Starting joystick event loop")
        
        try:
            while not exit_event.is_set():
                self.check_events()
                pygame.time.wait(10)  # Small sleep to prevent busy waiting
        
        except Exception as e:
            logger.error(f"Error in joystick event loop: {e}")
            raise
        finally:
            logger.info("Closing joystick input.")
            self._joystick.quit()
            pygame.quit()

    def register_button_callback(self, button, value, callback):
        """
        Register a callback for a button press or release event.

        :param button: The button to register the callback for.
        :param value: The value of the button to register the callback for (0 or 1).
        :param callback: The callback function to call when the button is pressed or released.
        """
        logger.info("Registering callback for button {} with value {}".format(button, value))
        self._button_callbacks[(button, value)] = callback
