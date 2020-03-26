
from skimage.filters import laplace, gaussian, sobel, sobel_h, sobel_v
from skimage.color import rgb2gray
from skimage.morphology import erosion, dilation, disk
from skimage.draw import circle
from scipy import ndimage
import numpy as np
import math
import heapq
import time

# def laplacian_cost(img):
#     L = laplace(img)
#     L_min = erosion(L, disk(1))
#     L_max = dilation(L, disk(1))
#     L = np.logical_or(np.logical_and(L_min < 0,  L > 0), np.logical_and(L_max > 0, L < 0))
#     return L

def gradient_cost(img):
    G = sobel(img)
    return 1-G/G.max()

class Livewire(object):

    def __init__(self, image=None, sigma=1):
        
        if image is not None:
            self.image = image
            self.sz = image.shape[0:2]
        else:
            self.image = None
            self.sz = None 
        self.sigma = sigma
        self.refresh()
        self.seed = None
        self.previous = None
    
    def set_image(self, image):
        self.image = image
        self.refresh()

    def set_sigma(self, sigma):
        self.sigma = sigma
        self.refresh()

    def refresh(self):
        if self.image is not None:
            image = rgb2gray(self.image)
            self.sz = image.shape
            img_smooth = gaussian(image, sigma=self.sigma)
            self.cost_G = gradient_cost(img_smooth) 

    def pt2index(self, pt):
        return pt[0] + pt[1] * self.sz[1]
    
    def index2pt(self, ind):
        return (ind % self.sz[1], ind //self.sz[1])

    def get_neighbors(self, pt):
        xx = list(range(max(0, pt[0]-1), min(pt[0]+2, self.sz[1])))
        yy = list(range(max(0, pt[1]-1), min(pt[1]+2, self.sz[0])))
        for x in xx:
            for y in yy:
                if x != pt[0] or y != pt[1]:
                # if (x != pt[0] and y == pt[1]) or (x == pt[0] and y != pt[1]):
                    yield (x, y)
    
    def check_pt_in_img(self, pt):
        if pt[0] < 0 or pt[1] < 0 or pt[0] >= self.sz[1] or pt[1] >= self.sz[0]:
            return False
        else:
            return True

    def set_seed(self, seed, live_radius=100):
        '''
        seed: (x, y)
        live_radius: int
        '''
        start = time.time()

        seed = (round(seed[0]), round(seed[1])) 
        self.seed = seed
        if self.image is None:
            return
        if not self.check_pt_in_img(seed):
            return

        processed = np.ones(self.sz, dtype=np.bool)
        rr, cc = circle(seed[1], seed[0], live_radius, shape=self.sz)
        processed[rr, cc] = False

        self.previous = np.zeros(self.sz, np.int32)-1
        self.cost = np.ones(self.sz) + float('inf')

        active = [(0, tuple(seed))]
        while len(active) > 0:
            C, k = heapq.heappop(active)
            ind_k = self.pt2index(k)

            if processed[k[1], k[0]]:
                continue

            processed[k[1], k[0]] = True
            for n in self.get_neighbors(k):
                if processed[n[1], n[0]]:
                    continue
                delta = (k[1]-n[1], k[0]-n[0])
                delta_A = math.sqrt(delta[0]**2+delta[1]**2)

                C_tmp = C + self.cost_G[n[1], n[0]]*delta_A
                if C_tmp < self.cost[n[1], n[0]]:
                    self.cost[n[1], n[0]] = C_tmp
                    self.previous[n[1], n[0]] = self.pt2index(k)
                heapq.heappush(active, (C_tmp, n))
        print('New seed took', time.time()-start, 'seconds.')

    def get_path(self, pt):
        pt = (round(pt[0]), round(pt[1]))
        path = [pt] 
        if self.previous is not None and self.check_pt_in_img(pt):
            ind_p = self.previous[pt[1], pt[0]]
            while self.seed is not None:
                if ind_p == -1:
                    break
                pt_p = self.index2pt(ind_p)
                path.append(pt_p)
                ind_p = self.previous[pt_p[1], pt_p[0]]
        x = np.array([p[0] for p in path]) 
        y = np.array([p[1] for p in path])
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

