from PyQt5.QtWidgets import QTreeWidgetItem
from .enumDef import *
from .image import compute_checksum

class FolderItem(QTreeWidgetItem):

    def __init__(self, text=''):
        super().__init__(FOLDER)
        self.setText(0, text)
    
    def set_icon(self, icon):
        self.setIcon(0, icon)
    
    def clone(self):
        item = FolderItem(text=self.text(0))
        return item

class ImageItem(QTreeWidgetItem):

    def __init__(self, base_dir=None):    
        super().__init__(IMAGE)
        self.base_dir = base_dir
        self.img_path = ''
        self.img_name = ''
        self.anno_path = ''
        self.checksum = None
        self.status = UNFINISHED
        self.folder = None
        self.idx = None

    ## set and get information dict
    
    def set_info(self, info):
        self.checksum = info['checksum']
        self.status = info['status']
        self.folder = info['folder']
        if info['image_path'] is not None:
            img_path = info['image_path'].replace('\\', '/')
            if info['rel_path']: 
                img_path = os.path.join(self.base_dir, img_path)
            self.set_image_path(img_path)
        if info['annotation_path'] is not None:
            anno_path = info['annotation_path'].replace('\\', '/')
            if info['rel_path_anno']: 
                anno_path = os.path.join(self.base_dir, anno_path)
            self.set_annotation_path(anno_path)
        self.img_name = info['name'] + '.' + info['ext']
        
    
    def get_info(self, rel_path=True):
        info = IMAGE_ITEM.copy()
        img_path, anno_path = os.path.abspath(os.path.realpath(self.img_path)), os.path.abspath(os.path.realpath(self.anno_path))
        if rel_path and self.base_dir is not None:
            if img_path.startswith(self.base_dir):
                info['rel_path'] = True
                img_path = os.path.relpath(img_path, start=self.base_dir)
            else:
                info['rel_path'] = False
            if anno_path.startswith(self.base_dir):
                info['rel_path_anno'] = True
                anno_path = os.path.relpath(anno_path, start=self.base_dir)
            else:
                info['rel_path_anno'] = False
        info['image_path'] = img_path.replace('\\', '/') 
        info['annotation_path'] = anno_path.replace('\\', '/') 
        info['name'], info['ext'] = os.path.splitext(os.path.basename(path))
        info['chechsum'] = self.checksum
        info['stauts'] = self.status
        info['folder'] = self.folder

        return info

    def clone(self):
        item = ImageItem(base_dir=self.base_dir)
        item.img_path = self.img_path
        item.img_name = self.img_name
        item.anno_path = self.anno_path
        item.checksum = self.checksum
        item.status = self.status
        item.folder = self.folder
        item.idx = self.idx
        return item

    def set_icon(self, icon):
        self.setIcon(0, icon)
    
    ## set and get idx
    # def set_idx(self, idx):
    #     self.idx = idx

    # def set_idx(self, idx):
    #     self.info['idx'] = idx
    #     self.set_annotation_path()

    # def idx(self):
        # return self.info['idx']

    # def is_rel_path(self):
    #     if self.info['rel_path'] is not None:
    #         return self.info['rel_path']
    #     else:
    #         return False

    def set_idx(self, idx):
        self.idx = idx
    
    def set_image_path(self, path):
        self.img_path = path.replace('\\', '/')
        self.setText(0, os.path.basename(path))
        color = Qt.black if os.path.isfile(path) else Qt.red
        self.setForeground(0, color)
        self.img_name = os.path.basename(path)
        self.set_checksum()
    
    def set_annotation_path(self, path):
        self.anno_path = path.replace('\\', '/')

    def set_checksum(self):
        if os.path.isfile(self.img_path):
            self.checksum = compute_checksum(self.img_path)

    def set_status(self, status):
        if status in [FINISHED, UNFINISHED, CONFIRMED, PROBLEM]:
            self.status = status

    def set_folder(self, folder):
        self.folder = folder
    