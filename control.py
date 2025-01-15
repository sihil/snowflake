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

# Time to sleep between iterations (in seconds)
LOOP_SLEEP_TIME = 0.1  # 100ms

# Safety margin from the edge of the plotter's working area (in mm)
MARGIN_MM = 30.0

def calculate_distance(x, y):
    """Calculate distance from center (0,0) with pygame coordinates"""
    return math.sqrt(x * x + y * y)  # Returns value 0.0 to 1.0 for unit circle

def calculate_components(x, y, distance):
    """Calculate movement components with pygame coordinates"""
    # Normalize the vector to get direction
    length = math.sqrt(x * x + y * y)
    if length == 0:
        return 0, 0
    
    norm_x = x / length
    norm_y = y / length
    
    # Scale by the desired distance
    return norm_x * distance, norm_y * distance

def map_distance_to_feedrate(distance, max_feedrate):
    """Map joystick distance (0.0 to 1.0) to feedrate"""
    return int(distance * max_feedrate)

def calculate_max_radius(plotter_instance):
    """Calculate the maximum safe drawing radius based on plotter dimensions"""
    if plotter_instance.width_mm is not None and plotter_instance.height_mm is not None:
        # Use the actual device dimensions, accounting for the fact we're drawing from the center
        max_radius = min(plotter_instance.width_mm / 2, plotter_instance.height_mm / 2) - MARGIN_MM
        logger.info(f"Using device dimensions for max radius with margin of {MARGIN_MM}mm: {max_radius}mm")
        return max_radius
    else:
        # Fallback to hardcoded value
        fallback_radius = 120.0
        logger.warning(f"No device dimensions available, using fallback radius: {fallback_radius}mm")
        return fallback_radius

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
        dead_zone = 0.04  # 4% of full range for dead zone
        max_radius = calculate_max_radius(plotter_instance)

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
            sleep_time_start = time.time()
            joystick_state = joystick_instance.latest_state()
            
            # Read joystick input (in -1.0 to 1.0 range)
            joystick_x = joystick_state["ABS_X"]
            joystick_y = joystick_state["ABS_Y"]
            joystick_z = joystick_state["ABS_Z"]

            # Calculate distance from neutral position (0.0 to 1.0)
            distance = calculate_distance(joystick_x, joystick_y)

            if joystick_z > 0.1 and plotter_instance.is_pen_up():
                with plotter_instance.exclusive:
                    plotter_instance.pen_down()
                    current_drawing.append((plotter_instance.x, plotter_instance.y))
            elif joystick_z <= 0.0 and plotter_instance.is_pen_down():
                with plotter_instance.exclusive:
                    plotter_instance.pen_up()
                    draw_snowflake(plotter=plotter_instance,
                                drawing=current_drawing,
                                order=order,
                                mirror=mirror,
                                return_to=(plotter_instance.x, plotter_instance.y))
                    current_drawing = []

            # Handle movement
            if distance < dead_zone:
                feed_rate = 0
                plotter_instance.check_sleep()
            else:
                # Scale the feed rate by how far the joystick is pushed
                feed_rate = map_distance_to_feedrate(distance, MAX_FEED_RATE_PEN_DOWN_MM_MIN)
                
                # Calculate movement for exactly one sleep period
                movement_scale = feed_rate * (LOOP_SLEEP_TIME / 60)  # Convert from mm/min to mm/sleep_time
                x_portion_of_distance, y_portion_of_distance = calculate_components(
                    joystick_y, joystick_x, movement_scale
                )

                target_x = plotter_instance.x + x_portion_of_distance
                target_y = plotter_instance.y + y_portion_of_distance
                distance_from_origin = math.sqrt(target_x ** 2 + target_y ** 2)

                if distance_from_origin <= max_radius:
                    with plotter_instance.exclusive:
                        sleep_time_start = time.time()
                        plotter_instance.move_to(x=target_x, y=target_y, feed_rate=feed_rate)
                        command_taken_time = time.time() - sleep_time_start
                        if command_taken_time > 0.01:
                            logger.info(f"!!!! Command took {command_taken_time} seconds !!!!")
                    if plotter_instance.is_pen_down():
                        current_drawing.append((plotter_instance.x, plotter_instance.y))

            # Small sleep to prevent busy waiting
            try:
                remaining_sleep_time = LOOP_SLEEP_TIME - (time.time() - sleep_time_start)
                if remaining_sleep_time > 0:
                    time.sleep(remaining_sleep_time)
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
            plotter_instance.sleep()
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

