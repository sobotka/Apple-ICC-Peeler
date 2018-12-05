#!/usr/bin/env python
# -*- coding: utf-8 -*-
import colour
import array
import sys
import struct
import numpy
import PyOpenColorIO
from iccinspector import iccinspector
import argparse


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(
            prog='Apple ICC Peeler'
        )
        parser.add_argument(
            "iccfile",
            type=argparse.FileType("rb")
        )

        parser.add_argument(
            "configfile",
            type=argparse.FileType("w")
        )

        args = parser.parse_args()

        numpy.set_printoptions(15)

        with args.iccfile as f:
            s = memoryview(f.read())

            iccFile = iccinspector.iccProfile()
            iccFile.read(s)
            
            chad = iccFile.tags["tag"][
                numpy.where(iccFile.tags["signature"] == "chad")
            ][0]

            CATD50toD65 = numpy.reshape(chad.type.value, (3, 3))

            rXYZ = iccFile.tags["tag"][
                numpy.where(iccFile.tags["signature"] == "rXYZ")
            ][0]
            gXYZ = iccFile.tags["tag"][
                numpy.where(iccFile.tags["signature"] == "gXYZ")
            ][0]
            bXYZ = iccFile.tags["tag"][
                numpy.where(iccFile.tags["signature"] == "bXYZ")
            ][0]

            AppleP3D50toXYZ = numpy.transpose(
                [
                    rXYZ.type.value[0].XYZ,
                    gXYZ.type.value[0].XYZ,
                    bXYZ.type.value[0].XYZ
                ]
            )

            sRGB = colour.models.sRGB_COLOURSPACE
            sRGB.use_derived_RGB_to_XYZ_matrix = True
            sRGB.use_derived_XYZ_to_RGB_matrix = True

            sRGBtoXYZ = sRGB.RGB_to_XYZ_matrix

            # Shape the RGB to XYZ array for OpenColorIO
            OCIOAppleP3D50toD65 = numpy.pad(
                AppleP3D50toXYZ,
                [(0, 1), (0, 1)],
                mode='constant'
            )
            OCIOAppleP3D50toD65 = OCIOAppleP3D50toD65.flatten()
            OCIOAppleP3D50toD65[-1] = 1.

            # Shape the adaptation array for OpenColorIO
            OCIOCATD50toD65 = numpy.pad(
                CATD50toD65,
                [(0, 1), (0, 1)],
                mode='constant'
            )
            OCIOCATD50toD65 = OCIOCATD50toD65.flatten()
            OCIOCATD50toD65[-1] = 1.

            # Shape the sRGB to XYZ array for OpenColorIO
            OCIOsRGBtoD65 = numpy.pad(
                sRGBtoXYZ,
                [(0, 1), (0, 1)],
                mode='constant'
            )
            OCIOsRGBtoD65 = OCIOsRGBtoD65.flatten()
            OCIOsRGBtoD65[-1] = 1.

        # Establish a boilerplate OCIO configuration. This won't work
        # as an actual configuration, but it will hold the transforms
        # for usage elsewhere.
        config = PyOpenColorIO.Config()
        colorspace = PyOpenColorIO.ColorSpace(family="display",
                                              name="Apple DCI-P3 D65")
        colorspace.setBitDepth(PyOpenColorIO.Constants.BIT_DEPTH_F32)
        colorspace.setAllocationVars([-12.473931188, 12.526068812])
        colorspace.setAllocation(PyOpenColorIO.Constants.ALLOCATION_LG2)

        transform_AppleD50RGBtoXYZ = PyOpenColorIO.MatrixTransform(
            OCIOAppleP3D50toD65
        )

        transform_AppleCATD50toD65 = PyOpenColorIO.MatrixTransform(
            OCIOCATD50toD65
        )

        transform_AppleCATD50toD65.setDirection(
            PyOpenColorIO.Constants.TRANSFORM_DIR_INVERSE
        )

        transform_sRGBRGBtoXYZ = PyOpenColorIO.MatrixTransform(
            OCIOsRGBtoD65
        )

        transform_sRGBRGBtoXYZ.setDirection(
            PyOpenColorIO.Constants.TRANSFORM_DIR_INVERSE
        )

        transform = PyOpenColorIO.GroupTransform()
        transform.setTransforms(
            [transform_AppleD50RGBtoXYZ,
             transform_AppleCATD50toD65,
             transform_sRGBRGBtoXYZ
             ]
        )

        colorspace.setTransform(
            transform,
            PyOpenColorIO.Constants.COLORSPACE_DIR_TO_REFERENCE
        )

        config.addColorSpace(colorspace)

        with args.configfile as fo:
            fo.write(config.serialize())

    except:
        raise