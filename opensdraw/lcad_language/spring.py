#!/usr/bin/env python
"""
.. module:: spring
   :synopsis: The spring function.

.. moduleauthor:: Hazen Babcock
"""

import math
import numbers
import numpy

import angles
import curveFunctions
import functions
import interpreter as interp
import lcadExceptions
import lcadTypes

lcad_functions = {}


#
# These classes create a spring function that can be used in opensdraw.
#
class LCadSpring(functions.LCadFunction):
    """
    **spring** - Creates a spring function.

    This function creates and returns a function that parametrizes a spring
    making it easier to add custom springs to a MOC. All units are LDU. The
    spring is oriented along the z-axis.

    :param length: The length of the spring.
    :param diameter: The diameter of the spring.
    :param gauge: The thickness of the spring wire.
    :param turns: The number of turns in the center part of the spring.
    :param end-turns: (optional) The number of turns at the end of the spring, default is 2.

    Usage::

     (import flexible-rod :locale)            ; Import the flexible-rod module.
     (def a-spring (spring 40 10 1 10))       ; Create a length 40 spring with diameter 10, gauge 1 and 10 turns.
     (flexible-rod a-spring 0 (a-spring t) 1) ; Draw a rod a long the path of a-spring with diameter 1.

     (def a-spring (spring 40 10 1 10 1))     ; Same as above, but with only 1 turn at the end.

    """

    def __init__(self):
        functions.LCadFunction.__init__(self, "spring")
        self.setSignature([[numbers.Number], [numbers.Number], [numbers.Number], [numbers.Number],
                           ["optional", [numbers.Number]]])

    def call(self, model, tree):
        args = self.getArgs(model, tree)

        end_turns = 2
        if (len(args) == 5):
            end_turns = args[4]

        # Create spring.
        spring = Spring(args[0], args[1], args[2], args[3], end_turns)

        # Return curve function.
        return curveFunctions.CurveFunction(spring, "user created spring function.")

lcad_functions["spring"] = LCadSpring()


#
# The classes below do the math necessary to create a spring.
#
class Spring(object):

    def __init__(self, length, diameter, gauge, turns, end_turns):
        self.radius = 0.5 * diameter
        self.fz = []

        # Starting turns.
        c1 = math.pi * diameter * end_turns
        z1 = gauge * end_turns
        d1 = math.sqrt(c1*c1 + z1*z1)
        if (end_turns > 0):
            self.fz.append([d1, 
                            0.5 * gauge, 
                            0, 
                            z1 / d1])

        # Middle turns.
        c2 = math.pi * diameter * turns
        z2 = length - gauge - 2.0*z1
        d2 = math.sqrt(c2*c2 + z2*z2)
        self.fz.append([d2 + d1, 
                        0.5 * gauge + z1, 
                        d1, 
                        z2 / d2])

        # End turns.
        if (end_turns > 0):
            self.fz.append([d2 + 2 * d1, 
                            0.5 * gauge + z1 + z2,
                            d2 + d1,
                            z1 / d1])

        self.length = d2 + 2*d1

    def getCoords(self, distance):
        """
        Return the position and orientation for a segment at distance along the spring.
        The z-axis points along the spring. The x-axis is the radial direction.
        """

        # Force to spring length.
        if (distance < 0):
            distance = 0
        elif (distance > self.length):
            distance = self.length

        for val in self.fz:
            if (distance <= val[0]):

                # Calculate position.
                d = (distance - val[2])
                a = math.sqrt(1.0 - val[3]*val[3])
                cos_t = math.cos(d * a / self.radius)
                sin_t = math.sin(d * a / self.radius)
                x = self.radius * cos_t
                y = self.radius * sin_t
                z = d * val[3] + val[1]

                # Calculate angles.
                x_vec = numpy.array([x, y, 0])
                z_vec = numpy.array([-sin_t * a, cos_t * a, val[3]])
                x_vec = x_vec / numpy.linalg.norm(x_vec)
                z_vec = z_vec / numpy.linalg.norm(z_vec)
                y_vec = numpy.cross(z_vec, x_vec)
                [rx, ry, rz] = angles.vectorsToAngles(x_vec, y_vec, z_vec)

                return [x, y, z, rx, ry, rz]

    def getLength(self):
        return self.length


#
# Testing
#
if (__name__ == "__main__"):
    import matplotlib as mpl
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt

    spring = Spring(10, 5, 0.1, 4, 0)
    print spring.getLength()
    for fz in spring.fz:
        print fz

    #d = numpy.linspace(0, spring.fz[1][0], 10)
    d = numpy.linspace(0, spring.getLength(), 100)
    plt.figaspect(1.0)
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    x = numpy.zeros(d.size)
    y = numpy.zeros(d.size)
    z = numpy.zeros(d.size)
    for i in range(d.size):
        [x[i], y[i], z[i]] = spring.getCoords(d[i])[:3]

    mpl.rcParams['legend.fontsize'] = 10
    ax.plot(x, y, z, label = 'spring')
    ax.legend()
        
    plt.show()
