#!/usr/bin/env python
#
# Using Python functions in OpenSDraw example. This requires PIL
# (or Pillow) to work.
#
# Hazen 03/15
#

import numbers
import os
from PIL import Image

# Define the basestring type for Python 3.
try:
    basestring
except NameError:
    basestring = str

# These OpenSDraw modules have some classes that we will use.
import opensdraw.lcad_language.interpreter as interpreter
import opensdraw.lcad_language.typeFunctions as typeFunctions

# This OpenSDraw module defines some types that we will use.
import opensdraw.lcad_language.lcadTypes as lcadTypes

# This OpenSDraw module defines some exceptions that we will use.
import opensdraw.lcad_language.lcadExceptions as lcadExceptions

# OpenSDraw will look for this dictionary to figure out what functions to import.
lcad_functions = {}

#
# Your function(s) (like all functions in OpenSDraw) should be a sub-class of 
# the interpreter.LCadFunction class.
#
# This class will open a user requested picture and return another class that
# the user can use to access various properties of the picture.
#
class OpenPicture(interpreter.LCadFunction):

    def __init__(self):

        # interpreter.LCadFunction.__init__ takes one argument, the name of the function.
        interpreter.LCadFunction.__init__(self, "picture")

        # Set the function signature so that the interpreter will type check for a single 
        # argument of type string (the name of the picture file). Use basestring since
        # this will also work with unicode strings.
        self.setSignature([[basestring]])

    # 
    # model is an instance of interpreter.Model. This stores the parts, groups,
    #    primitives and etc. This is the first argument to every function.
    #
    # filename is the name of the file.
    #
    # When you call this function the interpreter will check the arguments based on
    # the function signature provided in __init__(). The arguments to call should
    # match those in the signature.
    #
    def call(self, model, filename):

        # Check that the requested picture exists.
        if os.path.exists(filename):
            
            # Return an instance of the Picture class.
            return Picture(Image.open(filename))
    
        # If not, throw an exception.
        else:
            raise lcadExceptions.LCadException("picture " + filename + " not found.")

# Make sure to add an instance of your function to the functions dictionary.
lcad_functions["open-picture"] = OpenPicture()


#
# This class will return either the picture size, or the color at a particular
# pixel depending on the arguments that the user supplies
#
class Picture(interpreter.LCadFunction):

    def __init__(self, im):
        interpreter.LCadFunction.__init__(self, "user created picture function")

        # Store the PIL Image object.
        self.im = im

        # Set signature to be exactly two arguments both of which are numbers
        # or the symbols t/nil.
        self.setSignature([[numbers.Number, lcadTypes.LCadBoolean], [numbers.Number, lcadTypes.LCadBoolean]])

    def call(self, model, x, y):

        # If we got t/nil return the size of the picture.
        # (Note: To check for Truth use 'functions.isTrue(val)').
        if typeFunctions.isBoolean(x) or typeFunctions.isBoolean(y):
            return list(self.im.size)

        # Otherwise return the color of the pixel as a LDraw "direct" color. Best
        # practice might be to do some range checking. This will also fail for
        # certain types of images (such as .gif).
        [r, g, b] = self.im.getpixel((x, y))

        # Convert colors (0-255) to upper case hex & concatenate.
        return "0x2" + "".join(map(lambda x: "{0:#0{1}x}".format(x,4).upper()[2:], [r, g, b]))

