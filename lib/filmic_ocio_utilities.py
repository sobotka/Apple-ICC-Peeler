#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Defines OCIO utility functions.
"""

import os
import PyOpenColorIO


def OCIOCreateTransforms(config, transforms):
    # for name, description, family, isdata, allocationvars, bitdepth, type, \
    #         variables, direction in transforms:
    for transform_details in transforms:
        colorspace = PyOpenColorIO.ColorSpace()
        colorspace.setName(transform_details["name"])
        colorspace.setDescription(transform_details["description"])
        colorspace.setFamily(transform_details["family"])
        colorspace.setIsData(transform_details["isdata"])
        colorspace.setAllocationVars(
            [
                transform_details["allocationvars"]["from"],
                transform_details["allocationvars"]["to"]
            ]
        )
        colorspace.setAllocation(transform_details["allocationvars"]["type"])
        colorspace.setBitDepth(transform_details["bitdepth"])
        if transform_details["type"] is "ExponentTransform":
            transform = PyOpenColorIO.ExponentTransform(
                [
                    transform_details["variables"]["exponentR"],
                    transform_details["variables"]["exponentG"],
                    transform_details["variables"]["exponentB"],
                    transform_details["variables"]["exponentA"]
                ]
            )
        colorspace.setTransform(transform, transform_details["direction"])
        config.addColorSpace(colorspace)


def OCIOCreateAllocationTransform(minValue, maxValue, type, offset=None,
                                  direction=None):
    transform = PyOpenColorIO.AllocationTransform()
    if offset is not None:
        transform.setVars([minValue, maxValue, offset])
    else:
        transform.setVars([minValue, maxValue])
    if direction is not None:
        transform.setDirection(direction)
    transform.setAllocation(type)
    return transform


def OCIOSetDisplays(config, display_transforms):
    for display_name, transform_name, transform in display_transforms:
        config.addDisplay(display_name, transform_name, transform)


def OCIOSetRoles(config,
                 color_picking=None,
                 color_timing=None,
                 compositing_log=None,
                 data=None,
                 default=None,
                 matte_paint=None,
                 reference=None,
                 scene_linear=None,
                 texture_paint=None,
                 rendering=None,
                 compositing_linear=None):

    if color_picking is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_COLOR_PICKING,
                       color_picking)
    if color_timing is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_COLOR_TIMING, color_timing)
    if compositing_log is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_COMPOSITING_LOG,
                       compositing_log)
    if data is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_DATA, data)
    if default is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_DEFAULT, default)
    if matte_paint is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_MATTE_PAINT,
                       matte_paint)
    if reference is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_REFERENCE, reference)
    if texture_paint is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_TEXTURE_PAINT,
                       texture_paint)
    if rendering is not None:
        config.setRole('rendering', rendering)
    if compositing_linear is not None:
        config.setRole('compositing_linear', compositing_linear)
    if scene_linear is not None:
        config.setRole(PyOpenColorIO.Constants.ROLE_SCENE_LINEAR, scene_linear)
        if rendering is None:
            config.setRole('rendering', scene_linear)
        if compositing_linear is None:
            config.setRole('compositing_linear', scene_linear)

    return True


def OCIOWriteSPI1D(filename, values, from_minimum=0., from_maximum=1.,
                   components=1):
    with open(filename, "w") as fp:
        fp.write("Version 1\n")
        fp.write("From %f %f\n" % (from_minimum, from_maximum))
        fp.write("Length %d\n" % len(list(values)))
        fp.write("Components %d\n" % components)
        fp.write("{\n")
        for value in values:
            fp.write("{0:8}{1:2.14E}\n".format("", value))
        fp.write("}\n")


def OCIOWriteConfig(subdirectory, config, prefix=None):
    try:
        config.sanityCheck()

        currentDirectory = os.path.relpath(".")

        if prefix is None:
            filename = "config.ocio"
        else:
            filename = str(prefix) + "_config.ocio"

        destinationFile = (currentDirectory + "/" + subdirectory + "/" +
                           filename)

        if not os.path.exists(os.path.dirname(destinationFile)):
            os.makedirs(os.path.dirname(destinationFile))

        print(destinationFile)
        with open(destinationFile, mode='w') as fp:
            fp.write(config.serialize())

    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
