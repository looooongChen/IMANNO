import json
import os
from .enumDef import *
from PyQt5.QtGui import QIcon 

class Config(dict):

    def __init__(self, path):
        self['fileDirectory'] = './'
        self['configDirectory'] = './config'

        self['DotAnnotationRadius'] = 20
        self['CurveAnnotationWidth'] = 3
        self['MinPolygonArea'] = 10
        self['MinBBXLength'] = 5
        self['MinEllipseAxis'] = 5
        self['MinCurveLength'] = 5

        self['PenWidth'] = 1
        self['PenAlpha'] = 255
        self['BrushAlpha'] = 120
        self['HighlightIncrAlpha'] = 50
        self['HighlightIncrWidth'] = 1
        self['HighlightIncrWidthDot'] = 3

        self['DotDefaultColor'] = '#cc0000'

        self.saved = True
        self.disp = SHOW_ALL
        self.pre_disp = SHOW_ALL
        self.icons = {k: QIcon(p) for k, p in ICONS.items()}
        
        self.path = path
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if os.path.isfile(path):
            with open(path, 'r') as f:
                for k, value in json.load(f).items():
                    self[k] = value

    def save(self):
        # save_dict = {}
        # for k in save_config:
        #     save_dict[k] = self[k]
        with open(self.path, 'w') as f:
            json.dump(self, f, indent=2)