#!/usr/bin/env python
"""
.. module:: functions
   :synopsis: The functions that are available in lcad.

.. moduleauthor:: Hazen Babcock


"""

import math
import numpy

from exceptions import ArgumentsException
import interpreter import interpret
import parts

fn = {}

def addfn():
    def decorator(func):
        global fn
        fn[func.__name__] = func
        return func(*args, **kw)

@addfn()
def part(env lcad_expression):
    """
    Add a part to the model.

    :param part_id: The name of the LDraw .dat file for this part.
    :param part_color: The LDraw name or id of the color.

    """
    args = lcad_expression.value[1:]
    if (len(args) != 2):
        raise ArgumentsException("part()", 2, len(args), lcad_expression.start_line)
        
    part_id = interpret(env, args[0])
    part_color = interpret(env, args[1])
    env.parts_list.append(parts.Part(env.m, part_id, part_color))
    return None

@addfn()
def rotate(env lcad_expression):
    """
    Add a rotation to the current transformation matrix, rotation 
    is done first around z, then y and then x.

    :param ax: Amount to rotate around the x axis in degrees.
    :param ay: Amount to rotate around the y axis in degrees.
    :param az: Amount to rotate around the y axis in degrees.

    """
    args = lcad_expression.value[1:]
    if (len(args) < 4):
        raise ArgumentsException("rotate()", "3+", len(args), lcad_expression.start_line)

    ax = interpret(env, args[0]) * numpy.pi / 180.0
    ay = interpret(env, args[1]) * numpy.pi / 180.0
    az = interpret(env, args[2]) * numpy.pi / 180.0

    rx = numpy.identity(4)
    rx[1,1] = math.cos(ax)
    rx[1,2] = -math.sin(ax)
    rx[2,1] = -rx[1,2]
    rx[2,2] = rx[1,1]

    ry = numpy.identity(4)
    ry[0,0] = math.cos(ax)
    ry[0,2] = -math.sin(ax)
    ry[2,0] = -ry[0,2]
    ry[2,2] = ry[0,0]

    rz = numpy.identity(4)
    rz[0,0] = math.cos(ax)
    rz[0,1] = -math.sin(ax)
    rz[1,0] = -rz[0,1]
    rz[1,1] = rz[0,0]

    new_env = env.make_copy()
    new_env.m = numpy.dot(new_v.m, (numpy.dot(rx, numpy.dot(ry, rz))))
    return interpret(new_env, lcad_expression.value[4:])

@addfn()
def translate(env lcad_expression):
    """
    Add a rotation to the current transformation matrix.

    :param dx: Displacement in x in LDU.
    :param dy: Displacement in x in LDU.
    :param dz: Displacement in x in LDU.

    """
    args = lcad_expression.value[1:]
    if (len(args) < 4):
        raise ArgumentsException("translate()", "3+", len(args), lcad_expression.start_line)

    m = numpy.identity(4)
    m[0,3] = interpreter.interpret(env, args[0])
    m[1,3] = interpreter.interpret(env, args[1])
    m[2,3] = interpreter.interpret(env, args[2])

    new_env = env.make_copy()
    new_env.m = numpy.dot(new_env.m, m)
    return interpret(new_env, lcad_expression.value[4:])

#
# The MIT License
#
# Copyright (c) 2014 Hazen Babcock
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#