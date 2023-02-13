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
        self.data = []
        self.height, self.width = None, None
        self.disp = None
        self.auto_contrast = False
        # self.checksum = None 
        self.image_open = False
        self.idx = 0
    
    def is_open(self):
        return self.image_open

    def open(self, path):
        self.close()

        # unicode path compatiable
        # numpyarray = np.fromfile(path, dtype='uint8')
        # self.data = cv2.imdecode(numpyarray, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        _, ext = os.path.splitext(path)
        if ext in ['.tif', '.tiff']:
            self.data = cv2.imreadmulti(path, flags=cv2.IMREAD_UNCHANGED | cv2.IMREAD_ANYDEPTH)[1]
        elif ext in ['.avi', '.mp4']:
            pass
        else:
            self.data = cv2.imread(path, cv2.IMREAD_UNCHANGED | cv2.IMREAD_ANYDEPTH)
            self.data = [self.data] if self.data is not None else []
        self.data = [np.squeeze(f) for f in self.data]

        # for f in self.data:
        #     print(f.shape, f.dtype)
        
        if len(self.data) > 0:
            if len(self.data[0].shape) == 3:
                if self.data[0].shape[-1] == 4:
                    self.data = [im[...,:3] for im in self.data]
                elif self.data[0].shape[-1] == 2:
                    self.data = [im[...,0] for im in self.data]
                self.data = [np.flip(im, 2) for im in self.data]
            self.path = path
            self.filename = os.path.basename(path)
            self.height, self.width = self.data[0].shape[0], self.data[0].shape[1]
            self.mmax, self.mmin = np.max(self.data), np.min(self.data)
            self.disp = self.data[0]
            self.auto_contrast = False
            # self.checksum = None
            self.image_open = True
    
    def next(self):
        if len(self.data) > 0:
            self.idx = self.idx + 1 if self.idx < len(self.data)-1 else 0
            self.disp = self.data[self.idx]
            if self.auto_contrast:
                self.disp = ((self.data[self.idx]-self.mmin)/(self.mmax-self.mmin)*255).astype(np.uint8)
            return True
        else:
            return False

    def last(self):
        if len(self.data) > 0:
            self.idx = self.idx - 1 if self.idx > 0 else len(self.data) - 1
            self.disp = self.data[self.idx]
            return True
        else:
            return False
            
    
    def close(self):
        self.path = None
        self.filename = None
        self.data = []
        self.height, self.width = None, None
        self.disp = None
        self.auto_contrast = False
        # self.checksum = None
        self.image_open = False
        self.idx = 0

    def set_auto_contrast(self, auto_contrast=True):
        if self.is_open():
            if self.auto_contrast is False and auto_contrast:
                # data_sub = self.data[::16,::16]
                # mmin, mmax = data_sub.min(), data_sub.max()
                self.disp = ((self.data[self.idx]-self.mmin)/(self.mmax-self.mmin)*255).astype(np.uint8)
                self.auto_contrast = True
            if self.auto_contrast and auto_contrast is False:
                self.disp = self.data[self.idx]
                self.auto_contrast = False

    def get_QImage(self):
        if self.is_open():
            disp = (self.disp/255).astype(np.uint8) if self.disp.dtype == 'uint16' else self.disp
            # print(disp.shape, disp.dtype)
            if len(disp.shape) == 2:
                disp = cv2.cvtColor(disp,cv2.COLOR_GRAY2RGB) 
            # if disp.shape[-1] == 2:
            #     disp = cv2.cvtColor(disp[...,-1],cv2.COLOR_GRAY2RGB) 
            # elif disp.shape[-1] == 3:
            #     # disp = cv2.cvtColor(disp,cv2.COLOR_RGB2RGBA)
            #     # disp = cv2.cvtColor(disp,cv2.COLOR_BGR2RGB)
            #     pass
            return QImage(disp.copy(), self.width, self.height, QImage.Format_RGB888)
            # return QImage(np.transpose(disp,(1,0,2)).copy(), self.width, self.height, QImage.Format_RGB888)
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
            

