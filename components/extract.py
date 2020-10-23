from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QProgressBar 
from PyQt5.Qt import QAbstractItemView
from PyQt5.QtCore import Qt
from .enumDef import *
from .fileList import FolderTreeItem, ImageTreeItem
import numpy as np
from datetime import datetime
import os
import h5py
import csv
import cv2
import shutil

IMAGE_FORMATS = [f[1:] for f in IMAGE_TYPES]


#################################
TP_MASK_SINGLE = "mask, single (.png, all objects in one image, may overlap)"
TP_MASK_MULTI = "mask, multiple (.png, one mask for each object)"
TP_BBX = "boundingbox (.xml, PASCAL VOC format)"
TP_PATCH = "patches (.png)"
TP_SKELETON = "skeleton (.png)"

class AnnoExporter(QDialog):
    def __init__(self, project=None, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/annoExporter.ui', baseinstance=self)
        self.setWindowTitle("Export annotations")
        self.project = project
        
        self.btnSelect.clicked.connect(self.select)
        self.btnSelectAll.clicked.connect(self.select_all)
        self.btnExport.clicked.connect(self.export)
        self.exportType.currentTextChanged.connect(self.update_ui)
        
        self.exportType.addItem(TP_MASK_SINGLE)
        self.exportType.addItem(TP_MASK_MULTI)
        self.exportType.addItem(TP_BBX)
        self.exportType.addItem(TP_PATCH)
        self.exportType.addItem(TP_SKELETON)

        # init file list
        self.fileList.setColumnCount(1)
        self.fileList.setHeaderHidden(True)
        self.fileList.setIndentation(20)
        self.fileList.setRootIsDecorated(False)
        self.fileList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        # self.fileList.itemChanged.connect(self.on_item_change, Qt.QueuedConnection)
        self.fileList.itemChanged.connect(self.on_item_change)

        self.progressBar.setValue(0)
        self.valuePadding.setMinimum(0)
        self.valuePadding.setMaximum(100)
        self.valuePadding.setSingleStep(1)
        self.valuePadding.setValue(10)

    def initial_list(self, fileList):
        fileList = fileList.fileList
        for i in range(fileList.topLevelItemCount()):
            item = fileList.topLevelItem(i)
            item_c = item.clone()
            item_c.setCheckState(0, Qt.Unchecked)
            self.fileList.addTopLevelItem(item_c)
            if isinstance(item, FolderTreeItem):
                for j in range(item.childCount()):
                    child_item = item.child(j).clone()
                    child_item.setCheckState(0, Qt.Unchecked)
                    item_c.addChild(child_item)
    
    def on_item_change(self, item, col):
        if isinstance(item, FolderTreeItem):
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, item.checkState(0))

    def select(self):
        if len(self.fileList.selectedItems()) > 0:
            status = self.fileList.selectedItems()[0].checkState(0)
            if status == Qt.Checked:
                status = Qt.Unchecked
            else:
                status = Qt.Checked

        for item in self.fileList.selectedItems():
            item.setCheckState(0, status)
    
    def select_all(self):
        if self.fileList.topLevelItemCount() > 0:
            status = self.fileList.topLevelItem(0).checkState(0)
            if status == Qt.Checked:
                status = Qt.Unchecked
            else:
                status = Qt.Checked

        for i in range(self.fileList.topLevelItemCount()):
            item = self.fileList.topLevelItem(i)
            item.setCheckState(0, status)

    def is_empty(self, location, types):

        if 'annotations' in location.keys():
            for timestamp in location['annotations']:
                anno = location['annotations'][timestamp]
                if anno.attrs['type'] in types:
                    return False
        return True

    def update_ui(self, text):
        text = str(text)
        self.valueProperty.setEnabled(False)
        self.valuePadding.setEnabled(False)
        self.ckIgnoreEmpty.setEnabled(True)
        self.ckIgnoreEmpty.setCheckState(Qt.Checked)
        if text == TP_PATCH:
            self.valuePadding.setEnabled(True)
            self.ckIgnoreEmpty.setEnabled(False)
        elif text == TP_BBX:
            self.valueProperty.setEnabled(True)

    def export(self):
        self.progressBar.setValue(0)
        
        save_dir = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if len(save_dir) != 0:
            now = datetime.now()
            save_dir = os.path.join(save_dir, 'export-' + now.strftime("%Y-%b-%d-%H:%M:%S"))
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            # get selected items
            items = []
            for i in range(self.fileList.topLevelItemCount()):
                item = self.fileList.topLevelItem(i)
                if isinstance(item, FolderTreeItem):
                    for j in range(item.childCount()):
                        child_item = item.child(j)
                        if child_item.checkState(0) == Qt.Checked:
                            items.append(child_item)
                else:
                    if item.checkState(0) == Qt.Checked:
                        items.append(item)
            # get valid images and annotations
            images, annotations = [], []
            if self.project.is_open():
                for item in items:
                    idx = item.idx
                    image_path = self.project.get_image_path(idx)
                    annotation_path = self.project.get_annotation_path(idx)
                    if os.path.exists(image_path) and os.path.exists(annotation_path):
                        images.append(image_path)
                        annotations.append(annotation_path)
            else:
                for item in itmes:
                    image_path = item.path
                    annotation_path = os.path.splitext(image_path)[0] + '.' + ANNOTATION_EXT
                    if os.path.exists(image_path) and os.path.exists(annotation_path):
                        images.append(image_path)
                        annotations.append(annotation_path)
            # export annotations and the list
            total = len(images)
            with open(os.path.join(save_dir, 'files.csv'), mode='w') as files:
                file_writer = csv.writer(files, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for idx, img, ann in zip(list(range(total)), images, annotations):

                # employee_writer.writerow(['John Smith', 'Accounting', 'November'])
                # employee_writer.writerow(['Erica Meyers', 'IT', 'March'])

        samples = {}
        for f in os.listdir(self.source_dir):
            path = os.path.join(self.source_dir, f)
            if os.path.isdir(path):
                continue
            filename, ext = os.path.splitext(path)
            if ext not in IMAGE_FORMATS:
                continue
            if os.path.exists(filename + '.hdf5'):
                samples[path] = filename + '.hdf5'

        if not os.path.exists(os.path.join(self.dest_dir, 'ground_truth')):
            os.makedirs(os.path.join(self.dest_dir, 'ground_truth'))
        if self.ui.copy_image.checkState() == Qt.Checked and not os.path.exists(os.path.join(self.dest_dir, 'image')):
            os.makedirs(os.path.join(self.dest_dir, 'image'))
        
        image_index = 1
        total = len(samples)
        for img_path, hdf5_path in samples.items():
            type = str(self.ui.type.currentText())
            if type == TP_MASK_SINGLE:
                self.export_mask(hdf5_path, img_path, save_as_one=True)
            elif type == TP_MASK_MULTI:
                self.export_mask(hdf5_path, img_path, save_as_one=False)
            elif type == TP_BBX:
                self.export_bbx(hdf5_path, img_path)
            elif type == TP_PATCH:
                self.extract_patch(hdf5_path, img_path)
            elif type == TP_SKELETON:
                self.export_skeleton(hdf5_path, img_path)
            else:
                print("Unsupported output type")

            image_index += 1

            if int(self.count*100/self.total) - self.progressBar.value() >= 1:
                self.progressBar.setValue(self.count*100/self.total)

            if int(image_index*100/total) - self.ui.progress.value() >= 3:
                self.ui.progress.setValue(int(image_index*100/total))
        self.ui.progress.setValue(100)    

    def export_mask(self, hdf5_path, img_path, save_as_one=True):

        supported_type = [POLYGON]

        with h5py.File(hdf5_path, 'r') as location:
            
            if self.ui.ignore_empty.checkState() == Qt.Checked and self.is_empty(location, supported_type):
                print("Skip empty image: " + img_path)
                return
            else:
                image = cv2.imread(img_path)
                print("Process: " + img_path)
            
            if save_as_one:
                mask = np.zeros((image.shape[0], image.shape[1]), np.uint16)
            else:
                masks = []
                mask = np.zeros((image.shape[0], image.shape[1]), np.uint8)

            index = 0
            if 'annotations' in location.keys():
                for timestamp in location['annotations']:
                    anno = location['annotations'][timestamp]

                    type = anno.attrs['type']
                    if type not in supported_type:
                        print("Only" + str(supported_type) + " are supported.")
                        continue

                    # plot objects
                    if type == POLYGON:
                        # if len(anno['polygon'][:,0]) < 5:
                        #     continue
                        bbx = anno['boundingBox']
                        pts = np.stack([anno['polygon'][:,0]+bbx[0], anno['polygon'][:,1]+bbx[1]], axis=1)
                        pts = np.expand_dims(pts, 0)
                        if save_as_one:
                            cv2.fillPoly(mask, pts.astype(np.int32), index+1)
                        else:
                            mask = mask * 0
                            cv2.fillPoly(mask, pts.astype(np.int32), 255)
                            masks.append(mask.copy())
                        index += 1
                        
            fname = os.path.splitext(os.path.basename(img_path))[0]
            if save_as_one:
                mask = mask.astype(np.uint8) if index <= 255 else mask
                save_mask_as_png(os.path.join(self.dest_dir, 'ground_truth'), fname, mask)
            else:
                save_mask_as_png(os.path.join(self.dest_dir, 'ground_truth'), fname, masks)

            if self.ui.copy_image.checkState() == Qt.Checked:
                shutil.copy(img_path, os.path.join(self.dest_dir, 'image'))

    def export_bbx(self, hdf5_path, img_path):
        annoList = []
        supported_type = [POLYGON, BBX]

        with h5py.File(hdf5_path, 'r') as location:
            
            if self.ui.ignore_empty.checkState() == Qt.Checked and self.is_empty(location, supported_type):
                print("Skip empty image: " + img_path)
                return
            else:
                print("Process: " + img_path)

            export_property = str(self.ui.property.text()).strip()
            if export_property == '':
                export_property = None

            if 'annotations' in location.keys():
                for timestamp in location['annotations']:
                    anno = location['annotations'][timestamp]
                    
                    label_name = 'none'
                    if export_property is not None:
                        if 'labels' in anno.keys():
                            for attr_name in anno['labels'].keys():
                                if attr_name == export_property:
                                    label_name = anno['labels'][attr_name].attrs['label_name']

                    type = anno.attrs['type']
                    if type not in supported_type:
                        print("Only" + str(supported_type) + " are supported.")
                        continue

                    bbx = anno['boundingBox']
                    annoList.append({'name': label_name, 'bndbox': (bbx[0], bbx[1], bbx[0]+bbx[2], bbx[1]+bbx[3])})

            fname = os.path.splitext(os.path.basename(img_path))[0]
            save_path = os.path.join(os.path.join(self.dest_dir, 'ground_truth'), fname+'.xml')
            createXml(annoList, img_path, save_path)

            if self.ui.copy_image.checkState() == Qt.Checked:
                shutil.copy(img_path, os.path.join(self.dest_dir, 'image'))


    def extract_patch(self, hdf5_path, img_path):

            supported_type = [POLYGON, BBX]

            padding = float(self.ui.padding.text())
            padding = padding/100
            if padding < 0:
                print("negative padding value, reset to 0")
                padding = 0

            patch_index = 1
            with h5py.File(hdf5_path, 'r') as location:
                if self.is_empty(location, supported_type):
                    print("Skip empty image: " + img_path)
                    return
                else:
                    image = cv2.imread(img_path)
                    print("Process: " + img_path)

                if 'annotations' in location.keys():
                    for timestamp in location['annotations']:
                        anno = location['annotations'][timestamp]
                        type = anno.attrs['type']
                        if type not in supported_type:
                            print("Only" + str(supported_type) + " are supported.")
                            continue

                        # extract patches
                        bbx = anno['boundingBox']
                        x, y, w, h = bbx[0], bbx[1], bbx[2], bbx[3] 
                        sz = image.shape
                        padding_w = round(w*padding)
                        padding_h = round(h*padding)
                        Xmin, Xmax = int(max(x-1-padding_w, 0)), int(min(x+w+padding_w, sz[1]))
                        Ymin, Ymax = int(max(y-1-padding_h, 0)), int(min(y+h+padding_h, sz[0]))
                        image_patch = image[Ymin:Ymax, Xmin:Xmax]

                        mask_patch = None
                        if type == POLYGON:
                            # if len(anno['polygon'][:,0]) < 5:
                            #     return None, None
                            mask_patch = np.zeros((image_patch.shape[0], image_patch.shape[1]), np.uint8)
                            pts = np.stack([anno['polygon'][:,0]+padding_w, anno['polygon'][:,1]+padding_h], axis=1)
                            pts = np.expand_dims(pts, 0)
                            cv2.fillPoly(mask_patch, pts.astype(np.int32), 255)
                        
                        fname = os.path.splitext(os.path.basename(img_path))[0]
                        cv2.imwrite(os.path.join(os.path.join(self.dest_dir, 'image'), fname+"_patch_"+str(patch_index)+".png"), image_patch)
                        if mask_patch is not None:
                            cv2.imwrite(os.path.join(os.path.join(self.dest_dir, 'ground_truth'), fname+"_mask_"+str(patch_index)+".png"), mask_patch)
                        patch_index += 1


    def export_skeleton(self, hdf5_path, img_path):

            supported_type = [POLYGON]

            with h5py.File(hdf5_path, 'r') as location:
                
                if self.ui.ignore_empty.checkState() == Qt.Checked and self.is_empty(location, supported_type):
                    print("Skip empty image: " + img_path)
                    return
                else:
                    image = cv2.imread(img_path)
                    print("Process: " + img_path)

                mask = np.zeros((image.shape[0], image.shape[1]), np.uint16)
                skeleton = np.zeros((image.shape[0], image.shape[1]), np.uint16)

                if 'annotations' in location.keys():
                    index = 1
                    for timestamp in location['annotations']:
                        anno = location['annotations'][timestamp]

                        type = anno.attrs['type']
                        if type not in supported_type:
                            print("Only" + str(supported_type) + " are supported.")
                            continue

                        # if len(anno['polygon'][:,0]) < 5:
                        #     continue
                        bbx = anno['boundingBox']
                        pts = np.stack([anno['polygon'][:,0]+bbx[0], anno['polygon'][:,1]+bbx[1]], axis=1)
                        pts = np.expand_dims(pts, 0)
                        mask = mask * 0
                        cv2.fillPoly(mask, pts.astype(np.int32), 255)

                        if self.ui.single_pixel.checkState() == Qt.Checked:
                            skel = sekeleton_erosion(mask)
                            skel = thinning(skel)
                        else:
                            skel = sekeleton_erosion(mask)

                        # skel = remove_islolated_pixels(skel)

                        skel = (skel>0).astype(np.uint8)
                        skeleton = np.where(skel > 0, index*skel, skeleton)
                        
                        index += 1

                    skeleton = skeleton.astype(np.uint8) 

                fname = os.path.splitext(os.path.basename(img_path))[0]
                save_mask_as_png(os.path.join(self.dest_dir, 'ground_truth'), fname, skeleton)

                if self.ui.copy_image.checkState() == Qt.Checked:
                    shutil.copy(img_path, os.path.join(self.dest_dir, 'image'))


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


def save_mask_as_png(save_dir, fname, masks):

    if isinstance(masks, list):
        obj_dir = os.path.join(save_dir, fname)
        if not os.path.exists(obj_dir):
            os.makedirs(obj_dir)
        for index, mask in enumerate(masks, 1):
            cv2.imwrite(os.path.join(obj_dir, 'obj_'+str(index)+".png"), mask)
    else:
        cv2.imwrite(os.path.join(save_dir, fname+".png"), masks)

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
    image = cv2.imread(img_path)
    sz = np.squeeze(image.shape)
    imgSize = doc.createElement('size')

    imgWidth = doc.createElement('width')
    imgWidth.appendChild(doc.createTextNode(str(sz[1])))
    imgSize.appendChild(imgWidth)

    imgHeight = doc.createElement('height')
    imgHeight.appendChild(doc.createTextNode(str(sz[0])))
    imgSize.appendChild(imgHeight)

    depth = 1 if len(sz) == 2 else sz[2]
    imgDepth = doc.createElement('depth')
    imgDepth.appendChild(doc.createTextNode(str(depth)))
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

            
