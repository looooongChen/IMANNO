from skimage.filters import sobel
from skimage.draw import circle
from scipy import ndimage
from .image import Image
import cv2
import numpy as np
import math
import heapq
import time

def gradient_cost(img):
    G = sobel(img)
    # dx = cv2.Sobel(img,cv2.CV_32F,1,0,ksize=3)
    # dy = cv2.Sobel(img,cv2.CV_32F,0,1,ksize=3)
    # G = (dx ** 2 + dy ** 2) ** 0.5
    return 1-G/G.max()

class Livewire(object):

    def __init__(self, image=None, scale=1):
        '''
        Args:
            image: object of class components.image.Image
        '''
        self.image = image
        self.scale = scale
        self.status = [None, None] # the current image_checksum and scale
        self.scale_x, self.scale_y = None, None
        self.size_x, self.size_y = None, None
        self.cost = None
        self.cost_G = None
        self.seed = None
        self.previous = None

        self.set_image(image)
    
    def set_image(self, image):
        '''
        Args:
            image: object of class components.image.Image
        '''
        if isinstance(image, Image):
            self.image = image

    def sync_image(self, image=None, scale=None):
        '''
        Args:
            image: object of class components.image.Image
            scale: computational scale
        '''
        self.set_image(image)
        if scale is not None:
            self.scale = scale
        if self.image is not None and self.image.is_open() and self.scale is not None:
            check_sum = self.image.get_checksum()
            if check_sum != self.status[0] or self.scale != self.status[1]:
                self.status[0], self.status[1] = check_sum, self.scale
                self.size_x, self.size_y = int(self.image.width*self.scale), int(self.image.height*self.scale)
                image = cv2.resize(self.image.get_gray(), (self.size_x, self.size_y))
                image = cv2.GaussianBlur(image, (11,11), 1)
                self.scale_x, self.scale_y = image.shape[1]/self.image.width, image.shape[0]/self.image.height
                self.cost_G = gradient_cost(image) 
    
    def is_valid(self):
        if self.status[0] is None or self.status[1] is None:
            return False
        return True

    def _pt2index(self, pt):
        return pt[0] + pt[1] * self.size_x
    
    def _index2pt(self, ind):
        return (ind % self.size_x, ind // self.size_x)

    def _get_neighbors(self, pt):
        xx = list(range(max(0, pt[0]-1), min(pt[0]+2, self.size_x)))
        yy = list(range(max(0, pt[1]-1), min(pt[1]+2, self.size_y)))
        for x in xx:
            for y in yy:
                if x != pt[0] or y != pt[1]:
                    yield (x, y)
    
    def _pt_in_img(self, pt):
        '''
        Args:
            pt: coordinate tuple (x, y)
        '''
        if pt[0] < 0 or pt[1] < 0 or pt[0] >= self.size_x or pt[1] >= self.size_y:
            return False
        return True

    def set_seed(self, x, y, live_radius=100):
        '''
        Args:
            x: x coordinate (horizontal direction)
            y: y coordinate (vertical direction)
            live_radius: int
        '''
        if not self.is_valid():
            self.sync_image()
        if self.is_valid():
            start = time.time()

            seed = (round(x*self.scale_x), round(y*self.scale_y))
            self.seed = seed

            if self._pt_in_img(self.seed):
                processed = np.ones((self.size_y, self.size_x), dtype=np.bool)
                rr, cc = circle(seed[1], seed[0], live_radius, shape=(self.size_y, self.size_x))
                processed[rr, cc] = False

                self.previous = np.zeros((self.size_y, self.size_x), np.int32)-1
                self.cost = np.ones((self.size_y, self.size_x)) + float('inf')

                active = [(0, tuple(seed))]
                while len(active) > 0:
                    C, k = heapq.heappop(active)
                    ind_k = self._pt2index(k)

                    if processed[k[1], k[0]]:
                        continue

                    processed[k[1], k[0]] = True
                    for n in self._get_neighbors(k):

                        if processed[n[1], n[0]]:
                            continue

                        delta = (k[1]-n[1], k[0]-n[0])
                        delta_A = math.sqrt(delta[0]**2+delta[1]**2)

                        C_tmp = C + self.cost_G[n[1], n[0]]*delta_A
                        if C_tmp < self.cost[n[1], n[0]]:
                            self.cost[n[1], n[0]] = C_tmp
                            self.previous[n[1], n[0]] = self._pt2index(k)
                        heapq.heappush(active, (C_tmp, n))
                print('New seed set took', time.time()-start, 'seconds.')

    def get_path(self, x, y):
        pt = (round(x*self.scale_x), round(y*self.scale_y))
        path = [pt] 
        if self.previous is not None and self._pt_in_img(pt):
            ind_p = self.previous[pt[1], pt[0]]
            while self.seed is not None:
                if ind_p == -1:
                    break
                pt_p = self._index2pt(ind_p)
                path.append(pt_p)
                ind_p = self.previous[pt_p[1], pt_p[0]]
        path = np.array(path)
        path[:,0] = path[:,0]/self.scale_x
        path[:,1] = path[:,1]/self.scale_y
        if self.scale < 1:
            path = cv2.approxPolyDP(np.float32(path), 1/self.scale, closed=False)
            path = np.squeeze(path, axis=1)
        x, y = path[:,0], path[:,1]
        return x, y


if __name__ == '__main__': 
    from skimage.io import imread
    import matplotlib.pyplot as plt

    # start = (530, 156)
    start = (540, 143)
    end = (577, 185)
    # end = (627, 234)

    img = imread('./test.jpg')
    plt.imshow(img)
    live = Livewire(img)
    live.set_seed(seed=start, live_radius=100)
    x, y = live.get_path(end)

    plt.plot(x, y)

    plt.show()

