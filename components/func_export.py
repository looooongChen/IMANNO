from .enumDef import *
import h5py
from PIL import Image
import numpy as np
import math
import cv2

## exprot mask
def export_mask(anno_path, img_path, save_as_one=True):

    supported_type = [POLYGON]

    with h5py.File(anno_path, 'r') as location:
        
        image = Image.open(img_path)
        width, height = image.size
        
        if save_as_one:
            mask = np.zeros((height, width), np.uint16)
        else:
            mask = []
            mask_tmp = np.zeros((height, width), np.uint8)

        count = 0
        if 'annotations' in location.keys():
            for timestamp in location['annotations']:
                anno = location['annotations'][timestamp]

                if anno.attrs['type'] not in supported_type:
                    print("Mask export: only " + str(supported_type) + " are supported.")
                    continue

                # plot objects
                if anno.attrs['type'] == POLYGON:
                    count += 1
                    bbx = anno['boundingBox']
                    pts = np.stack([anno['polygon'][:,0]+bbx[0], anno['polygon'][:,1]+bbx[1]], axis=1)
                    pts = np.expand_dims(pts, 0)
                    if save_as_one:
                        cv2.fillPoly(mask, pts.astype(np.int32), count)
                    else:
                        mask_tmp = mask_tmp * 0
                        cv2.fillPoly(mask_tmp, pts.astype(np.int32), 255)
                        mask.append(mask_tmp.copy())

        is_empty = count == 0

    return mask, is_empty

def export_bbx(hdf5_path, img_path, export_property=None):

    annoList = []
    supported_type = [POLYGON, BBX]

    if export_property == '':
        export_property = None

    with h5py.File(hdf5_path, 'r') as location:
        
        count = 0
        if 'annotations' in location.keys():
            for timestamp in location['annotations']:
                anno = location['annotations'][timestamp]
                
                if anno.attrs['type'] not in supported_type:
                    print("BBX export: only " + str(supported_type) + " are supported.")
                    continue

                label_name = 'none'
                if export_property is not None:
                    if 'labels' in anno.keys():
                        for attr_name in anno['labels'].keys():
                            if attr_name == export_property:
                                label_name = anno['labels'][attr_name].attrs['label_name']

                bbx = anno['boundingBox']
                annoList.append({'name': label_name, 'bndbox': (bbx[0], bbx[1], bbx[0]+bbx[2], bbx[1]+bbx[3])})
                count += 1
    
    is_empty = count == 0

    return annoList, is_empty

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

    for dict in AnnoList:

        nodeObject = doc.createElement('object')

        nodeName = doc.createElement('name')
        nodeName.appendChild(doc.createTextNode(str(dict['name'])))

        nodeBndbox = doc.createElement('bndbox')

        nodeXmin = doc.createElement('xmin')
        nodeXmin.appendChild(doc.createTextNode(str(int(dict['bndbox'][0]))))

        nodeYmin = doc.createElement('ymin')
        nodeYmin.appendChild(doc.createTextNode(str(int(dict['bndbox'][1]))))

        nodeXmax = doc.createElement('xmax')
        nodeXmax.appendChild(doc.createTextNode(str(int(dict['bndbox'][2]))))

        nodeYmax = doc.createElement('ymax')
        nodeYmax.appendChild(doc.createTextNode(str(int(dict['bndbox'][3]))))

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

