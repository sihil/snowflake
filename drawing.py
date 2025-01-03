import math

from plotter import Plotter, MAX_FEED_RATE_PEN_UP_MM_MIN, MAX_FEED_RATE_PEN_DOWN_MM_MIN


def draw_snowflake(plotter: Plotter, drawing: list[tuple[float, float]], order: int, mirror: bool, return_to: tuple[float, float]):
    if not drawing:
        return
    # we've already drawn the first one, so we can skip it
    # we need to draw a reflection of the current drawing
    # and then draw five more and their reflections

    # what are the angles...
    angle_delta: float = 360 / order
    angles = [angle_delta * i for i in range(order)]
    # do we guess from the drawing which is closest or always start with 0?

    # we need to rotate the drawing by 60 degrees
    for angle in angles[1:]:
        rotated_drawing = [rotate((0, 0), (x, y), math.radians(angle))
                           for x, y in drawing]
        draw(plotter, rotated_drawing)

    # now draw the mirror image
    if mirror:
        # mirror on the x-axis
        mirrored_drawing = [(-x, y) for x, y in drawing]
        for angle in angles:
            rotated_drawing = [rotate((0, 0), (x, y), math.radians(angle))
                               for x, y in mirrored_drawing]
            draw(plotter, rotated_drawing)

    # now return to the start
    plotter.move_to(*return_to, feed_rate=8000)


def rotate(origin: tuple[float, float], point: tuple[float, float], angle: float) -> tuple[float, float]:
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy


def draw(plotter: Plotter, drawing: list[tuple[float, float]]):
    plotter.pen_up()
    # move to the start of the line
    plotter.move_to(*drawing[0], feed_rate=MAX_FEED_RATE_PEN_UP_MM_MIN)
    plotter.pen_down()
    # now draw the rest of the shape with the pen down
    for x, y in drawing[1:]:
        plotter.move_to(x, y, feed_rate=MAX_FEED_RATE_PEN_DOWN_MM_MIN)
    plotter.pen_up()
