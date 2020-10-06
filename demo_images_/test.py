import cv2
import time
from skimage.transform import rescale
from skimage.filters import laplace, gaussian, sobel, sobel_h, sobel_v
from skimage.filters import sobel
import numpy as np

# im = cv2.imread('./Kremer P2 25 b 58.png')
# im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
im = np.ones((30000, 4000, 3))
import hashlib

t = time.time()

# for i in range(0,10):
    # rescale(im, 0.5)
    # cv2.resize(im, (1500, 2000))
    # gaussian(im, 1)
    # cv2.GaussianBlur(im, (11,11), 1)
    # sobel(im)
    # dx = cv2.Sobel(im,cv2.CV_32F,1,0,ksize=3)
    # dy = cv2.Sobel(im,cv2.CV_32F,0,1,ksize=3)
    # dx, dy = cv2.spatialGradient(im)
    # dx = dx/dx.max()	
    # a = (dx ** 2 + dy ** 2)
    # a = dx * dx
    # a = np.power(dx, 2)
    # print(a.dtype, a.min(), a.max())
    # np.sqrt(dx ** 2 + dy ** 2)
    # (dx ** 2 + dy ** 2) ** 0.5
print(im[:50,:50].shape)
s = im[:50,:50].tobytes(order='C')
s = s + im[:50,-50:].tobytes(order='C')
s = s + im[-50:,:50].tobytes(order='C')
s = s + im[-50:,-50:].tobytes(order='C')
# print(len(aa))
hashlib.sha256(s).hexdigest()


print(time.time()-t)
