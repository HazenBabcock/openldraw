#!/usr/bin/env python
"""
.. module:: lcad_to_ldraw
   :synopsis: Generates a ldraw format file from a lcad model.

.. moduleauthor:: Hazen Babcock
"""

import os
import sys

import opensdraw.lcad_language.interpreter as interpreter

if (len(sys.argv) < 2):
    print "usage: <lcad file> <ldraw file (optional)> <time points (optional)>"
    print "       If you want to specify time points you also have to specify the ldraw file."
    exit()

# Parse arguments.
output_fname = sys.argv[1][:-4]
time_points = 1
if (len(sys.argv) == 3):
    output_fname = sys.argv[2]
elif (len(sys.argv) == 4):
    output_fname = sys.argv[2]
    try:
        time_points = int(sys.argv[3])
    except ValueError as e:
        print "Third argument (time points) is not an integer."
        raise

# Read input file.
with open(sys.argv[1]) as fp:
    ldraw_file_contents = fp.read()

# Generate output files.
cur_dir = os.getcwd()    
index = 0
while (index < time_points):

    # Change current working directory to the location of the lcad file (so that imported files will be found correctly).
    if not (os.path.dirname(sys.argv[1]) == ""):
        os.chdir(os.path.dirname(sys.argv[1]))

    # Generate model.
    model = interpreter.execute(ldraw_file_contents, filename = sys.argv[1], time_index = index)

    # Check for single or multi-part model.
    mp_model = False
    if (len(model.groups()) > 1):
        mp_model = True

    # Some feedback.
    n_parts = 0
    if (index == 0):
        if mp_model:
            for group in model.groups():
                if (group.getNParts() > 0):
                    n_parts += group.getNParts()
                    print "Group:", group.name, "has", group.getNParts(), "parts."
                if (group.getNPrimitives() > 0):
                    n_parts += group.getNPrimitives()
                    print "Group:", group.name, "has", group.getNPrimitives(), "primitives."
        else:
            group = model.groups()[0]
            if (group.getNParts() > 0):
                n_parts += group.getNParts()
                print "Model has", group.getNParts(), "parts."
            if (group.getNPrimitives() > 0):
                n_parts += group.getNPrimitives()
                print "Model has", group.getNPrimitives(), "primitives."
    elif ((index % 10) == 0):
        print " time step", index

    # Go to next iteration if there are no parts.
    if (n_parts == 0):
        index += 1
        continue

    # Reset working directory.
    os.chdir(cur_dir)

    # If the user provided a filename, then we just use it. If not then
    # use .dat for single part models and .mpd for multi-part models.
    dat_fname = output_fname
    if (len(sys.argv) == 2):
        if mp_model:
            dat_fname += "mpd"
        else:
            dat_fname += "dat"

    # And file number for animations.
    if (time_points > 1):
        [name, ext] = os.path.splitext(output_fname)
        dat_fname = name + "_" + "{0:05d}".format(index) + ext
        
    # Write the file.
    with open(dat_fname, "w") as fp_out:

        added_opensdraw = False
        for group in model.groups():

            # Add file identifier for MPD document.
            if mp_model:
                fp_out.write("0 FILE " + group.name + "\n")

            # Add header.
            for text in group.header:
                fp_out.write("0 " + text + "\n")

            # Add program identifier (only to the first group).
            if not added_opensdraw:
                fp_out.write("0 // Generated by opensdraw from " + os.path.basename(sys.argv[1]) + "\n")
                added_opensdraw = True

            fp_out.write("\n")
            # Add parts.
            parts = group.getParts()
            for i in range(len(parts)):

                # Write part.
                fp_out.write(parts[i].toLDraw() + "\n")

                # Check if we need to add a step.
                if (i < (len(parts)-1)) and not group.have_comments:
                    if (parts[i].step != parts[i+1].step):
                        fp_out.write("0 STEP\n")

            fp_out.write("\n\n")

    index += 1

print "Done."
