#!/usr/bin/env python
#
## @file
#
# A PyQt OpenGL widget for rendering parts.
#
# Hazen 07/14
#

import math
import numpy
import sys

from OpenGL import GL, GLU
from PyQt4 import QtCore, QtGui, QtOpenGL

import scad_lib.datFileParser as datFileParser
import scad_lib.glParser as glParser

## GLWidget
#
# The GL widget for displaying a part.
#
class GLWidget(QtOpenGL.QGLWidget):

    ## __init__
    #
    # @param parent The PyQT parent of this widget.
    #
    def __init__(self, parent):
        QtOpenGL.QGLWidget.__init__(self, parent)

        self.edge_color = [0, 0, 0, 1]
        self.face_color = [1, 0, 0, 1]
        self.last_pos = QtCore.QPoint()
        self.offset = numpy.array([[0], [0], [0], [0]], dtype = numpy.float32)
        self.p_matrix = None           # Projection matrix.
        self.part = None
        self.m_r_matrix = None         # Model rotation matrix.
        self.m_s_matrix = None         # Model scale matrix.
        self.m_t_matrix = None         # Model translation matrix.
        self.v_matrix = None           # View matrix.
        self.v_r_matrix = None         # View rotation matrix.
        self.verbose = True

        self.initializeMatrices()
        self.setMinimumSize(500, 500)

    ## initializeGL
    #
    # Initialize OpenGL.
    #
    def initializeGL(self):

        if self.verbose:
            print 'OpenGL info'
            print ' Vendor: %s' % (GL.glGetString(GL.GL_VENDOR))
            print ' Opengl version: %s' % (GL.glGetString(GL.GL_VERSION))
            print ' GLSL Version: %s' % (GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION))
            print ' Renderer: %s' % (GL.glGetString(GL.GL_RENDERER))

        GL.glClearColor(1.0, 1.0, 1.0, 1.0)

        # FIXME: Get backface culling to work properly.
        #
        #GL.glFrontFace(GL.GL_CCW)
        #GL.glEnable(GL.GL_CULL_FACE)

        GL.glEnable(GL.GL_DEPTH_TEST)

    ## initializeMatrices
    #
    # Set matrices to the correct initial values.
    #
    def initializeMatrices(self):
        self.m_r_matrix = numpy.identity(4, dtype = numpy.float32)
        self.m_s_matrix = numpy.identity(4, dtype = numpy.float32)*0.01
        self.m_t_matrix = numpy.identity(4, dtype = numpy.float32)
        self.v_r_matrix = numpy.identity(4, dtype = numpy.float32)
        self.m_s_matrix[3,3] = 1.0

    ## loadPart
    #
    # @param filename The filename of the part to load.
    #
    def loadPart(self, filename):
        if self.part is not None:
            self.part.freeGL()
        self.part = glParser.GLParser()
        datFileParser.parsePartFile(self.part, filename)
        self.initializeMatrices()
        self.updateGL()

    ## mousePressEvent
    #
    # @param event A PyQt QMouseEvent.
    #
    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    ## mouseMoveEvent
    #
    # @param event A PyQT QMouseEvent.
    #
    def mouseMoveEvent(self, event):
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()

        if (event.buttons() == QtCore.Qt.LeftButton):
            self.rotateView(dx, dy)
        elif (event.buttons() == QtCore.Qt.RightButton):
            self.translateView(dx, dy)

        self.lastPos = event.pos()
        self.updateGL()

    ## paintGL
    #
    # Paints the OpenGL scene.
    #
    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        if self.part is not None:
            m = numpy.dot(self.m_s_matrix, numpy.dot(self.m_t_matrix, self.m_r_matrix))
            mvp = numpy.dot(m, numpy.dot(self.v_matrix, self.p_matrix))
            self.part.render(mvp, self.face_color, self.edge_color)

        GL.glFlush()

    ## resizeGL
    #
    # @param w The new widget width.
    # @param h The new widget height.
    #
    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)
        
        # Use OpenGL to figure out the projection matrix for us.
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(20.0, float(w)/float(h), 0.1, 10.0)
        self.p_matrix = numpy.array(GL.glGetDoublev(GL.GL_PROJECTION_MATRIX),
                                    dtype = numpy.float32)

        self.updateView()

    ## rotateView
    #
    # @param dx The amount to rotate the view matrix by around the current y axis.
    # @param dy The amount to rotate the view matrix by around the current x axis.
    #
    def rotateView(self, dx, dy):
        dx = -dx/50.0
        dy = dy/50.0
        rot_x = numpy.matrix([[math.cos(dx), 0, math.sin(dx), 0],
                              [0, 1, 0, 0],
                              [-math.sin(dx), 0, math.cos(dx), 0],
                              [0, 0, 0, 1]],
                           dtype = numpy.float32)
        rot_y = numpy.matrix([[1, 0, 0, 0],
                              [0, math.cos(dy), math.sin(dy), 0],
                              [0, -math.sin(dy), math.cos(dy), 0],
                              [0, 0, 0, 1]],
                             dtype = numpy.float32)
        self.v_r_matrix = numpy.dot(self.v_r_matrix, numpy.dot(rot_x, rot_y))
        self.updateView()

    ## setColor
    #
    # @param face_color The color to use triangle faces.
    # @param edge_color The color to use for lines.
    #
    def setColor(self, face_color, edge_color):
        self.face_color = face_color
        self.edge_color = edge_color
        self.updateGL()

    ## translateView
    #
    # @param dx The amount to translate the view by along the current x axis.
    # @param dy The amount to translate the view by along the current y axis.
    #
    def translateView(self, dx, dy):
        gain = 0.005
        temp = numpy.array([[-gain * dx], [gain * dy], [0], [0]], dtype = numpy.float32)
        self.offset += numpy.dot(self.v_r_matrix, temp)
        self.updateView()

    ## updateView
    #
    # Update the view matrix based on the current rotation and translation.
    #
    def updateView(self):
        eye_pos = numpy.array([[0], [0], [5], [0]], dtype = numpy.float32)  # Eye location.
        eye_pos = numpy.dot(self.v_r_matrix, eye_pos)

        up = numpy.array([[0], [1], [0], [0]], dtype = numpy.float32)  # Up vector.
        up = numpy.dot(self.v_r_matrix, up)

        GL.glLoadIdentity()
        GLU.gluLookAt(self.offset[0,0] + eye_pos[0,0], self.offset[1,0] + eye_pos[1,0], self.offset[2,0] + eye_pos[2,0],
                      self.offset[0,0], self.offset[1,0], self.offset[2,0],
                      up[0,0], up[1,0], up[2,0])
        self.v_matrix = numpy.array(GL.glGetDoublev(GL.GL_PROJECTION_MATRIX),
                                    dtype = numpy.float32)

    ## wheelEvent
    #
    # @param event A PyQt QMouseEvent.
    #
    def wheelEvent(self, event):
        gain = 1.2
        if (event.delta() > 0):
            for i in range(3):
                self.m_s_matrix[i,i] = self.m_s_matrix[i,i] * gain
        else:
            for i in range(3):
                self.m_s_matrix[i,i] = self.m_s_matrix[i,i] / gain
        self.updateGL()


## GLWidgetTest
#
# For testing the GLWidget.
#
class GLWidgetTest(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.gl_widget = GLWidget(self)
        self.setCentralWidget(self.gl_widget)
        QtCore.QTimer.singleShot(0, self.loadPart)

    def loadPart(self):
        #self.gl_widget.loadPart("C:/Program Files (x86)/LDraw/parts/1.dat")
        self.gl_widget.loadPart("C:/Program Files (x86)/LDraw/parts/32523.dat")
        #self.gl_widget.loadPart("C:/Program Files (x86)/LDraw/parts/u8001a.dat")


if (__name__ == '__main__'):
    app = QtGui.QApplication(sys.argv)
    window = GLWidgetTest()
    window.show()
    app.exec_()

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
