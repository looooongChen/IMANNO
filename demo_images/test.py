import numpy as np
from imantics import Polygons, Mask
import cv2

# This can be any array
im = cv2.imread('cells_mask.png')

polygons = Mask(im).polygons()

print(polygons.points)
print(polygons.segmentation)