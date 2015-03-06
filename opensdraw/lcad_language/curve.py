#!/usr/bin/env python
"""
.. module:: curve
   :synopsis: The curve function.

.. moduleauthor:: Hazen Babcock

"""

import math
import numbers
import numpy
from scipy.optimize import minimize

import functions
import interpreter as interp
import lcadExceptions

lcad_functions = {}


#
# These classes create a curve function that can be used in opensdraw.
#
class CurveFunction(functions.LCadFunction):

    def __init__(self, curve):
        functions.LCadFunction.__init__(self, "user created curve function")
        self.curve = curve

    def argCheck(self, tree):
        if (len(tree.value) != 2):
            raise lcadExceptions.NumberArgumentsException("1", len(tree.value) - 1)

    def call(self, model, tree):
        arg = interp.getv(interp.interpret(model, tree.value[1]))

        # If arg is t return the curve length.
        if (arg is interp.lcad_t):
            return self.curve.length

        # Get distance along curve.
        if not isinstance(arg, numbers.Number):
            raise lcadExceptions.WrongTypeException("number", type(arg))

        # Determine position and orientation.
        return interp.List(self.curve.getCoords(arg))


class LCadCurve(functions.LCadFunction):
    """
    **curve** - Creates a curve function.
    
    This function creates and returns a function that parametrizes a curve, specifically
    a cubic spline. All units are LDU. Each control point is specified by a list of lists
    in the form *((xp yp zp) (dx dy dz))*, where xp, yp and zp specify the location of the
    control point and dx, dy, dz specify the derivative (tangent) of the line as it 
    passes through the control point. A curve must have at least two control points, and
    additionally you must provide a (approximately) perpendicular vector to the
    derivate *((xp yp zp) (dx dy dz) (px py pz))* for the first control point.

    When you call the created curve function you will get the 6 element list *(x y z rx ry rz)* 
    where x, y, z are the location of the curve and rx, ry, rz are the angles that will rotate
    from the current coordinate system to the curve coordinate system. In the curve
    coordinate system z is along the curve and x is perpendicular to the coordinate system
    as defined by the perpendicular vector provided for the 1st control point. The distance
    argument to the created curve function will be adjusted to be in the range 0 - curve
    length if the argument falls outside of this range.

    If you call the created curve function with the argument **t** it will return the length
    of the curve.

    Additionally curve has several keyword arguments::

      :auto-scale   t/nil        ; default is t, automatically scale the derivative to
                                 ; minimize the maximum curvature of the curve.
      :extrapolate  t/nil        ; default is t, distances outside of the curve will be
                                 ; linearly extrapolated from the end of the curve. If nil
                                 ; then the distance will be modulo the curve length.
      :scale        float > 0.0  ; multiplier for auto-scale mode, defaults to 1. This 
                                 ; sets the boundaries on the auto-scale optimal
                                 ; derivative search range. If you change this you probably 
                                 ; want a number greater than 1.0, which is the default value.
      :twist        angle        ; additional twist along the curve, defaults to 0.

    Unfortunately auto scaling is a bit slow and sometimes fails, so more work is needed..

    Usage::

     (def my-curve (curve (list (list (list 0 0 0) (list 1 1 0) (list 0 0 1)) ; Create a curve going through (0,0,0), (5,0,0)
                                (list (list 5 0 0) (list 1 0 0))))            ; With derivative (1,1,0) and (1,0,0). Since we did
                                                                              ; not specify :auto-scale nil, the derivative will
                                                                              ; be scaled to create a hopefully pleasing curve.

     (def p1 (my-curve 1))                                                    ; p1 is the list (x y z rx ry rz) which defines the
                                                                              ; curve at distance one along the curve.
     (my-curve t)                                                             ; Returns the length of the curve.

    """
    def __init__(self):
        functions.LCadFunction.__init__(self, "curve")

    def argCheck(self, tree):
        if (len(tree.value) < 2):
            raise lcadExceptions.NumberArgumentsException(len(tree.value)-1)
        
        # Check keyword arguments.
        if (len(tree.value) > 2):
            args = tree.value[2:]
            index = 0
            while (index < len(args)):
                arg = args[index]
            
                if (arg.value[0] == ":"):
                    if not (arg.value in [":auto-scale", ":extrapolate", ":scale", ":twist"]):
                        raise lcadExceptions.UnknownKeywordException(arg.value)
                    index += 2
                    if (index > len(args)):
                        raise lcadExceptions.KeywordValueException()
                else:
                    raise ControlPointException(arg.value + " is not a list or a keyword")

    def call(self, model, tree):

        # Keyword defaults.
        auto_scale = True
        extrapolate = True
        scale = 1.0
        twist = 0

        # Get list of control points.
        controlp_list = interp.getv(interp.interpret(model, tree.value[1]))
        if not isinstance(controlp_list, interp.List):
            raise lcadExceptions.WrongTypeException("list", type(controlp_list))

        if (controlp_list.size < 2):
            raise NumberControlPointsException(controlp_list.size)

        # Process keywords.
        index = 0
        args = tree.value[2:]
        while (index < len(args)):
            arg = args[index]

            # Process keyword.
            if (arg.value == ":auto-scale"):
                auto_scale = functions.isTrue(model, args[index+1])
            if (arg.value == ":extrapolate"):
                extrapolate = functions.isTrue(model, args[index+1])
            if (arg.value == ":scale"):
                scale = interp.getv(interp.interpret(model, args[index+1]))
                if not isinstance(scale, numbers.Number):
                    raise lcadExceptions.WrongTypeException("number", type(scale))
            if (arg.value == ":twist"):
                twist = interp.getv(interp.interpret(model, args[index+1]))
                if not isinstance(twist, numbers.Number):
                    raise lcadExceptions.WrongTypeException("number", type(twist))
            index += 2

        # Process control points.
        control_points = []
        for i in range(controlp_list.size):

            # Get list of control point vectors.
            control_point = interp.getv(controlp_list.getv(i))

            if not isinstance(control_point, interp.List):
                raise lcadExceptions.WrongTypeException("list", type(control_point))

            if (i == 0):
                if (control_point.size != 3):
                    raise ControlPointException("First control point must include a perpendicular vector.")
            else:
                if (control_point.size != 2):
                    raise ControlPointException("Control point must have a location and a derivative (tangent) vector.")

            # Process control point vectors.
            vals = []
            for j in range(control_point.size):                
                vec = interp.getv(control_point.getv(j))
            
                if isinstance(vec, interp.List):
                    if (vec.size != 3):
                        raise ControlPointException("Control point vector must have 3 elements")

                    for k in range(3):
                        val = interp.getv(vec.getv(k))
                        if not isinstance(val, numbers.Number):
                            raise lcadExceptions.WrongTypeException("number", type(val))
                        vals.append(val)

                elif isinstance(vec, numpy.ndarray):
                    for k in range(3):
                        vals.append(vec[k])

                else:
                    raise lcadExceptions.WrongTypeException("list, numpy.ndarray", type(vec))

            # Check that tangent is not zero.
            tx = vals[3]
            ty = vals[4]
            tz = vals[5]
            if ((tx*tx + ty*ty + tz*tz) < 1.0e-3):
                raise TangentException()

            # Create control point.
            control_points.append(ControlPoint(*vals))

        # Create curve.
        curve = Curve(auto_scale, extrapolate, scale, twist)
        for i in range(len(control_points)-1):
            curve.addSegment(control_points[i], control_points[i+1])

        # Return curve function.
        return CurveFunction(curve)

