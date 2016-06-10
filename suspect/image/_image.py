from suspect import transformation_matrix

import numpy
import os
import pydicom


def load_dicom_volume(filename):
    # load the supplied file and get the UID of the series
    ds = pydicom.read_file(filename)
    seriesUID = ds.SeriesInstanceUID

    # get the position of the image
    position = numpy.array(list(map(float, ds.ImagePositionPatient)))

    # get the direction normal to the plane of the image
    row_vector = numpy.array(ds.ImageOrientationPatient[:3])
    col_vector = numpy.array(ds.ImageOrientationPatient[3:])
    normal_vector = numpy.cross(row_vector, col_vector)

    # we order slices by their distance along the normal
    def normal_distance(coords):
        return numpy.dot(normal_vector, coords)

    # create a dictionary to hold the slices as we load them
    slices = {normal_distance(position): ds.pixel_array}

    # extract the path to the folder of the file so we can look for others from the same series
    folder, _ = os.path.split(filename)
    for name in os.listdir(folder):
        if name.lower().endswith(".ima") or name.lower().endswith(".dcm"):
            new_dicom_name = os.path.join(folder, name)
            new_ds = pydicom.read_file(new_dicom_name)

            # check that the series UID matches
            if new_ds.SeriesInstanceUID == seriesUID:
                if new_ds.pixel_array.shape != ds.pixel_array.shape:
                    continue
                new_position = list(map(float, new_ds.ImagePositionPatient))
                slices[normal_distance(new_position)] = new_ds.pixel_array

                # we set the overall position of the volume with the position
                # of the lowest slice
                if normal_distance(new_position) < normal_distance(position):
                    position = new_position

    # that is all the slices in the folder, assemble them into a 3d volume
    voxel_array = numpy.zeros((len(slices),
                               ds.pixel_array.shape[0],
                               ds.pixel_array.shape[1]), dtype=numpy.float)
    sorted_slice_positions = sorted(slices.keys())
    for i, slice_position in enumerate(sorted_slice_positions):
        voxel_array[i] = slices[slice_position]

    # the voxel spacing is a combination of PixelSpacing and slice separation
    voxel_spacing = list(map(float, ds.PixelSpacing))
    voxel_spacing.append(sorted_slice_positions[1] - sorted_slice_positions[0])

    # replace the initial slice z position with the lowest slice z position
    # position[2] = sorted_slice_positions[0]

    transform = transformation_matrix(row_vector,
                                      col_vector,
                                      position,
                                      voxel_spacing)

    return {
        "voxel_spacing": voxel_spacing,
        "position": position,
        "volume": voxel_array,
        "vectors": [row_vector, col_vector, normal_vector],
        "transform": transform
    }