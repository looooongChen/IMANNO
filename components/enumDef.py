from PyQt5.QtGui import QPen, QBrush, QColor
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

OP_MERGE = 30
OP_OVERWRITE = 31
OP_CANCEL = 32
OP_IMPORT = 33
OP_CLOSEANDOPEN = 34

# from PyQt5.QtGui import QIcon
import os
icon_path = os.path.join(os.path.dirname(__file__), '../icons/')
ICONS = {}
ICONS[UNFINISHED] = os.path.join(icon_path, 'unfinished.png')
ICONS[FINISHED] = os.path.join(icon_path, 'finished.png')
ICONS[CONFIRMED] = os.path.join(icon_path, 'confirmed.png')
ICONS[PROBLEM] = os.path.join(icon_path, 'problem.png')
ICONS[FOLDER] = os.path.join(icon_path, 'folder.png')
ICONS[DELETE] = os.path.join(icon_path, 'delete.png')
ICONS[RENAME] = os.path.join(icon_path, 'rename.png')
ICONS[IMPORT] = os.path.join(icon_path, 'import_image.png')
ICONS[SEARCH] = os.path.join(icon_path, 'search.png')
ICONS[NEW] = os.path.join(icon_path, 'new.png')
ICONS[LABEL] = os.path.join(icon_path, 'label.png')

LABEL_COLORS = {'red':'#ec524b',
                'orange': '#ffa62b',
                'yellow': '#fddb3a',
                'green': '#7ea04d',
                'cyan': '#7fdbda',
                'blue': '#3282b8',
                'violet': '#6a2c70',
                'magenta': '#db75c5'}
DRAWING_COLORS = {'normal': [QColor(0, 200, 0, 255), QColor(0, 200, 0, 70)],
                  'hide': [QColor(0, 0, 0, 0), QColor(0, 0, 0, 0)],
                  'shadow': [QColor(0, 0, 0, 255), QColor(0, 0, 0, 70)]}
LINE_PEN = {k: QPen(c[0], 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin) for k, c in DRAWING_COLORS.items()}
AREA_BRUSH = {k: QBrush(c[1]) for k, c in DRAWING_COLORS.items()}