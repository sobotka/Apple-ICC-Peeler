#!/usr/bin/env python
# -*- coding: utf-8 -*-
import colour
import array
import sys
import struct
import numpy
import PyOpenColorIO


def fs15f16(x):
    """Convert float to ICC s15Fixed16Number (as a Python ``int``)."""
    return int(round(x * 2**16))


def s15f16l(s):
    """Convert sequence of ICC s15Fixed16 to list of float."""
    n = len(s)//4
    t = struct.unpack('>%dl' % n, s)
    return map((2**-16).__mul__, t)


tags = ["chad", "wtpt", "rXYZ", "gXYZ", "bXYZ", "PCSXYZ"]

variables = {
    "wtpt_headerpos": None, "wtpt_offset": None, "wtpt_size": None,
    "rXYZ_headerpos": None, "rXYZ_offset": None, "rXYZ_size": None,
    "gXYZ_headerpos": None, "gXYZ_offset": None, "gXYZ_size": None,
    "bXYZ_headerpos": None, "bXYZ_offset": None, "bXYZ_size": None,
    "chad_headerpos": None, "chad_offset": None, "chad_size": None,
    "PCSXYZ_headerpos": None, "PCSXYZ_offset": None, "PCSXYZ_size": None,
    "wtpt": None, "rXYZ": None, "gXYZ": None, "bXYZ": None, "PCSXYZ": None,
    "chad": None, "D50XYZ": None, "D50XYZ_OCIO": None
    }