lcad_functions["curve"] = LCadCurve()


class ControlPointException(lcadExceptions.LCadException):
    def __init__(self, msg):
        lcadExceptions.LCadException.__init__(self, msg)
        

class NumberControlPointsException(lcadExceptions.LCadException):
    def __init__(self, got):
        lcadExceptions.LCadException.__init__(self, "A curve must have at least 2 control points, got " + str(got))


class TangentException(lcadExceptions.LCadException):
    def __init__(self):
        lcadExceptions.LCadException.__init__(self, "The length of the tangent line must be greater than 0.")


#
# The classes below do the math necessary to create a curve.
#
# In the curve coordinate system the z vector is the tangent to the
# curve and x/y vectors are perpendicular to the curve.
#

def crossProduct(u, v):
    cp = numpy.zeros(3)
    cp[0] = u[1]*v[2] - u[2]*v[1]
    cp[1] = u[2]*v[0] - u[0]*v[2]
    cp[2] = u[0]*v[1] - u[1]*v[0]
    return cp

def dotpVector(v1, v2):
    return numpy.sum(v1 * v2)

def normVector(vector):
    return vector/numpy.sqrt(numpy.sum(vector * vector))

# Return the projection of vector1 onto vector2.
def projVector(v1, v2):
    return numpy.dot(v1, v2) * v2

