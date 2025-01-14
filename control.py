import logging
import math
import threading
import time
import signal

import joystick
import plotter
from plotter import MAX_FEED_RATE_PEN_DOWN_MM_MIN
from drawing import draw_snowflake

logger = logging.getLogger(__name__)

# Set up logging to the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s [%(levelname)s] %(message)s')

def calculate_distance(x, y, max_distance):
    center_x, center_y = 512, 512
    distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    capped_distance = min(distance, max_distance)
    return capped_distance

def calculate_components(x, y, distance):
    center_x, center_y = 512, 512
    angle = math.atan2(y - center_y, x - center_x)
    x_portion_of_distance = math.cos(angle) * distance
    y_portion_of_distance = math.sin(angle) * distance
    return x_portion_of_distance, y_portion_of_distance

def map_distance_to_feedrate(distance, max_distance, max_feedrate):
    normalized_distance = min(distance / max_distance, 1.0)
    feedrate = normalized_distance * max_feedrate
    return int(feedrate)

def main():
    # Create an event to signal the thread to exit
    exit_event = threading.Event()
    joystick_instance = joystick.Joystick()

    # Create a thread for joystick reading
    joystick_thread = threading.Thread(target=joystick_instance.read_event_loop, args=(exit_event,))

    try:
        # Start the thread
        joystick_thread.start()

        def signal_handler(signum, frame):
            logger.info("Received signal to terminate")
            exit_event.set()
            
        # Register signal handler
        signal.signal(signal.SIGINT, signal_handler)

        # Initialize plotter
        plotter_instance = plotter.Plotter()
        plotter_instance.initialise()

        # Initialize state variables
        current_drawing = []
        order = 6
        mirror = True
        max_distance = 512

        def home_and_origin():
            def _do():
                logger.info("Homing and setting origin")
                plotter_instance.home()
                plotter_instance.centre()
                plotter_instance.set_origin()
            plotter_instance.execute_if_idle(_do)

        def log_state():
            mirror_state = "with mirroring" if mirror else "without mirroring"
            logger.info(f"Order {order} {mirror_state}")

        def change_order(delta):
            nonlocal order
            order += delta
            if order < 1:
                order = 1
            log_state()

        def change_mirror(new_mirror: bool):
            nonlocal mirror
            if mirror != new_mirror:
                mirror = new_mirror
                log_state()

        def move_to_origin():
            def _do():
                logger.info("Moving to origin")
                if not plotter_instance.is_at_origin():
                    plotter_instance.move_to(0, 0, 8000)
            plotter_instance.execute_if_idle(_do)

        # Register callbacks
        joystick_instance.register_button_callback(button="ABS_HAT0Y", value=-1, callback=lambda: change_order(1))
        joystick_instance.register_button_callback(button="ABS_HAT0Y", value=1, callback=lambda: change_order(-1))
        joystick_instance.register_button_callback(button="ABS_HAT0X", value=-1, callback=lambda: change_mirror(False))
        joystick_instance.register_button_callback(button="ABS_HAT0X", value=1, callback=lambda: change_mirror(True))
        joystick_instance.register_button_callback(button="BTN_BASE5", value=1, callback=move_to_origin)
        joystick_instance.register_button_callback(button="BTN_BASE6", value=1, callback=home_and_origin)

        # Main control loop
        while not exit_event.is_set():
            joystick_state = joystick_instance.latest_state()

            # Read joystick input
            joystick_x = joystick_state["ABS_X"]
            joystick_y = joystick_state["ABS_Y"]
            joystick_z = joystick_state["ABS_Z"]

            # Calculate distance from neutral position
            distance = calculate_distance(joystick_y, joystick_x, max_distance=512)
            component_x, component_y = joystick_y - 512, joystick_x - 512

            # Handle pen state
            if joystick_z > 140 and plotter_instance.is_pen_up():
                with plotter_instance.exclusive:
                    plotter_instance.pen_down()
                    current_drawing.append((plotter_instance.x, plotter_instance.y))
            elif joystick_z <= 128 and plotter_instance.is_pen_down():
                with plotter_instance.exclusive:
                    plotter_instance.pen_up()
                    draw_snowflake(plotter=plotter_instance,
                                 drawing=current_drawing,
                                 order=order,
                                 mirror=mirror,
                                 return_to=(plotter_instance.x, plotter_instance.y))
                    current_drawing = []

            # Handle movement
            if distance < 20:
                feed_rate = 0
                plotter_instance.check_sleep()
            else:
                feed_rate = map_distance_to_feedrate(distance, max_distance, MAX_FEED_RATE_PEN_DOWN_MM_MIN)
                x_portion_of_distance, y_portion_of_distance = calculate_components(
                    joystick_y, joystick_x, feed_rate * (1/600)
                )

                target_x = plotter_instance.x + x_portion_of_distance
                target_y = plotter_instance.y + y_portion_of_distance
                distance_from_origin = math.sqrt(target_x ** 2 + target_y ** 2)

                if distance_from_origin <= 148:
                    with plotter_instance.exclusive:
                        plotter_instance.move_to(x=target_x, y=target_y, feed_rate=feed_rate)
                    if plotter_instance.is_pen_down():
                        current_drawing.append((plotter_instance.x, plotter_instance.y))

            try:
                time.sleep(0.1)
            except InterruptedError:
                break

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise

    finally:
        # Cleanup
        exit_event.set()
        
        # Ensure pen is up
        try:
            if plotter_instance.is_pen_down():
                plotter_instance.pen_up()
        except:
            pass
        
        # Wait for the joystick thread to finish
        logger.info("Waiting for joystick thread to terminate...")
        joystick_thread.join(timeout=2.0)
        
        if joystick_thread.is_alive():
            logger.warning("Joystick thread did not terminate cleanly")
        
        logger.info("Program terminated.")

if __name__ == "__main__":
    main()

