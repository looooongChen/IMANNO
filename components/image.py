import cv2
import os
from PyQt5.QtGui import QImage
import numpy as np
import hashlib

def compute_checksum(file):

    if os.path.isfile(file):
        f = open(file, "rb") # opening for [r]eading as [b]inary
        data = f.read(524288) # read the first 2**9 bytes
        f.close()
        return hashlib.sha256(data).hexdigest()
    else:
        return None

class Image(object):

    def __init__(self):
        
        self.path = None
        self.filename = None
        self.data = None
        self.height, self.width = None, None
        self.disp = None
        self.auto_contrast = False
        # self.checksum = None
        self.image_open = False
    
    def is_open(self):
        return self.image_open

    def open(self, path):
        self.close()
        self.data = cv2.imread(path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        if self.data is not None:
            self.path = path
            self.filename = os.path.basename(path)
            if len(self.data.shape) == 3:
                self.data = np.flip(self.data, 2)
            self.height, self.width = self.data.shape[0], self.data.shape[1]
            self.disp = self.data
            self.auto_contrast = False
            # self.checksum = None
            self.image_open = True
    
    def close(self):
        self.path = None
        self.filename = None
        self.data = None
        self.height, self.width = None, None
        self.disp = None
        self.auto_contrast = False
        # self.checksum = None
        self.image_open = False

    def set_auto_contrast(self, auto_contrast=True):
        if self.is_open():
            if self.auto_contrast is False and auto_contrast:
                # data_sub = self.data[::16,::16]
                # mmin, mmax = data_sub.min(), data_sub.max()
                mmin, mmax = self.data.min(), self.data.max()
                self.disp = ((self.data-mmin)*(255/(mmax-mmin))).astype(np.uint8)
                self.auto_contrast = True
            if self.auto_contrast and auto_contrast is False:
                self.disp = self.data
                self.auto_contrast = False

    def get_QImage(self):
        if self.is_open():
            disp = (self.disp/255).astype(np.uint8) if self.disp.dtype == 'uint16' else self.disp
            if len(disp.shape) == 2:
                disp = cv2.cvtColor(disp,cv2.COLOR_GRAY2RGBA) 
            elif disp.shape[-1] == 3:
                disp = cv2.cvtColor(disp,cv2.COLOR_RGB2RGBA)
            elif disp.shape[-1] ==4:
                pass
            else:
                return None
                print("Not supported image shape:", self.data.shape, ', image dtype:', self.data.dtype) 
            return QImage(disp, self.width, self.height, QImage.Format_RGBA8888)
        else:
            return None

    def get_gray(self):
        if self.is_open():
            if len(self.data.shape) == 3:
                return cv2.cvtColor(self.data, cv2.COLOR_RGB2GRAY)
            else:
                return self.data

    def checksum(self):
        if self.is_open():
            return compute_checksum(self.path)

        # if self.height < 64 or self.width < 64:
        #     return hashlib.sha256(self.data.tobytes(order='C')).hexdigest()
        # else:
        #     s = self.data[:64,:64].tobytes(order='C')
        #     s = s + self.data[:64,-64:].tobytes(order='C')
        #     s = s + self.data[-64:,:64].tobytes(order='C')
        #     s = s + self.data[-64:,-64:].tobytes(order='C')
        #     return hashlib.sha256(s).hexdigest()

        # if self.is_open() and self.checksum is None:
        #     self.checksum = hashlib.sha256(self.data.tobytes(order='C')).hexdigest()
        #     return self.checksum
        # else:
        #     return None
            

