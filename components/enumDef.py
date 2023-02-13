from PyQt5.QtCore import Qt

UNFINISHED = 'unfinished'
FINISHED = 'finished'
CONFIRMED = 'confirmed'
PROBLEM = 'problematic'

ANNOTATION_EXT = '.json'

BROWSE = 'browse'
POLYGON = 'polygon'
LIVEWIRE = 'livewire'
# OVAL = 'oval'
ELLIPSE = 'ellipse'
# POINT = 'point'
DOT = 'dot'
BBX = 'bbx'
# BBX = 'bouding box'
# LINE = 'line'
CURVE = 'curve'

ZOOM_IN_RATE = 1.2
ZOOM_OUT_RATE = 1/ZOOM_IN_RATE
IMAGE_TYPES = ['*.png', '*.bmp', '*.tiff', '*.tif', '*.jpg', '*.jpeg']

HIDE_ALL = 0
SHOW_ALL = 1

FOLDER = 10
FILE = 11
PROPERTY = 12
LABEL = 13

NEW = 20
DELETE = 21
RENAME = 22
IMPORT = 23
SEARCH = 24
CLEAR = 25

SYM_WARNING = 30

OP_MERGE = 100
OP_OVERWRITE = 101
OP_CANCEL = 102
OP_IMPORT = 103
OP_CLOSEANDOPEN = 104

EX_STAR = 200

# from PyQt5.QtGui import QIcon
import os
icon_path = os.path.join(os.path.dirname(__file__), '../icons/')
ICONS = {}
ICONS[UNFINISHED] = os.path.join(icon_path, 'unfinished.png')
ICONS[FINISHED] = os.path.join(icon_path, 'finished.png')
ICONS[CONFIRMED] = os.path.join(icon_path, 'confirmed.png')
ICONS[PROBLEM] = os.path.join(icon_path, 'problem.png')

ICONS[FOLDER] = os.path.join(icon_path, 'folder.png')
ICONS[LABEL] = os.path.join(icon_path, 'label.png')

ICONS[EX_STAR] = os.path.join(icon_path, 'star.png')

ICONS[NEW] = os.path.join(icon_path, 'new.png')
ICONS[DELETE] = os.path.join(icon_path, 'delete.png')
ICONS[RENAME] = os.path.join(icon_path, 'rename.png')
ICONS[IMPORT] = os.path.join(icon_path, 'import_image.png')
ICONS[SEARCH] = os.path.join(icon_path, 'search.png')
ICONS[CLEAR] = os.path.join(icon_path, 'clear.png')

ICONS[SYM_WARNING] = os.path.join(icon_path, 'warning.png')


DEFAULT_COLOR = '#00cc00'
SHADOW_COLOR = '#009900'

LABEL_COLORS = {'red':'#ec524b',
                'orange': '#ffa62b',
                'yellow': '#fddb3a',
                'green': '#7ea04d',
                'cyan': '#7fdbda',
                'blue': '#3282b8',
                'violet': '#6a2c70',
                'magenta': '#db75c5'}

IMPORT_FP = [255, 0, 0]
IMPORT_CHECKED = [0, 255, 0]
IMPORT_FN = [255, 255, 0]
IMPORT_MATCH_DICE = 0.6