def extract_patch(hdf5_path, img_path, padding=0):

    supported_type = [POLYGON, BBX]

    if padding < 0:
        print("negative padding value, reset to 0")
        padding = 0

    with h5py.File(hdf5_path, 'r') as location:
        image = Image.open(img_path)

        patches_img, patches_mask = [], []
        if 'annotations' in location.keys():
            for timestamp in location['annotations']:
                anno = location['annotations'][timestamp]
                if anno.attrs['type'] not in supported_type:
                    print("Patch export: only " + str(supported_type) + " are supported.")
                    continue

                # extract patches
                bbx = anno['boundingBox']
                x, y, w, h = bbx[0], bbx[1], bbx[2], bbx[3] 
                padding_w, padding_h = round(w*padding), round(h*padding)
                Xmin, Xmax = int(math.floor(max(x-padding_w, 0))), int(math.ceil(min(x+w+1+padding_w, image.width)))
                Ymin, Ymax = int(math.floor(max(y-padding_h, 0))), int(math.ceil(min(y+h+1+padding_h, image.height)))
                offset_x, offset_y = x - Xmin, y - Ymin
                image_patch = image.crop((Xmin, Ymin, Xmax, Ymax))
                # image_patch = np.array(image)[Ymin:Ymax, Xmin:Xmax]

                mask_patch = None
                if anno.attrs['type'] == POLYGON:
                    mask_patch = np.zeros((image_patch.height, image_patch.width), np.uint8)
                    pts = np.stack([anno['polygon'][:,0]+offset_x, anno['polygon'][:,1]+offset_y], axis=1)
                    pts = np.expand_dims(pts, 0)
                    cv2.fillPoly(mask_patch, pts.astype(np.int32), 255)
                
                patches_img.append(image_patch)
                patches_mask.append(mask_patch)
                
    return patches_img, patches_mask

def export_skeleton(hdf5_path, img_path):

    supported_type = [POLYGON]

    with h5py.File(hdf5_path, 'r') as location:
        
        image = Image.open(img_path)
        width, height = image.size

        mask = np.zeros((height, width), np.uint16)
        skeleton = mask.copy()

        count = 0
        if 'annotations' in location.keys():
            for timestamp in location['annotations']:
                anno = location['annotations'][timestamp]

                if anno.attrs['type'] not in supported_type:
                    print("Skeleton export: only " + str(supported_type) + " are supported.")
                    continue

                bbx = anno['boundingBox']
                pts = np.stack([anno['polygon'][:,0]+bbx[0], anno['polygon'][:,1]+bbx[1]], axis=1)
                pts = np.expand_dims(pts, 0)
                mask = mask * 0
                cv2.fillPoly(mask, pts.astype(np.int32), 255)

                skel = sekeleton_erosion(mask)
                skel = thinning(skel)

                # skel = remove_islolated_pixels(skel)

                count += 1
                skel = (skel>0).astype(np.uint8)
                skeleton = np.where(skel > 0, count*skel, skeleton)
                
    is_empty = count == 0
    return skeleton, is_empty


def thinning(mask):
    # print(skeleton.shape, skeleton.dtype)
    mask = (mask > 0).astype(np.uint8)
    kernels = []
    K1 = np.array(([-1, -1, -1], [0, 1, 0], [1, 1, 1]), dtype="int")
    K2 = np.array(([0, -1, -1], [1, 1, -1], [0, 1, 0]), dtype="int")
    kernels.append(K1)
    kernels.append(K2)
    kernels.append(np.rot90(K1, k=1))
    kernels.append(np.rot90(K2, k=1))
    kernels.append(np.rot90(K1, k=2))
    kernels.append(np.rot90(K2, k=2))
    kernels.append(np.rot90(K1, k=3))
    kernels.append(np.rot90(K2, k=3))

    done = False
    while not done:
        new = np.copy(mask)
        for k in kernels:
            new = new - cv2.morphologyEx(new, cv2.MORPH_HITMISS, k)
        done = np.array_equal(new, mask)
        mask = new
    
    return mask

def sekeleton_erosion(mask):

    size = np.size(mask)
    skel = np.zeros((mask.shape[0], mask.shape[1]), np.uint8)
    _, mask = cv2.threshold(mask,127,255,cv2.THRESH_BINARY)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
    done = False
    
    while( not done):
        eroded = cv2.erode(mask,element)
        temp = cv2.dilate(eroded,element)
        temp = cv2.subtract(mask,temp)
        skel = np.bitwise_or(skel,temp)
        mask = eroded.copy()
    
        zeros = size - cv2.countNonZero(mask)
        if zeros==size:
            done = True
    
    return skel