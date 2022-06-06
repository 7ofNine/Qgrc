import logging

from PyQt6 import QtCore

from ...Constants import POSSIBLE_ROTATIONS

log = logging.getLogger(__name__)

def get_rotated_coordinate(coor, rotation):
    """
    Rotate the coordinate by the given rotation.
    Args:
        coor: the coordinate x, y tuple
        rotation: the angle in degrees
    Returns:
        the rotated coordinates
    """
    # handles negative angles
    rotation = (rotation + 360) % 360
    if rotation not in POSSIBLE_ROTATIONS:
        raise ValueError('unusable rotation angle "%s"'%str(rotation))
    # determine the number of degrees to rotate
    cos_r, sin_r = {
        0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1),
    }[rotation]
    x, y = coor.x(), coor.y()
    return QtCore.QPointF(x * cos_r - y * sin_r, x * sin_r + y * cos_r)    # Be aware. This is specific to the connection and how the points there are calculated independently of the block rotation
                                                                           # which means we actually have to use the negative values for counterclock wise and this changes the signum of the sin functions. 
                                                                           # SHould find a way to do this in the same method by connecting these points to the block and let the scene do the job!