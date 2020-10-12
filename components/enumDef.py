UNFINISHED = 'unfinished'
FINISHED = 'finished'
CONFIRMED = 'confirmed'
PROBLEM = 'problematic'

ANNOTATION_EXT = 'hdf5'

BROWSE = 'browse'
POLYGON = 'polygon'
LIVEWIRE = 'livewire'
OVAL = 'oval'
POINT = 'point'
BBX = 'bouding box'
LINE = 'line'

ZOOM_IN_RATE = 1.2
ZOOM_OUT_RATE = 1/ZOOM_IN_RATE
IMAGE_TYPES = ['*.png', '*.bmp', '*.tiff', '*.tif', '*.jpg', '*.jpeg']

HIDE_ALL = 0
SHOW_ALL = 1

OP_MERGE = 0
OP_OVERWRITE = 1
OP_CANCEL = 2

FOLDER = 0
FILE = 1
DELETE = 2
RENAME = 3
IMPORT = 4
SEARCH = 5

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