if __name__ == "__main__":
    try:
        numpy.set_printoptions(15)

        with open(sys.argv[1], 'rb') as f:
            s = f.read()

            # Test to see if it is an ICC / ICM file. Must contain the "acsp"
            # tag at position 36 to 39
            isicc = s[36:40]
            if isicc != b"acsp":
                raise ValueError("file doesn't appear to be a valid ICC / ICM")

            # Grab the Profile Connection Space illuminant at position 60 to
            # 79. This should alway be ICC D50, but for the sake of getting
            # the most accurate round trip values for non ICC D50 illuminants,
            # it is important to use the values included in this region.

            for tag in tags:
                # The initial values are set to the offset in ICC / ICM files
                # for each of the PCS XYZ chromaticities. Use this, and convert
                # found value to its decimal representaion and store in the
                # dictionary at the same position.
                if (tag is "PCSXYZ"):
                    variables[tag + "_headerpos"] = 68
                    variables[tag + "_offset"] = 68
                    variables[tag + "_size"] = 12
                else:
                    variables[tag + "_headerpos"] = s.index(
                        bytes(tag, "utf-8"))
                    variables[tag + "_offset"] = int.from_bytes(
                        s[variables[tag + "_headerpos"] + 4:
                          variables[tag + "_headerpos"] + 8],
                        byteorder="big"
                    ) + 8
                    variables[tag + "_size"] = int.from_bytes(
                        s[variables[tag + "_headerpos"] + 8:
                          variables[tag + "_headerpos"] + 12],
                        byteorder="big"
                    ) - 8
                variables[tag] = list(
                    s15f16l(
                        s[variables[tag + "_offset"]:
                          variables[tag + "_offset"] +
                          variables[tag + "_size"]]
                    )
                )

            # Shape the chad tag into a proper matrix for use.
            variables["chad"] = numpy.reshape(variables["chad"], (3, 3))

            # Shape the Apple D50 RGB to XYZ transform into a proper form
            # for matrices.
            variables["D50XYZ"] = numpy.transpose(
                [variables["rXYZ"], variables["gXYZ"], variables["bXYZ"]]
            )

            # Shape the Apple D50 RGB to XYZ transform into a proper form
            # for OCIO, which has slots for offsets, as well as flatten it
            # for ingestion into the OCIO MatricTransform function.
            addlrow = [0., 0., 0.]
            addlcol = [[0.], [0.], [0.], [1.]]

            variables["D50XYZ_OCIO"] = numpy.vstack(
                [variables["D50XYZ"], addlrow])
            variables["D50XYZ_OCIO"] = numpy.hstack(
                [variables["D50XYZ_OCIO"], addlcol])
            variables["D50XYZ_OCIO"] = numpy.asarray(
                variables["D50XYZ_OCIO"]).flatten()

            print(variables)

            # Perform test. Convert a D65 sRGB value to D50 Apple P3.

            AppleCATD50toD65 = numpy.asarray(variables["chad"])
            AppleP3_D50RGB_to_XYZ = numpy.asarray(variables["D50XYZ"])
            AppleP3_D65RGB_to_XYZ = numpy.matmul(
                numpy.linalg.inv(AppleCATD50toD65),
                AppleP3_D50RGB_to_XYZ
            )

            AppleWhite50XYZ = numpy.matmul(variables["D50XYZ"], [1., 1., 1.])

            print("AppleWhite50 xyY:\n" + str(colour.XYZ_to_xyY(
                AppleWhite50XYZ, [0.3127, 0.3290])) + ", XYZ: " +
                str(AppleWhite50XYZ))

            colour_AppleCATD50toD65 = (
                colour.adaptation.chromatic_adaptation_matrix_VonKries(
                    AppleWhite50XYZ,
                    colour.xyY_to_XYZ([0.3127, 0.3290, 1.]),
                    transform=u"Bradford"
                )
            )
            print("Apple D50 to D65 CAT:\n" + str(colour_AppleCATD50toD65))

            sRGB = colour.models.sRGB_COLOURSPACE
            sRGB.use_derived_RGB_to_XYZ_matrix = True
            sRGB.use_derived_XYZ_to_RGB_matrix = True

            print("sRGB derived:\n" + str(sRGB.RGB_to_XYZ_matrix))

            AppleWhiteTestD50toD65XYZ = numpy.matmul(
                colour_AppleCATD50toD65,
                AppleWhite50XYZ
                )
            sRGBfromApple50XYZ = numpy.matmul(
                sRGB.XYZ_to_RGB_matrix,
                AppleWhiteTestD50toD65XYZ
            )

            print("Round trip Apple D50 white to sRGB white:\n" +
                  str(sRGBfromApple50XYZ))

            sRGBRGBtoXYZ = sRGB.RGB_to_XYZ_matrix

            # Shape the CAT matrix for OCIO.
            addlrow = [0., 0., 0.]
            addlcol = [[0.], [0.], [0.], [1.]]

            ocio_AppleCATD50toD65 = numpy.vstack(
                [colour_AppleCATD50toD65, addlrow])
            ocio_AppleCATD50toD65 = numpy.hstack(
                [ocio_AppleCATD50toD65, addlcol])
            ocio_AppleCATD50toD65 = numpy.asarray(
                ocio_AppleCATD50toD65).flatten()

            print(str(ocio_AppleCATD50toD65))
            # Shape the AppleP3 D50 RGB to XYZ transform.
            ocio_AppleD50RGBtoXYZ = numpy.vstack(
                [variables["D50XYZ"], addlrow])
            ocio_AppleD50RGBtoXYZ = numpy.hstack(
                [ocio_AppleD50RGBtoXYZ, addlcol])
            ocio_AppleD50RGBtoXYZ = numpy.asarray(
                ocio_AppleD50RGBtoXYZ).flatten()

            # Shape the sRGB derived matrix.
            ocio_sRGBRGBtoXYZ = numpy.vstack(
                [sRGBRGBtoXYZ, addlrow])
            ocio_sRGBRGBtoXYZ = numpy.hstack(
                [ocio_sRGBRGBtoXYZ, addlcol])
            ocio_sRGBRGBtoXYZ = numpy.asarray(
                ocio_sRGBRGBtoXYZ).flatten()

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
                ocio_AppleD50RGBtoXYZ
            )
            transform_sRGBRGBtoXYZ = PyOpenColorIO.MatrixTransform(
                ocio_sRGBRGBtoXYZ
            )

            transform_sRGBRGBtoXYZ.setDirection(
                PyOpenColorIO.Constants.TRANSFORM_DIR_INVERSE
            )

            transform_AppleCATD50toD65 = PyOpenColorIO.MatrixTransform(
                ocio_AppleCATD50toD65
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
            with open("config.ocio", mode='w') as fp:
                fp.write(config.serialize())

    except FileNotFoundError as e:
        print("Unable to find file. Error:", e)
    except ValueError as e:
        print("Unable to find necessary ICC tags in file. Error:", e)
        raise
    except IndexError as e:
        print("Unable to open the file specified. Error:", e)
    except Exception as e:
        raise
