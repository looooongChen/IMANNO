from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QProgressBar 
import os
import h5py
import cv2
from .graphDef import *
import numpy as np
IMAGE_FORMATS = ['jpg', 'jpeg', 'tif', 'tiff', 'png']

class PatchExtractor(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/PatchExtractor.ui', baseinstance=self)
        self.setWindowTitle("Patch Extractor")
        self.ui.source_button.clicked.connect(self.get_source_dir)
        self.ui.dest_button.clicked.connect(self.get_dest_dir)
        self.ui.extract_button.clicked.connect(self.extract)
        self.ui.format.addItem(".png")
        self.ui.padding.setText('0.1')
        self.ui.progress.setValue(0)

        self.source_dir = None
        self.dest_dir = None

    def get_source_dir(self):
        self.source_dir = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        self.ui.source.setText(self.source_dir)

    def get_dest_dir(self):
        self.dest_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        self.ui.dest.setText(self.dest_dir)

    def extract(self):
        if self.source_dir is None or self.dest_dir is None:
            return
        padding = float(self.ui.padding.text())
        if padding < 0:
            print("Padding value should be positive")
            return
        
        
        samples = {}
        for f in os.listdir(self.source_dir):
            path = os.path.join(self.source_dir, f)
            if os.path.isdir(path):
                continue
            filename, ext = os.path.splitext(path)
            if ext[1:] not in IMAGE_FORMATS:
                continue
            if os.path.exists(filename + '.hdf5'):
                samples[path] = filename + '.hdf5'
        
        patch_index = 1
        image_index = 1
        total = len(samples)
        for img_path, hdf5_path in samples.items():
            print("processing: " + img_path)

            image = cv2.imread(img_path)

            with h5py.File(hdf5_path) as location:
                # self.load_attributes(location)

                if 'annotations' in location.keys():
                    for timestamp in location['annotations']:
                        image_patch, mask_patch = self.extract_single_annotation(image, location['annotations'][timestamp], padding)
                        if str(self.ui.format.currentText()) == '.png':
                            if image_patch is not None:
                                cv2.imwrite(os.path.join(self.dest_dir, "patch_"+str(patch_index)+".png"), image_patch)
                                if mask_patch is not None:
                                    cv2.imwrite(os.path.join(self.dest_dir, "mask_"+str(patch_index)+".png"), mask_patch)
                                patch_index += 1
                            

            image_index += 1
            self.ui.progress.setValue(round(image_index*100/total))
        self.ui.progress.setValue(100)    

    def extract_single_annotation(self, image, anno, padding, attr_group=None):
        
        type = anno.attrs['type']
        if type == POLYGON:
            bbx = anno['boundingBox']
        elif type == BBX:
            bbx = anno['boundingBox']
        elif type == OVAL:
            print("Ellipse annotation not supported currently.")
            return None, None
        else:
            print("Ignored type")
            return None, None

        # extract image patch
        x, y, w, h = bbx[0], bbx[1], bbx[2], bbx[3] 
        sz = image.shape
        padding_w = round(w*padding)
        padding_h = round(h*padding)
        Xmin, Xmax = int(max(x-1-padding_w, 0)), int(min(x+w+padding_w, sz[1]))
        Ymin, Ymax = int(max(y-1-padding_h, 0)), int(min(y+h+padding_h, sz[0]))
        image_patch = image[Ymin:Ymax, Xmin:Xmax]

        # extract mask patch
        mask_patch = np.zeros((image_patch.shape[0], image_patch.shape[1]), np.uint8)
        if type == POLYGON:
            if len(anno['polygon'][:,0]) < 5:
                return None, None
            pts = np.stack([anno['polygon'][:,0]+padding_w, anno['polygon'][:,1]+padding_h], axis=1)
            pts = np.expand_dims(pts, 0)
            cv2.fillPoly(mask_patch, pts.astype(np.int32), 255)
            return image_patch, mask_patch
        elif type == OVAL:
            print("Ellipse annotation not supported currently.")
            return image_patch, None
        else:
            return image_patch, None
            
class MaskExtractor(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/MaskExtractor.ui', baseinstance=self)
        self.setWindowTitle("Mask Extractor")
        self.ui.source_button.clicked.connect(self.get_source_dir)
        self.ui.dest_button.clicked.connect(self.get_dest_dir)
        self.ui.extract_button.clicked.connect(self.extract)
        self.ui.type.addItem("single (all objects in one image, may overlap)")
        self.ui.type.addItem("multiple (save a mask for each object)")
        self.ui.format.addItem(".png")
        # self.ui.format.addItem(".mat")
        self.ui.progress.setValue(0)

        self.source_dir = None
        self.dest_dir = None

    def get_source_dir(self):
        self.source_dir = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        self.ui.source.setText(self.source_dir)

    def get_dest_dir(self):
        self.dest_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        self.ui.dest.setText(self.dest_dir)

    def extract(self):
        if self.source_dir is None or self.dest_dir is None:
            return
        
        samples = {}
        for f in os.listdir(self.source_dir):
            path = os.path.join(self.source_dir, f)
            if os.path.isdir(path):
                continue
            filename, ext = os.path.splitext(path)
            if ext[1:] not in IMAGE_FORMATS:
                continue
            if os.path.exists(filename + '.hdf5'):
                samples[path] = filename + '.hdf5'
        
        image_index = 1
        total = len(samples)
        for img_path, hdf5_path in samples.items():
            print("processing: " + img_path)

            image = cv2.imread(img_path)

            with h5py.File(hdf5_path) as location:
                # self.load_attributes(location)

                if 'annotations' in location.keys():
                    
                    save_as_one = True if str(self.ui.type.currentText()).startswith('single') else False
                    masks = MaskExtractor.generate_mask(location, [image.shape[0], image.shape[1]], save_as_one=save_as_one)

                    if str(self.ui.format.currentText()) == '.png':
                        fname = os.path.splitext(os.path.basename(img_path))[0]
                        MaskExtractor.save_mask_as_png(self.dest_dir, fname, masks, save_as_one)

            image_index += 1
            self.ui.progress.setValue(round(image_index*100/total))
        self.ui.progress.setValue(100)    

    @classmethod
    def generate_mask(cls, annos, sz, save_as_one=True):

        masks = []
        if save_as_one:
            masks.append(np.zeros((sz[0], sz[1]), np.uint16))
        else:
            mask = np.zeros((sz[0], sz[1]), np.uint8)

        index = 1
        for timestamp in annos['annotations']:

            anno = annos['annotations'][timestamp]

            type = anno.attrs['type']
            if type == POLYGON:
                bbx = anno['boundingBox']
            elif type == OVAL or type == BBX:
                print("Ellipse and BBX annotation not supported currently.")
                continue
            else:
                print("Ignored type")
                continue

            # plot objects
            if type == POLYGON:
                if len(anno['polygon'][:,0]) < 5:
                    continue
                pts = np.stack([anno['polygon'][:,0]+bbx[0], anno['polygon'][:,1]+bbx[1]], axis=1)
                pts = np.expand_dims(pts, 0)
                if save_as_one:
                    cv2.fillPoly(masks[0], pts.astype(np.int32), index)
                else:
                    mask = mask * 0
                    cv2.fillPoly(mask, pts.astype(np.int32), 255)
                    masks.append(mask.copy())
                index += 1

            if save_as_one and index<=256:
                masks[0] = masks[0].astype(np.uint8) 
        
        return masks
    
    @classmethod
    def save_mask_as_png(cls, save_dir, fname, masks, save_as_one=True):
        
        if not save_as_one:
            obj_dir = os.path.join(save_dir, fname)
            if not os.path.exists(obj_dir):
                os.makedirs(obj_dir)
            for index, mask in enumerate(masks, 1):
                cv2.imwrite(os.path.join(obj_dir, 'obj_'+str(index)+".png"), mask)
        else:
            cv2.imwrite(os.path.join(save_dir, fname+"_mask.png"), masks[0])


class DetectionAnnoExtractor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/DetectionAnnoExtractor.ui', baseinstance=self)
        self.setWindowTitle("Extract annotation file for object detection")
        self.ui.source_button.clicked.connect(self.get_source_dir)
        self.ui.dest_button.clicked.connect(self.get_dest_dir)
        self.ui.extract_button.clicked.connect(self.extract)
        self.ui.format.addItem(".xml")
        # self.ui.format.addItem(".mat")
        self.ui.progress.setValue(0)

        self.source_dir = None
        self.dest_dir = None

    def get_source_dir(self):
        self.source_dir = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        self.ui.source.setText(self.source_dir)

    def get_dest_dir(self):
        self.dest_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        self.ui.dest.setText(self.dest_dir)

    def extract(self):
        if self.source_dir is None or self.dest_dir is None:
            return
        
        samples = {}
        for f in os.listdir(self.source_dir):
            path = os.path.join(self.source_dir, f)
            if os.path.isdir(path):
                continue
            filename, ext = os.path.splitext(path)
            if ext[1:] not in IMAGE_FORMATS:
                continue
            if os.path.exists(filename + '.hdf5'):
                samples[path] = filename + '.hdf5'
        
        image_index = 1
        total = len(samples)
        for img_path, hdf5_path in samples.items():
            print("processing: " + img_path)

            annoList = []
            with h5py.File(hdf5_path) as location:
                # self.load_attributes(location)
                if 'annotations' in location.keys():
                    for timestamp in location['annotations']:
                        anno = location['annotations'][timestamp]
                        type = anno.attrs['type']
                        if type == POLYGON or type == BBX:
                            bbx = anno['boundingBox']
                            annoList.append({'name': 'obj', 'bndbox': (bbx[0], bbx[1], bbx[0]+bbx[2], bbx[1]+bbx[3])})
                        else:
                            print("Only polygon and bounding box type are supported.")
                            continue
                if str(self.ui.format.currentText()) == '.xml':
                    fname = os.path.splitext(os.path.basename(img_path))[0]
                    save_path = os.path.join(self.dest_dir, fname+'.xml')
                    DetectionAnnoExtractor.createXml(annoList, save_path)

            image_index += 1
            self.ui.progress.setValue(round(image_index*100/total))
        self.ui.progress.setValue(100)    

    
    @classmethod
    def createXml(cls, AnnoList, file_name):
        """

        :param AnnoList: include 'name' and 'bndbox'.
        e.g:
        AnnoList = [
        {'name': 'test', 'bndbox': ('xmin', 'ymin', 'xmax', 'ymax')},
        {'name': 'test2', 'bndbox': ('xmin', 'ymin2', 'xmax', 'ymax')}
        ]

        :param file_name: should be defined.
        :return: .xml file
        """
        import xml.dom.minidom

        doc = xml.dom.minidom.Document()
        root = doc.createElement('Annotation')
        doc.appendChild(root)

        for dict in AnnoList:

            nodeObject = doc.createElement('object')

            nodeName = doc.createElement('name')
            nodeName.appendChild(doc.createTextNode(str(dict['name'])))

            nodeBndbox = doc.createElement('bndbox')

            nodeXmin = doc.createElement('xmin')
            nodeXmin.appendChild(doc.createTextNode(str(dict['bndbox'][0])))

            nodeYmin = doc.createElement('ymin')
            nodeYmin.appendChild(doc.createTextNode(str(dict['bndbox'][1])))

            nodeXmax = doc.createElement('xmax')
            nodeXmax.appendChild(doc.createTextNode(str(dict['bndbox'][2])))

            nodeYmax = doc.createElement('ymax')
            nodeYmax.appendChild(doc.createTextNode(str(dict['bndbox'][3])))

            nodeBndbox.appendChild(nodeXmin)
            nodeBndbox.appendChild(nodeYmin)
            nodeBndbox.appendChild(nodeXmax)
            nodeBndbox.appendChild(nodeYmax)

            nodeObject.appendChild(nodeName)
            nodeObject.appendChild(nodeBndbox)

            root.appendChild(nodeObject)

        fp = open(file_name, 'w')
        doc.writexml(fp, indent='\t', addindent='\t', newl='\n', encoding="utf-8")
        fp.close()

    
            
            