def toDegrees(angle):
    return 180.0 * angle/math.pi


class ControlPoint(object):

    def __init__(self, x, y, z, dx, dy, dz, px = 0, py = 0, pz = 0):
        
        self.location = numpy.array([x, y, z])
        self.raw_z_vec = numpy.array([dx, dy, dz])
        self.x_vec = numpy.array([px, py, pz])

        if (dotpVector(self.raw_z_vec, self.raw_z_vec) == 0.0):
            raise TangentException

        self.z_vec = normVector(self.raw_z_vec)

        # Only the first point has a perpendicular vector.
        if (dotpVector(self.x_vec, self.x_vec) > 0.1):

            # Normalize perpendicular vector.
            self.x_vec = normVector(self.x_vec)
            
            # Adjust x_vec to make it exactly perpendicular to z_vec
            # and normalize it's length to one.
            self.x_vec = normVector(self.x_vec - projVector(self.z_vec, self.x_vec))

            # Compute cross-product of z_vec and x_vec to create y vector.
            self.y_vec = crossProduct(self.z_vec, self.x_vec)

        else:
            self.x_vec = None
            self.y_vec = None


class Curve(object):

    def __init__(self, normalize, extrapolate, scale, total_twist):
        self.extrapolate = extrapolate
        self.length = 0
        self.normalize = normalize
        self.scale = scale
        self.segments = []
        self.total_twist = total_twist

    def addSegment(self, cp1, cp2):

        if self.normalize:

            # Adjust derivatives at the control points to minimize the maximum curvature of the segment.
            segment = Segment(cp1, cp2)

            # Check if the segment is already basically straight.
            if not (segment.maxCurvature() < 1.0e-2):

                dist = cp1.location - cp2.location
                d_scale = 2.0 * numpy.sqrt(numpy.sum(dist*dist))

                # Minimize curvature using nelder-mead algorithm.
                def errf(x):
                    if (x[0] < 0.1 * d_scale):
                        x[0] = 0.1 * d_scale
                    if (x[0] > d_scale * self.scale):
                        x[0] = d_scale * self.scale
                    if (x[1] < 0.1 * d_scale):
                        x[1] = 0.1 * d_scale
                    if (x[1] > d_scale * self.scale):
                        x[1] = d_scale * self.scale
                    cp1.raw_z_vec = cp1.z_vec * x[0]
                    cp2.raw_z_vec = cp2.z_vec * x[1]
                    segment = Segment(cp1, cp2)
                    max_c = segment.maxCurvature()
                    return max_c

                x0 = numpy.array([0.5 * d_scale * self.scale, 
                                  0.5 * d_scale * self.scale])
                res = minimize(errf, 
                               x0, 
                               method='nelder-mead',
                               #method = 'powell',
                               options={'xtol': 1e-3, 'disp': False})

                if not res.success:
                    print "Curve auto-scaling failed!"
                    print res

                # Create segment with optimal values.
                cp1.raw_z_vec = cp1.z_vec * res.x[0]
                cp2.raw_z_vec = cp2.z_vec * res.x[1]
                segment = Segment(cp1, cp2)

        else:
            segment = Segment(cp1, cp2)

        # Finish segment setup.
        segment.calcLUTs(self.length)

        # Add segment length to current length & save segment.
        self.length += segment.length
        self.segments.append(segment)

    def getCoords(self, dist):

        if not self.extrapolate:
            while (dist < 0):
                dist += self.length
            while (dist > self.length):
                dist -= self.length

        if (dist < 0):
            a_seg = self.segments[0]
        elif (dist > self.length):
            a_seg = self.segments[-1]
        else:
            for seg in self.segments:
                if (dist >= seg.dist_lut[0][1]) and (dist <= seg.dist_lut[-1][1]):
                    a_seg = seg
                    break
            
        # Get position and angles.
        [x, y, z, rx, ry, rz] = a_seg.getCoords(dist)

        # Add twist to the z angle.
        rz += self.total_twist * (dist / self.length)
        return [x, y, z, rx, ry, rz]
                

