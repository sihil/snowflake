The snowflake machine
=====================

This is really more like a digital spirograph than a snowflake machine. It's a project that takes input from a joystick
and uses that to draw a pattern on the plotter. The joystick can be used to draw an initial line, when the pen is lifted
then the plotter will draw a pattern based on the line drawn. 

At the moment that pattern is to:
 - rotate the line around the centre of the plot area with rotational symmetry of order six
 - reflected in the x-axis and then rotated around the centre of the plot area with rotational symmetry of order six

I expected that to produce a snowflake-like pattern, although in reality it can do flowers and other designs too.


TODO
----

Some ideas for further improvements:
 - [x] Narrow the circular area so there is a bigger margin around the edge of the plot area, that will make it more 
       asthetically pleasing.
 - [ ] At the moment there is a pause between drawing each segment whilst we calculate the next segment. This should be
       resolved somehow, possibly by sleeping for a little less time and pre-calculating the next segment so that
       we send the command before the pen has finished moving on the previous segment.
 - [ ] Add a way to draw the border of the plot area so that the pattern is contained within it. This will be 
       asthetically pleasing and also make it easier for the user to know where the plot area is (it's impossible to
       draw outside the circular area as otherwise it cannot always be rotated).
 - [ ] Consider making the pen height / z-axis adjustable so that the pen can be lifted and lowered during the drawing
       process. This would allow for more complex patterns to be drawn with things like brush pens.
 - [ ] Add a way to save the patterns drawn so that they can be replayed later. This would be useful for debugging and
       also for sharing the patterns with others.
 - [ ] Add a better user interface using the raspberry pi's touch screen.
 - [ ] Add constraints to the possible drawing directions. Two possible constraints are:
   - [ ] The movement must always be one of the 6 directions of the hexagon which makes snowflake like patterns more
         likely
   - [ ] The movement is automatically smoothed so that you can't do angular movements. This would make it easier to
         draw smooth curves and would make it easier to draw patterns that are more likely to be flower like.
 - [ ] Write some unit tests. This will make it a lot easier as it becomes more complicated
 - [x] Figure out why the ctrl-c doesn't work to stop the program. The threads are not being stopped properly so you
       currently have to press ctrl-c three times. 
 - [x] Query the plotter's configuration to get the width and height of the plotter. This will make it easier to 
       calculate the maximum radius for drawing.
