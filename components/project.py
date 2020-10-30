from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5 import uic
from .image import compute_checksum, Image
from .func_annotation import *
from .messages import annotation_move_message
from .enumDef import *
from datetime import date
from pathlib import Path
import glob
import shutil
import json
import os

PROJ = {'project_name': '', 'folders': [], 'images': []}
ITEM = {'idx': None, 'name': None, 'ext': None, 'checksum': None, 'image_path': None, 'rel_path': False, 'annotation_path': None, 'status': UNFINISHED, 'folder': None}

class Item(object):

    def __init__(self, proj_dir):    
        self.data = ITEM.copy()
        self.proj_dir = proj_dir
    
    @classmethod
    def create(cls, data_dict, proj_dir):
        obj = cls(proj_dir)
        obj.data = data_dict
        return obj
    
    def idx(self):
        return self.data['idx']

    def set_idx(self, idx):
        self.data['idx'] = idx
        self.set_annotation_path()
    
    def exists(self):
        path = self.image_path()
        if path is not None:
            return os.path.isfile(path)
        else:
            return False
    
    def is_rel_path(self):
        if self.data['rel_path'] is not None:
            return self.data['rel_path']
        else:
            return False
    
    ## set and get image path

    def set_image_path(self, path, rel_path=True):
        path = os.path.abspath(os.path.realpath(path))
        if rel_path and path.startswith(self.proj_dir):
            self.data['rel_path'] = True
            path = os.path.relpath(path, start=self.proj_dir)
        self.data['image_path'] = path
        self.data['name'], self.data['ext'] = os.path.splitext(os.path.basename(path))
        self.set_checksum()

    def image_path(self):
        if self.data['image_path'] is not None:
            path = self.data['image_path']
            path = os.path.join(self.proj_dir, path) if self.data['rel_path'] else path
            return path
        else:
            return None

    def image_name(self):
        if self.data['name'] is not None and self.data['ext'] is not None:
            return self.data['name'] + self.data['ext']
        else:
            return None

    ## set and get annotation path

    def set_annotation_path(self):
        if self.data['idx'] is not None:
            anno_dir = os.path.join(self.proj_dir, 'annotations', self.data['idx'])
            if not os.path.exists(anno_dir):
                os.makedirs(anno_dir)
            self.data['annotation_path'] = os.path.join('annotations', self.data['idx'], 'anno.'+ANNOTATION_EXT)
            anno_path = os.path.join(self.proj_dir, self.data['annotation_path'])
            with h5py.File(anno_path) as location:
                location.attrs['status'] = UNFINISHED
    
    def annotation_path(self):
        if self.data['idx'] is not None:
            return os.path.join(self.proj_dir, self.data['annotation_path'])
        else:
            return None

    def annotation_dir(self):
        if self.data['idx'] is not None:
            return os.path.join(self.proj_dir, 'annotations', self.data['idx'])
        else:
            return None

    ## set and get checksum

    def set_checksum(self):
        if self.exists():
            self.data['checksum'] = compute_checksum(self.image_path())

    def checksum(self):
        if self.data['checksum'] is None:
            path = self.image_path()
            if path is not None:
                self.data['checksum'] = compute_checksum(path)
        return self.data['checksum']

    ## status setter and getter

    def set_status(self, status):
        if status in [FINISHED, UNFINISHED, CONFIRMED, PROBLEM]:
            anno_path = self.annotation_path()
            if anno_path is not None:
                with h5py.File(anno_path, 'a') as location:
                    location.attrs['status'] = status
                self.data['status'] = status

    def status(self):
        return self.data['status']
    
    ## folder setter and getter

    def set_folder(self, folder):
        self.data['folder'] = folder
    
    def folder(self):
        return self.data['folder']

