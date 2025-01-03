import logging
import math
import threading
import time

import joystick
import plotter
from plotter import MAX_FEED_RATE_PEN_DOWN_MM_MIN
from drawing import draw_snowflake

logger = logging.getLogger(__name__)

# Set up logging to the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s [%(levelname)s] %(message)s')

# Create an event to signal the thread to exit
exit_event = threading.Event()
joystick = joystick.Joystick()

# Create a thread for joystick reading
joystick_thread = threading.Thread(target=joystick.read_event_loop, args=(exit_event,))

# Start the thread
joystick_thread.start()


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
    # Scale the distance to the range [0, 1]
    normalized_distance = min(distance / max_distance, 1.0)

    # Map the normalized distance to the range [0, max_feedrate]
    feedrate = normalized_distance * max_feedrate

    return int(feedrate)  # Convert to an integer if needed


max_distance = 512  # this is the maximum distance from the center of the joystick


plotter = plotter.Plotter()
plotter.initialise()


def home_and_origin():
    def _do():
        logger.info("Homing and setting origin")
        plotter.home()
        plotter.centre()
        plotter.set_origin()

    plotter.execute_if_idle(_do)


current_drawing = []

order = 6
mirror = True


def log_state():
    mirror_state = "with mirroring" if mirror else "without mirroring"
    logger.info(f"Order {order} {mirror_state}")


def change_order(delta):
    global order
    order += delta
    if order < 1:
        order = 1
    log_state()


def change_mirror(new_mirror: bool):
    global mirror
    if mirror != new_mirror:
        mirror = new_mirror
        log_state()


def move_to_origin():
    def _do():
        logger.info("Moving to origin")
        if not plotter.is_at_origin():
            plotter.move_to(0, 0, 8000)

    plotter.execute_if_idle(_do)


# register all the behaviour modifications
joystick.register_button_callback(button="ABS_HAT0Y", value=-1, callback=lambda: change_order(1))
joystick.register_button_callback(button="ABS_HAT0Y", value=1, callback=lambda: change_order(-1))
joystick.register_button_callback(button="ABS_HAT0X", value=-1, callback=lambda: change_mirror(False))
joystick.register_button_callback(button="ABS_HAT0X", value=1, callback=lambda: change_mirror(True))

joystick.register_button_callback(button="BTN_BASE5", value=1, callback=move_to_origin)
joystick.register_button_callback(button="BTN_BASE6", value=1, callback=home_and_origin)

try:
    while True:
        joystick_state = joystick.latest_state()

        # Read joystick input
        joystick_x = joystick_state["ABS_X"]
        joystick_y = joystick_state["ABS_Y"]
        joystick_z = joystick_state["ABS_Z"]

        # Calculate distance from neutral/rest position; note that we map the joysticks x-axis to the
        # y-axis of the plotter and vice versa
        distance = calculate_distance(joystick_y, joystick_x, max_distance=512)
        component_x, component_y = joystick_y - 512, joystick_x - 512

        # Set the pen state
        if joystick_z > 140 and plotter.is_pen_up():
            with plotter.exclusive:
                plotter.pen_down()
                current_drawing.append((plotter.x, plotter.y))
        elif joystick_z <= 128 and plotter.is_pen_down():
            with plotter.exclusive:
                plotter.pen_up()
                draw_snowflake(plotter=plotter,
                               drawing=current_drawing,
                               order=order,
                               mirror=mirror,
                               return_to=(plotter.x, plotter.y))
                current_drawing = []

        # Apply a dead zone (e.g., 20 units) around the neutral position
        if distance < 20:
            feed_rate = 0
            plotter.check_sleep()

        else:
            # Map joystick values to speed
            feed_rate = map_distance_to_feedrate(distance, max_distance, MAX_FEED_RATE_PEN_DOWN_MM_MIN)

            # Calculate the components of the movement
            x_portion_of_distance, y_portion_of_distance = calculate_components(
                joystick_y, joystick_x, feed_rate * (1/600)
            )

            # Calculate where we want the head to move to in a tenth of a second (or a 600th of a minute)
            target_x = plotter.x + x_portion_of_distance
            target_y = plotter.y + y_portion_of_distance

            # Calculate distance from origin
            distance_from_origin = math.sqrt(target_x ** 2 + target_y ** 2)

            # Move the head to the target location if it's safe to do so
            if distance_from_origin <= 148:
                with plotter.exclusive:
                    plotter.move_to(x=target_x, y=target_y, feed_rate=feed_rate)
                # add the current location to the drawing if we're drawing
                if plotter.is_pen_down():
                    current_drawing.append((plotter.x, plotter.y))

        time.sleep(0.1)  # Add some main program logic or just sleep to keep the program running

except KeyboardInterrupt:
    logger.info("Exiting main program.")

finally:
    # Set the event to signal the thread to exit
    exit_event.set()

    # Wait for the joystick thread to finish
    joystick_thread.join()

    logger.info("Main program and joystick thread terminated.")

