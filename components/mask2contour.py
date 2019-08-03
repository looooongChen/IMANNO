import cv2
import numpy as np

def mask2contour(img):
    """
    Input:  Single channel uint8 image
    Ouput:  Contour list, non-approximated
    Step:   Unconnect adjacent cell masks then use cv2.findContours
    """
    img_dilate = cv2.dilate(img, np.ones((3,3),np.uint8), iterations=1)
    img_unconnected = np.where(img==0, 0, 255).astype('uint8')
    img_unconnected = np.where(img_dilate-img != 0, 0, img_unconnected).astype('uint8')

    _, contours, _ = cv2.findContours(img_unconnected, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    print(len(contours), 'contours found!')

    return contours
