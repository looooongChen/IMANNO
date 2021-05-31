from .enumDef import *
from PIL import Image
import numpy as np
import math
import cv2
from .func_annotation import anno_read


def export_mask(anno_path, img_path, export_labels=None, save_as_one=True):

    anno_file = anno_read(anno_path)
    image = Image.open(img_path)
    width, height = image.size
    if save_as_one:
        mask = np.zeros((height, width), np.uint16)
    else:
        mask_tmp = np.zeros((height, width), np.uint8)
        mask = []
    if export_labels is not None:
        label_lookup = {}
        for p, lbs in export_labels.items():
            for lb in lbs:
                label_lookup[p+'-'+lb] = 1  

    count = 0
    for _, anno in anno_file['annotations'].items(): 
        anno_type = anno['type']

        if anno_type == POLYGON:

            if export_labels is None:
                export = True
            else:
                export = False
                for p, lb in anno['labels'].items():
                    if p+'-'+lb in label_lookup.keys():
                        export = True
                        break
            if export:
                count += 1
                pts = np.expand_dims(np.array(anno['coords']), 0)
                if save_as_one:
                    cv2.fillPoly(mask, pts.astype(np.int32), count)
                else:
                    mask_tmp = mask_tmp * 0
                    cv2.fillPoly(mask_tmp, pts.astype(np.int32), 255)
                    mask.append(mask_tmp.copy())
        else:
            print('Mask Export: ' + anno_type + ' not supported')
    
    return mask, count == 0

def export_semantic(anno_path, img_path, category, labels, export_undefined=False, save_as_one=True):

    if export_undefined:
        lb_undefined = max(list(labels.values())) + 1 

    anno_file = anno_read(anno_path)
    image = Image.open(img_path)
    width, height = image.size
    if save_as_one:
        mask = np.zeros((height, width), np.uint8)
    else:
        mask_tmp = np.zeros((height, width), np.uint8)
        mask = []

    count = 0
    for _, anno in anno_file['annotations'].items(): 
        anno_type = anno['type']

        if anno_type == POLYGON:

            if export_undefined:
                export = True
                lb = lb_undefined
            else:
                export = False

            if category in anno['labels']:
                if anno['labels'][category] in labels.keys():
                    export = True
                    lb = labels[anno['labels'][category]]
            
            if export:
                count += 1
                pts = np.expand_dims(np.array(anno['coords']), 0)
                if save_as_one:
                    cv2.fillPoly(mask, pts.astype(np.int32), lb)
                else:
                    mask_tmp = mask_tmp * 0
                    cv2.fillPoly(mask_tmp, pts.astype(np.int32), lb)
                    mask.append(mask_tmp.copy())
        else:
            print('Mask Export: ' + anno_type + ' not supported')

    
    return mask, count == 0


def export_bbx(anno_path, img_path, category=None, labels={}, export_undefined=False):

    anno_file = anno_read(anno_path)
    annoList = []

    count = 0
    for _, anno in anno_file['annotations'].items(): 

        if 'bbx' in anno.keys():
            if export_undefined:
                export = True
                lb = 'none'
            else:
                export = False

            if category in anno['labels']:
                if anno['labels'][category] in labels.keys():
                    export = True
                    lb = anno['labels'][category]
            
            if export:
                count += 1
                bbx = anno['bbx']
                annoList.append({'name': lb, 'bndbox': (bbx[0], bbx[1], bbx[0]+bbx[2], bbx[1]+bbx[3])})
        else:
            print('Bounding Box Export: ' + anno['type'] + ' not supported')     
    
    return annoList, count == 0


