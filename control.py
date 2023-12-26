import logging
import math
import threading
import time
from enum import Enum

import joystick
import plotter
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


max_feedrate = 2000  # note that this is mm/min
max_distance = 512  # this is the maximum distance from the center of the joystick


class PenState(Enum):
    UP = 0
    DOWN = 1


plotter = plotter.Plotter()
plotter.initialise()
plotter.home()
plotter.centre()
plotter.set_origin()
current_x = 0
current_y = 0

plotter.pen_up()
current_pen_state = PenState.UP

current_drawing = []
sleep_count = 0

# Your main program can continue to run concurrently with the joystick reading thread
try:
    while True:
        # Your main program logic goes here
        joystick_state = joystick.latest_state()

        # Read joystick input
        joystick_x = joystick_state["ABS_X"]
        joystick_y = joystick_state["ABS_Y"]
        joystick_z = joystick_state["ABS_Z"]

        se_button = joystick_state.get("BTN_BASE5", 0)

        if current_pen_state == PenState.UP and se_button == 1 and (current_x != 0 or current_y != 0):
            # reset back to centre
            plotter.move_to(0, 0, 8000)
            current_x = 0
            current_y = 0
            continue

        # Calculate distance from neutral/rest position
        distance = calculate_distance(joystick_y, joystick_x, max_distance=512)
        component_x, component_y = joystick_y - 512, joystick_x - 512

        # Set the pen state
        if joystick_z > 140 and current_pen_state == PenState.UP:
            plotter.pen_down()
            current_pen_state = PenState.DOWN
            current_drawing.append((current_x, current_y))
        elif joystick_z <= 128 and current_pen_state == PenState.DOWN:
            plotter.pen_up()
            current_pen_state = PenState.UP
            draw_snowflake(plotter=plotter, drawing=current_drawing, return_to=(current_x, current_y))
            current_drawing = []

        # Apply a dead zone (e.g., 20 units) around the neutral position
        if distance < 20:
            feed_rate = 0
            if sleep_count < 50:
                sleep_count += 1
            elif current_pen_state != PenState.DOWN and sleep_count == 50:
                plotter.sleep()
                logger.info("Plotter sleeping")
                sleep_count += 1
        else:
            sleep_count = 0
            # Map joystick values to speed
            feed_rate = map_distance_to_feedrate(distance, max_distance, max_feedrate)

            # Calculate the components of the movement
            x_portion_of_distance, y_portion_of_distance = calculate_components(joystick_y, joystick_x, feed_rate * (1/600))

            # Calculate where we want the head to move to in a tenth of a second (or a 600th of a minute)
            target_x = current_x + x_portion_of_distance
            target_y = current_y + y_portion_of_distance

            # Calculate distance from origin
            distance_from_origin = math.sqrt(target_x ** 2 + target_y ** 2)

            # Move the head to the target location if it's safe to do so
            if distance_from_origin <= 148:
                plotter.move_to(x=target_x, y=target_y, feed_rate=feed_rate)
                # update where we think we are
                current_x = target_x
                current_y = target_y
                # add the current location to the drawing if we're drawing
                if current_pen_state == PenState.DOWN:
                    current_drawing.append((current_x, current_y))

        time.sleep(0.1)  # Add some main program logic or just sleep to keep the program running

except KeyboardInterrupt:
    logger.info("Exiting main program.")

finally:
    # Set the event to signal the thread to exit
    exit_event.set()

    # Wait for the joystick thread to finish
    joystick_thread.join()

    logger.info("Main program and joystick thread terminated.")

