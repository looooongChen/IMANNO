import json
import os
from .enumDef import *

save_config = ['fileDirectory', 'defaultLabelListDir', 'DotAnnotationRadius', 'lineAnnotationWidth', 'minPolygonArea', 'minBBXLength', 'minOvalAxis', 'minLineLength']

class Config(dict):

    def __init__(self, path):
        self['fileDirectory'] = './demo_images'
        self['defaultLabelListDir'] = './config'
        self['DotAnnotationRadius'] = 2
        self['lineAnnotationWidth'] = 2
        self['minPolygonArea'] = 10
        self['minBBXLength'] = 5
        self['minOvalAxis'] = 5
        self['minLineLength'] = 5

        self['display_channel'] = SHOW_ALL
        self['pre_display_channel'] = SHOW_ALL
        
        self.path = path
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if os.path.isfile(path):
            with open(path, 'r') as f:
                for k, value in json.load(f).items():
                    self[k] = value

    def save(self):
        save_dict = {}
        for k in save_config:
            save_dict[k] = self[k]
        with open(self.path, 'w') as f:
            json.dump(save_dict, f)