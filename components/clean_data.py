from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QProgressBar 
import os
import h5py
import cv2
from .enumDef import *
import numpy as np
IMAGE_FORMATS = ['jpg', 'jpeg', 'tif', 'tiff', 'png']

class AnnotationCleaner(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/AnnotationCleaner.ui', baseinstance=self)
        self.setWindowTitle("Annotation Cleaner")
        self.ui.dir_button.clicked.connect(self.get_dir)
        self.ui.clean_button.clicked.connect(self.clean)
        self.ui.progress.setValue(0)

        self.dataset_dir = None

    def get_dir(self):
        self.dataset_dir = QFileDialog.getExistingDirectory(self, "Select Dataset Directory")
        self.ui.dir.setText(self.dataset_dir)

    def clean(self):
        if self.dataset_dir is None:
            return
        
        samples = {}
        for f in os.listdir(self.dataset_dir):
            path = os.path.join(self.dataset_dir, f)
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
                    for timestamp in location['annotations']:
                        print(timestamp)
                        if self.is_noisy(location['annotations'][timestamp]):
                            del location['annotations'][timestamp]      
                location.flush()   
                       
            image_index += 1
            self.ui.progress.setValue(round(image_index*100/total))
        self.ui.progress.setValue(100)    

    def is_noisy(self, anno):
        
        type = anno.attrs['type']
        if type == POLYGON:
            area = cv2.contourArea(anno['polygon'][:,0:2].astype(np.float32))
            return True if area < 10 else False
        elif type == BBX:
            bbx = anno['boundingBox']
            return True if bbx[2]<5 or bbx[3]<5 else False
        elif type == OVAL:
            axis = anno['axis']
            return True if axis[0]<5 or axis[1]<5 else False
        else:
            print("Ignored type")
            return False
            
        