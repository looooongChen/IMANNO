import instSeg
import os 



class Interface(object):

    def __init__(self):
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.model = None

    def predict(img): 
        if self.model is None:
            self.model = instSeg.load_model(path, load_best=True)
        instance = instSeg.seg_in_tessellation(self.model, img, patch_sz=[512,512], margin=[64,64], overlap=[0,0], mode='wsi')
        return instance

model = Interface()