def createXml(AnnoList, img_path, save_name):
    """
    :param AnnoList: include 'name' and 'bndbox'.
    e.g:
    AnnoList = [
    {'name': 'test', 'bndbox': ('xmin', 'ymin', 'xmax', 'ymax')},
    {'name': 'test2', 'bndbox': ('xmin', 'ymin2', 'xmax', 'ymax')}
    ]
    """
    import xml.dom.minidom

    doc = xml.dom.minidom.Document()
    root = doc.createElement('annotation')
    doc.appendChild(root)
    
    # file info
    imgName = doc.createElement('filename')
    img_name = os.path.basename(img_path)    
    imgName.appendChild(doc.createTextNode(img_name))
    root.appendChild(imgName)

    # image size
    # image = cv2.imread(img_path)
    image = Image.open(img_path)
    imgSize = doc.createElement('size')

    imgWidth = doc.createElement('width')
    imgWidth.appendChild(doc.createTextNode(str(image.width)))
    imgSize.appendChild(imgWidth)

    imgHeight = doc.createElement('height')
    imgHeight.appendChild(doc.createTextNode(str(image.height)))
    imgSize.appendChild(imgHeight)

    imgDepth = doc.createElement('depth')
    imgDepth.appendChild(doc.createTextNode(str(len(image.getbands()))))
    imgSize.appendChild(imgDepth)

    root.appendChild(imgSize)

    for anno_dict in AnnoList:

        nodeObject = doc.createElement('object')

        nodeName = doc.createElement('name')
        nodeName.appendChild(doc.createTextNode(str(anno_dict['name'])))

        nodeBndbox = doc.createElement('bndbox')

        nodeXmin = doc.createElement('xmin')
        nodeXmin.appendChild(doc.createTextNode(str(int(anno_dict['bndbox'][0]))))

        nodeYmin = doc.createElement('ymin')
        nodeYmin.appendChild(doc.createTextNode(str(int(anno_dict['bndbox'][1]))))

        nodeXmax = doc.createElement('xmax')
        nodeXmax.appendChild(doc.createTextNode(str(int(anno_dict['bndbox'][2]))))

        nodeYmax = doc.createElement('ymax')
        nodeYmax.appendChild(doc.createTextNode(str(int(anno_dict['bndbox'][3]))))

        nodeBndbox.appendChild(nodeXmin)
        nodeBndbox.appendChild(nodeYmin)
        nodeBndbox.appendChild(nodeXmax)
        nodeBndbox.appendChild(nodeYmax)

        nodeObject.appendChild(nodeName)
        nodeObject.appendChild(nodeBndbox)

        root.appendChild(nodeObject)

    fp = open(save_name, 'w')
    doc.writexml(fp, indent='\t', addindent='\t', newl='\n', encoding="utf-8")
    fp.close()


def extract_patch(anno_path, img_path, padding=0, export_labels=None):

    anno_file = anno_read(anno_path)
    image = Image.open(img_path)
    padding = 0 if padding < 0 else padding

    if export_labels is not None:
        label_lookup = {}
        for p, lbs in export_labels.items():
            for lb in lbs:
                label_lookup[p+'-'+lb] = 1  

    patches_img, patches_mask = [], []
    for _, anno in anno_file['annotations'].items():
        if 'bbx' in anno.keys():

            if export_labels is None:
                export = True
            else:
                export = False
                for p, lb in anno['labels'].items():
                    if p+'-'+lb in label_lookup.keys():
                        export = True
                        break

            if export: 
                # extract patches
                bbx = anno['bbx']
                x, y, w, h = bbx[0], bbx[1], bbx[2], bbx[3] 
                padding_w, padding_h = round(w*padding), round(h*padding)
                Xmin, Xmax = int(math.floor(max(x-padding_w, 0))), int(math.ceil(min(x+w+1+padding_w, image.width)))
                Ymin, Ymax = int(math.floor(max(y-padding_h, 0))), int(math.ceil(min(y+h+1+padding_h, image.height)))
                offset_x, offset_y = x - Xmin, y - Ymin
                image_patch = image.crop((Xmin, Ymin, Xmax, Ymax))

                mask_patch = None
                if anno['type'] == POLYGON:
                    mask_patch = np.zeros((image_patch.height, image_patch.width), np.uint8)
                    pts = np.array(anno['coords'])
                    pts[:,0] = pts[:,0] - Xmin 
                    pts[:,1] = pts[:,1] - Ymin 
                    pts = np.expand_dims(pts, 0)
                    cv2.fillPoly(mask_patch, pts.astype(np.int32), 255)
                
                patches_img.append(image_patch)
                patches_mask.append(mask_patch)
        else:
            print('Patch Export: ' + anno['type'] + ' not supported')     
                
    return patches_img, patches_mask