class Project(object):
    def __init__(self, annotationMgr=None):
        self.annotationMgr = annotationMgr
        self.project_name = None
        self.project_dir = None
        self.project_file = None
        self.annotation_dir = None
        self.data = {}
        self.index_id = {}
        self.index_folder = {}
        # self.index_checksum = {}
        self.idx = 0
        self.project_open = False

    def is_open(self):
        return self.project_open
    
    def open(self, path):
        '''
        path to the project directory / project file
        '''
        if os.path.splitext(path)[1] == '.improj':
            self.proj_dir = os.path.abspath(os.path.realpath(os.path.dirname(path))) 
            self.proj_file = path
        else:
            self.proj_dir = os.path.abspath(os.path.realpath(path))
            f = glob.glob(os.path.join(path, '*.improj'))
            if len(f) > 0:
                self.proj_file = f[0]
            else:
                self.proj_file = os.path.join(path, os.path.basename(path)+'.improj')
        # create directories when necessary
        if not os.path.exists(self.proj_dir):
            os.makedirs(self.proj_dir)
        self.annotation_dir = os.path.join(self.proj_dir, 'annotations')
        if not os.path.exists(self.annotation_dir):
            os.makedirs(self.annotation_dir)
        # load project file if exists
        if not os.path.exists(self.proj_file):
            self.data = PROJ.copy()
            self.data['project_name'] = os.path.basename(self.proj_file)[:-7]
        else:
            with open(self.proj_file) as json_file:
                self.data = json.load(json_file)
            self.index_id = {e['idx']: Item.create(e, self.proj_dir) for e in self.data['images']}
            self.index_folder = self.get_index('folder')
        self.project_name = self.data['project_name']
        # compute current idx
        ids = [int(idx) for idx in self.index_id.keys()]
        self.idx = max(ids) + 1 if len(ids) != 0 else 0
        self.project_open = True

    def close(self):
        if self.project_open:
            self.annotationMgr.save()
            self.save()
        self.project_name = None
        self.proj_dir = None
        self.proj_file = None
        self.annotation_dir = None
        self.data = {}
        self.index_id = {}
        self.index_folder = {}
        self.idx = 0
        self.project_open = False
    
    def save(self):
        if self.is_open():
            self.data['folders'] = list(self.index_folder.keys())
            self.data['images'] = []
            for item in self.index_id.values():
                self.data['images'].append(item.data)
            with open(self.proj_file, 'w') as outfile:
                json.dump(self.data, outfile, indent=4)

    ## folder operations
    def add_folder(self, folder_name):
        if folder_name not in self.index_folder.keys():
            self.index_folder[folder_name] = []
    
    def delete_folder(self, folder_name, remove_image=True):
        if folder_name in self.index_folder.keys():
            # do not call self.remove_image for faster speed
            for item in self.index_folder[folder_name]:
                if remove_image:
                    if item.annotation_path() == self.annotationMgr.annotation_path:
                        self.annotationMgr.close()
                    anno_dir = item.annotation_dir()
                    if os.path.exists(anno_dir):
                        shutil.rmtree(anno_dir)
                    del self.index_id[item.idx()]
                else:
                    item.set_folder(None)
            del self.index_folder[folder_name]
    
    def rename_folder(self, old_name, new_name):
        if old_name in self.index_folder.keys() and new_name not in self.index_folder.keys():
            for item in self.index_folder[old_name]:
                item.set_folder(new_name)
            self.index_folder[new_name] = self.index_folder.pop(old_name)

    ## image operations

    def add_images(self, images, folders=None):
        idxs = []
        if folders is None or isinstance(folders, str):
            folders = [folders] * len(images)
        if len(images) > 0:
            progress = ProgressDiag(len(images), 'Adding images to project...')
            progress.show()
        for img, folder in zip(images, folders):
            idx = self.add_image(img, folder)
            progress.new_item('Added: ' + img)
            # QCoreApplication.processEvents()
            if idx is not None:
                idxs.append(idx)
        return idxs
    
    def add_image(self, image_path, folder=None):
        item = Item(self.proj_dir)
        idx = '{:08d}'.format(self.idx)
        self.idx += 1
        # set idx (annotation is also set here) 
        item.set_idx(idx) 
        # add image path (checksum is also set here)  
        item.set_image_path(image_path)
        # copy annotation file if exist 
        annotation_path = os.path.splitext(image_path)[0] + '.' + ANNOTATION_EXT
        if os.path.isfile(annotation_path):
            item.set_status(self.annotationMgr.get_status(annotation_path))
            shutil.copy(annotation_path, item.annotation_path())
        # update index
        self.index_id[idx] = item
        if folder in self.index_folder.keys():
            item.set_folder(folder)
            self.index_folder[folder].append(item)
        return idx

    def remove_image(self, idx):
        if idx in self.index_id.keys():
            item = self.index_id[idx]
            if item.annotation_path == self.annotationMgr.annotation_path:
                self.annotationMgr.close()
            anno_dir = item.annotation_dir()
            if os.path.exists(anno_dir):
                shutil.rmtree(anno_dir)
            del self.index_id[idx]
            folder = item.folder()
            if folder in self.index_folder.keys():
                for i in range(len(self.index_folder[folder])):
                    if self.index_folder[folder][i] is item:
                        del self.index_folder[folder][i]
                        break
    
    ## image path setter and getter

    def set_image_path(self, idx, path):
        if idx in self.index_id.keys():
            self.index_id[idx].set_image_path(path)

    def get_image_path(self, idx):
        if idx in self.index_id.keys():
            return self.index_id[idx].image_path()
        else:
            return None
    
    def get_image_name(self, idx):
        if idx in self.index_id.keys():
            return self.index_id[idx].image_name()
        else:
            return None

    ## annotation path setter and getter

    def get_annotation_path(self, idx):
        if idx in self.index_id.keys():
            return self.index_id[idx].annotation_path()
        else:
            return None
    
    ## chechsum setter and getter
    
    def set_checksum(self, idx):
        if idx in self.index_id.keys():
            self.index_id[idx].set_checksum()

    def get_checksum(self, idx):
        if idx in self.index_id.keys():
            return self.index_id[idx].checksum()  
        else:
            return None

    ## status setter and getter

    def set_status(self, idx, status):
        if idx in self.index_id.keys():
            self.index_id[idx].set_status(status)
            if self.index_id[idx].annotation_path() == self.annotationMgr.annotation_path:
                self.annotationMgr.set_status(status)

    def get_status(self, idx):
        if idx in self.index_id.keys():
            return self.index_id[idx].status()
        else:
            return None

    ## compute index

    def get_files(self, folder):
        files = []
        for f in [str(path) for t in IMAGE_TYPES for path in Path(folder).rglob(t)]:
            item = Item(self.proj_dir)
            item.set_image_path(f)
            files.append(item)
        return files

    def get_index(self, attr_name, files=None, check_exist=False, progressBar=False):
        '''
        if the attr_name is not available, item will not be indexed
        Args:
            attr_name: the attribute used as index
            files: a list of file items
            check_exist: only consider existing files, if True
        '''
        index = {}
        files = files if files is not None else list(self.index_id.values())

        if attr_name == 'name':
            attr_name = "image_name"
            msg = 'constructing name index...'
        elif attr_name == 'checksum':
            attr_name = "checksum"
            msg = 'constructing chechsum index...'
        elif attr_name == 'folder':
            attr_name = "folder"
            msg = 'constructing folder index...'
        else:
            return index

        if progressBar:
            progress = ProgressDiag(len(files), msg)
            progress.show()

        for item in files:
            if progressBar:
                progress.new_item('processed: ' + item.image_path())
                QCoreApplication.processEvents()
            if check_exist and not item.exists():
                continue
            attr = getattr(item, attr_name)()
            if attr is not None:
                if attr in index.keys():
                    index[attr].append(item)
                else:
                    index[attr] = [item]

        return index
    
    ## search missing images

    def search_image(self, folder):
        if os.path.exists(folder):
            files = self.get_files(folder)
            index_checksum = self.get_index('checksum', files, progressBar=True)

            progress = ProgressDiag(len(self.index_id), 'Seaching missing images...')
            progress.show()

            for _, item in self.index_id.items():
                progress.new_item('processed: ' + item.image_path())
                QCoreApplication.processEvents()
                if item.exists():
                    continue
                checksum = item.checksum()
                if checksum is not None and checksum in index_checksum.keys():
                    item.set_image_path(index_checksum[checksum][0].image_path())
    
    ## check duplicates

    def remove_duplicate(self):
        index_checksum = self.get_index('checksum')

        progress = ProgressDiag(len(index_checksum), 'Finding duplicates...')
        progress.show()

        for checksum, items in index_checksum.items():
            msg = 'processed: ' + checksum + ', '.join([s.image_name() for s in items])
            progress.new_item(msg)
            QCoreApplication.processEvents()
            if len(items) > 1:
                index_remain = 0
                for idx, item in enumerate(items):
                    if item.is_rel_path():
                        index_remain = idx
                        break
                for idx, item in enumerate(items):
                    if idx == index_remain:
                        continue
                    anno_merge(items[index_remain].annotation_path(), item.annotation_path())
                    self.remove_image(item.idx())

    ## collect/distribute annotations from/to file locations

    def collect(self):
        self.annotationMgr.save()
        op = annotation_move_message('Collect annotations', 'Would you like to merge or overwrite annotations files in the project?')
        if op != OP_CANCEL:
            if len(self.index_id) > 0:
                progress = ProgressDiag(len(self.index_id), 'Collecting images...')
                progress.show()
            for idx, item in self.index_id.items():
                image_path = item.image_path()
                anno_path = os.path.splitext(image_path)[0] + '.' + ANNOTATION_EXT
                if op == OP_MERGE:
                    anno_merge(item.annotation_path(), anno_path)
                elif op == OP_OVERWRITE:
                    shutil.copy(anno_path, item.annotation_path())
                progress.new_item('Collected from: ' + anno_path)
                self.set_status(idx, self.annotationMgr.get_status(item.annotation_path()))

    def distribute(self):
        self.annotationMgr.save()
        op = annotation_move_message('Distribute annotations', 'Would you like to merge or overwrite annotations files next to the image files?')
        if op != OP_CANCEL:
            if len(self.index_id) > 0:
                progress = ProgressDiag(len(self.index_id), 'Distributing images...')
                progress.show()
            for _, item in self.index_id.items():
                image_path = item.image_path()
                if os.path.isfile(image_path):
                    anno_path = os.path.splitext(image_path)[0] + '.' + ANNOTATION_EXT
                    if op == OP_MERGE:
                        anno_merge(anno_path, item.annotation_path())
                    elif op == OP_OVERWRITE:
                        shutil.copy(item.annotation_path(), anno_path)
                    progress.new_item('Distributed to: ' + anno_path)
                else:
                    progress.new_item('Image not found: ' + image_path)

    def merge(self, proj):
        self.annotationMgr.save()
        print('inn')
        op = annotation_move_message('Merge project', 'Would you like to merge or overwrite annotations?')
        print('innnnn', op)
        if op != OP_CANCEL and not os.path.samefile(self.proj_file, proj.proj_file):
            # merge folders
            for f in proj.index_folder.keys():
                if f not in self.index_folder.keys():
                    self.add_folder(f)
            # merge image items
            if len(proj.index_id) > 0:
                progress = ProgressDiag(len(proj.index_id), 'Merging project...')
                progress.show()
            for idx, item_src in proj.index_id.items():
                if idx in self.index_id.keys():
                    item_dst = self.index_id[idx]
                    checksum_src, checksum_dst = item_src.checksum(), item_dst.checksum()
                    if checksum_src is not None and checksum_src == checksum_dst:
                        if op == OP_MERGE:
                            anno_merge(item_dst.annotation_path(), item_src.annotation_path())
                            progress.new_item("Item overwritten: " + item_dst.image_path())
                        elif op == OP_OVERWRITE:
                            shutil.copy(item_src.annotation_path(), item_dst.annotation_path())
                            progress.new_item("Item merged: " + item_dst.image_path())
                        continue
                
                self.add_image(item_src.image_path(), item_src.folder())
                item_dst = self.index_id[idx]
                item_dst.set_status(item_src.status())
                shutil.copy(item_src.annotation_path(), item_dst.annotation_path())
                progress.new_item("Item added: " + item_dst.image_path())

class ProgressDiag(QDialog):
    def __init__(self, total, msg="", parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/importProgress.ui', baseinstance=self)
        self.setWindowTitle(msg)
        # self.setWindowModality(Qt.WindowModal)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.Desktop)
        self.progressBar.setValue(0)
        self.count = 0
        self.total = total
    
    def keyPressEvent(self, e):
        if e.key() != Qt.Key_Escape:
            super().keyPressEvent(e)
    
    def new_item(self, msg):
        self.count += 1
        self.fileList.addItem(msg)
        self.fileList.setCurrentRow(self.fileList.count()-1)
        if int(self.count*100/self.total) - self.progressBar.value() >= 1:
            self.progressBar.setValue(self.count*100/self.total)
        if self.count == self.total:
            self.progressBar.setValue(100)
            self.close() 
        QCoreApplication.processEvents()