class Segment(object):

    def __init__(self, control_point_1, control_point_2):

        # Control point 1 is assumed to have a valid perpendicular (x_vec).
        # Control point 2 will be modified to have a valid (non-zero) x_vec.
        self.cp1 = control_point_1
        self.cp2 = control_point_2

        # Calculate x, y, z polynomial coefficients. Basically we are creating
        # a cubic-spline that goes through the two control points with the
        # specified derivative at the control points.
        A = numpy.array([[0, 0, 0, 1],
                         [0, 0, 1, 0],
                         [1, 1, 1, 1],
                         [3, 2, 1, 0]])

        vx = numpy.array([self.cp1.location[0],
                          self.cp1.raw_z_vec[0],
                          self.cp2.location[0],
                          self.cp2.raw_z_vec[0]])

        vy = numpy.array([self.cp1.location[1],
                          self.cp1.raw_z_vec[1],
                          self.cp2.location[1],
                          self.cp2.raw_z_vec[1]])

        vz = numpy.array([self.cp1.location[2],
                          self.cp1.raw_z_vec[2],
                          self.cp2.location[2],
                          self.cp2.raw_z_vec[2]])

        self.x_coeff = numpy.linalg.solve(A, vx)
        self.y_coeff = numpy.linalg.solve(A, vy)
        self.z_coeff = numpy.linalg.solve(A, vz)

    #
    # This is the same approach that is used in ldraw_to_lcad.py to 
    # extract the rotation angles from the rotation matrix.
    #
    def angles(self, p, x_vec):

        # Calculate z vector.
        z_vec = normVector(self.d_xyz(p))
    
        # Calculate x vector.
        proj = projVector(x_vec, z_vec)
        x_vec = normVector(x_vec - proj)

        # Calculate y vector
        y_vec = crossProduct(z_vec, x_vec)

        # Calculate rotation angles.
        ry = math.atan2(-z_vec[0], math.sqrt(z_vec[1]*z_vec[1] + z_vec[2]*z_vec[2]))

        # If the rotation around the y axis is +- 90 then we can't separate the x-axis rotation
        # from the z-axis rotation. In this case we just assume that the x-axis rotation is
        # zero and that there was only z-axis rotation.
        if (abs(math.cos(ry)) < 1.0e-3):
            rx = 0
            rz = math.atan2(x_vec[1],y_vec[1])
        else:
            rx = math.atan2(-z_vec[1], z_vec[2])
            rz = math.atan2(-y_vec[0], x_vec[0])

        return map(lambda(x): x * 180.0/math.pi, [rx, ry, rz])

    def calcLUTs(self, dist_offset):

        # Compute distance look-up table and segment length
        table_size = 100  # Hopefully 100 sections is enough to accurately capture most curves.
        #table_size = int(round(4.0 * cp_dist))
        self.dist_lut = numpy.zeros((table_size, 2))
        self.dist_lut[0,1] = dist_offset
        total_dist = 0.0
        startp = self.xyz(0.0)
        for i in range(table_size - 1):
            p = float(i+1)/float(table_size - 1)
            endp = self.xyz(p)
            dp = endp - startp
            total_dist += numpy.sqrt(numpy.sum(dp*dp))
            self.dist_lut[i+1, 0] = p
            self.dist_lut[i+1, 1] = total_dist + dist_offset
            startp = endp
        self.length = total_dist

        # Compute perpendicular vector look-up table. We need this
        # in order to return the proper angles to go from world
        # coordinates to curve coordinates.
        self.xvec_lut = numpy.zeros((table_size, 3))
        self.xvec_lut[0,:] = self.cp1.x_vec
        for i in range(table_size - 1):
            p = float(i+1)/float(table_size - 1)
            dxyz = normVector(self.d_xyz(p))
            proj = projVector(self.xvec_lut[i,:], dxyz)
            self.xvec_lut[i+1,:] = normVector(self.xvec_lut[i,:] - proj)

        # This is so that the perpendicular vector will be propogated
        # along the curve.
        self.cp2.x_vec = self.xvec_lut[-1,:]

    def curvature(self, p):
        p_vec = numpy.array([3.0*p*p, 2.0*p, 1.0, 0.0])
        pp_vec = numpy.array([6.0*p, 2.0, 0.0, 0.0])

        # Calculate derivatives.
        xp = numpy.sum(self.x_coeff * p_vec)
        xpp = numpy.sum(self.x_coeff * pp_vec)
        yp = numpy.sum(self.y_coeff * p_vec)
        ypp = numpy.sum(self.y_coeff * pp_vec)
        zp = numpy.sum(self.z_coeff * p_vec)
        zpp = numpy.sum(self.z_coeff * pp_vec)

        #
        # Calculate curvature following:
        #  http://en.wikipedia.org/wiki/Curvature#Local_expressions_2
        #
        t1 = zpp*yp - ypp*zp
        t2 = xpp*zp - zpp*xp
        t3 = ypp*xp - xpp*yp

        return math.sqrt(t1*t1 + t2*t2 + t3*t3)/math.pow(xp*xp + yp*yp + zp*zp, 1.5)

    def d_xyz(self, p):
        p_vec = numpy.array([3.0*p*p, 2.0*p, 1.0, 0.0])
        return numpy.array([numpy.sum(self.x_coeff * p_vec),
                            numpy.sum(self.y_coeff * p_vec),
                            numpy.sum(self.z_coeff * p_vec)])

    def getCoords(self, distance):

        # Extrapolate from curve start.
        if (distance <= 0):
            p = 0
            start = 0
            a_xyz = self.xyz(p) + distance * normVector(self.d_xyz(p))

        # Extrapolate from curve end.
        elif (distance >= self.dist_lut[-1][1]):
            p = 1
            start = len(self.dist_lut) - 1
            a_xyz = self.xyz(p) + (distance - self.dist_lut[-1][1]) * normVector(self.d_xyz(p))

        # Interpolate in the middle.
        else:
            # Mid-point bisection to find the bracketing 
            # points in the distance look up table.
            start = 0
            end = len(self.dist_lut) - 1
            mid = (end - start)/2
            while ((end - start) > 1):
                if (distance > self.dist_lut[mid, 1]):
                    start = mid
                elif (distance == self.dist_lut[mid, 1]):
                    start = mid
                    end = start + 1
                else:
                    end = mid
                mid = (end - start)/2 + start

            # Interpolate between bracketing points.
            ratio = (distance - self.dist_lut[start, 1])/(self.dist_lut[end, 1] - self.dist_lut[start, 1])
            p = ratio * (self.dist_lut[end, 0] - self.dist_lut[start, 0]) + self.dist_lut[start, 0]
        
            # Get xyz
            a_xyz = self.xyz(p)

        # Get angles
        [rx, ry, rz] = self.angles(p, self.xvec_lut[start,:])
        return [a_xyz[0], a_xyz[1], a_xyz[2], rx, ry, rz]

    def maxCurvature(self):
        p = numpy.arange(0, 1.0, 0.01)
        max_p = 0
        max_c = 0.0
        for i in range(p.size):
            c = self.curvature(p[i])
            if (c > max_c):
                max_p = p[i]
                max_c = c
        #print max_p
        return max_c

    def xyz(self, p):
        p_vec = numpy.array([p*p*p, p*p, p, 1.0])
        return numpy.array([numpy.sum(self.x_coeff * p_vec),
                            numpy.sum(self.y_coeff * p_vec),
                            numpy.sum(self.z_coeff * p_vec)])


#
# Testing
#
if (__name__ == "__main__"):

    cp1 = ControlPoint(0, 0, 0, 1, 1, 0, 0, 0, 1.0)
    cp2 = ControlPoint(2, 0, 0, 1, 0, 0)
    cp3 = ControlPoint(4, 0, 0, 1, 1, 0)

    curve = Curve(False, True, 1.0, 0)
    curve.addSegment(cp1, cp2)
    curve.addSegment(cp2, cp3)

    print curve.segments[0].maxCurvature()

    x = numpy.arange(-1, curve.length + 1, 0.1)
    xf = numpy.zeros(x.size)
    yf = numpy.zeros(x.size)
    for i in range(x.size):
        [cx, cy, cz, rx, ry, rz] = curve.getCoords(x[i])
        xf[i] = cx
        yf[i] = cy

    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1, aspect = 1.0)
    ax.plot(xf, yf)
    plt.show()


#
# The MIT License
#
# Copyright (c) 2015 Hazen Babcock
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
