import pyclipper
import cv2
import numpy as np

def mask2contour(mask):
    morph_element = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    mask_ero = cv2.erode(mask, morph_element)
    mask_dil = cv2.dilate(mask, morph_element)
    mask = np.logical_and(mask_ero == mask_dil, mask > 0)
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    contours = [np.squeeze(np.array(c))for c in contours]
    contours = [np.squeeze(cv2.approxPolyDP(c, 0.7, True)) for c in contours]
    return contours

def match_contours(contour_query, contour_set):
    '''
    Args:
        contour_query: np.array of size Nx2 or [[x1,y1],[x2,y2]...]
        contour_set: np.array of size Nx2 or [[x1,y1],[x2,y2]...]
    '''
    match = np.zeros((len(contour_query), len(contour_set)))
    area_query = [cv2.contourArea(c) for c in contour_query]
    area_set = [cv2.contourArea(c) for c in contour_set]
    for idx_query, c_query in enumerate(contour_query):
        for idx_set, c_set in enumerate(contour_set):
            pc = pyclipper.Pyclipper()
            pc.AddPath(c_query, pyclipper.PT_CLIP, True)
            pc.AddPaths([c_set], pyclipper.PT_SUBJECT, True)

            contour_inter = pc.Execute(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
            if len(contour_inter) != 0:
                contour_inter = np.squeeze(np.array(contour_inter))
                match[idx_query, idx_set] = 2*cv2.contourArea(contour_inter)/(area_query[idx_query]+area_set[idx_set])
    return match

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import time

    gt = cv2.imread('./test/cell/gt/mcf-z-stacks-03212011_i01_s1_w14fc74585-6706-47ea-b84b-ed638d101ae8.png', cv2.IMREAD_UNCHANGED)
    pred = cv2.imread('./test/cell/pred/mcf-z-stacks-03212011_i01_s1_w14fc74585-6706-47ea-b84b-ed638d101ae8.tif', cv2.IMREAD_UNCHANGED)
    s = time.time()
    contours_gt = mask2contour(gt)
    contours_pred = mask2contour(pred)
    
    match = match_contours(contours_pred, contours_gt)
    score = np.max(match, axis=1) 
    print(score)
    print(len(score), len(contours_pred))
    print(time.time()-s)
        # break