# def export_skeleton(anno_path, img_path, export_labels=None):

#     supported_type = [POLYGON]

#     anno_file = anno_read(anno_path)
#     image = Image.open(img_path)
#     width, height = image.size
#     skeleton = np.zeros((height, width), np.uint16)
#     if export_labels is not None:
#         label_lookup = {}
#         for p, lbs in export_labels.items():
#             for lb in lbs:
#                 label_lookup[p+'-'+lb] = 1  

#     count = 0
#     for _, anno in anno_file['annotations'].items():
        
#         ske_tmp = skeleton.copy()
#         anno_type = anno['type']

#         if anno_type == POLYGON:

#             if export_labels is None:
#                 export = True
#             else:
#                 export = False
#                 for p, lb in anno['labels'].items():
#                     if p+'-'+lb in label_lookup.keys():
#                         export = True
#                         break
#             if export:
#                 count += 1

#                 pts = np.expand_dims(np.array(anno['coords']), 0)
#                 ske_tmp = ske_tmp * 0
#                 cv2.fillPoly(ske_tmp, pts.astype(np.int32), 255)

#                 ske_tmp = sekeleton_erosion(ske_tmp)
#                 ske_tmp = thinning(ske_tmp)

#                 # ske_tmp = remove_islolated_pixels(ske_tmp)

#                 ske_tmp = (ske_tmp>0).astype(np.uint8)
#                 skeleton = np.where(ske_tmp > 0, count*ske_tmp, skeleton)
                
#         else:
#             print('Mask Export: ' + anno_type + ' not supported')

#     is_empty = count == 0
#     return (skeleton*30).astype(np.uint8), is_empty


# def thinning(mask):
#     # print(skeleton.shape, skeleton.dtype)
#     mask = (mask > 0).astype(np.uint8)
#     kernels = []
#     K1 = np.array(([-1, -1, -1], [0, 1, 0], [1, 1, 1]), dtype="int")
#     K2 = np.array(([0, -1, -1], [1, 1, -1], [0, 1, 0]), dtype="int")
#     kernels.append(K1)
#     kernels.append(K2)
#     kernels.append(np.rot90(K1, k=1))
#     kernels.append(np.rot90(K2, k=1))
#     kernels.append(np.rot90(K1, k=2))
#     kernels.append(np.rot90(K2, k=2))
#     kernels.append(np.rot90(K1, k=3))
#     kernels.append(np.rot90(K2, k=3))

#     done = False
#     while not done:
#         new = np.copy(mask)
#         for k in kernels:
#             new = new - cv2.morphologyEx(new, cv2.MORPH_HITMISS, k)
#         done = np.array_equal(new, mask)
#         mask = new
    
#     return mask

# def sekeleton_erosion(mask):

#     size = np.size(mask)
#     skel = np.zeros((mask.shape[0], mask.shape[1]), np.uint8)
#     _, mask = cv2.threshold(mask,127,255,cv2.THRESH_BINARY)
#     element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
#     done = False
    
#     while( not done):
#         eroded = cv2.erode(mask,element)
#         temp = cv2.dilate(eroded,element)
#         temp = cv2.subtract(mask,temp)
#         skel = np.bitwise_or(skel,temp)
#         mask = eroded.copy()
    
#         zeros = size - cv2.countNonZero(mask)
#         if zeros==size:
#             done = True
    
#     return skel