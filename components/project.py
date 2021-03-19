from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog
from .image import compute_checksum, Image
from .func_annotation import *
from .messages import annotation_move_message, ProgressDiag
from .enumDef import *
from .contour import *
import uuid
from datetime import datetime as datim
import copy

from time import sleep
from pathlib import Path
import glob
import shutil
import json
import os
import csv

PROJ = {'project_name': '', 'folders': [], 'images': []}
ITEM = {'idx': None, 'name': None, 'ext': None, 'checksum': None, 'image_path': None, 'rel_path': False, 'annotation_path': None, 'status': UNFINISHED, 'folder': None}

class Item(object):

    def __init__(self, proj_dir=None):    
        self.data = ITEM.copy()
        if isinstance(proj_dir, str):
            self.proj_dir = proj_dir.replace('\\', '/') 
        else:
            self.proj_dir = proj_dir
    
    @classmethod
    def create(cls, data_dict, proj_dir):
        obj = cls(proj_dir)
        obj.data = data_dict
        obj.data['image_path'] = obj.data['image_path'].replace('\\', '/') 
        # obj.data['annotation_path'] = obj.data['annotation_path'].replace('\\', '/') 
        return obj
    
    def idx(self):
        return self.data['idx']

    def set_idx(self, idx):
        self.data['idx'] = idx
        # self.set_annotation_path()
        anno_dir = os.path.join(self.proj_dir, 'annotations', idx)
        if not os.path.exists(anno_dir):
            os.makedirs(anno_dir)
    
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
        self.data['image_path'] = path.replace('\\', '/') 
        self.data['name'], self.data['ext'] = os.path.splitext(os.path.basename(path))
        self.set_checksum()

    def image_path(self):
        if self.data['image_path'] is not None:
            path = self.data['image_path'].replace('\\', '/')
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

    # def set_annotation_path(self):
    #     if self.data['idx'] is not None:
    #         anno_dir = os.path.join(self.proj_dir, 'annotations', self.data['idx'])
    #         if not os.path.exists(anno_dir):
    #             os.makedirs(anno_dir)
    #         self.data['annotation_path'] = os.path.join('annotations', self.data['idx'], 'anno'+ANNOTATION_EXT).replace('\\', '/') 
    #         anno_path = os.path.join(self.proj_dir, self.data['annotation_path'])
    
    def annotation_path(self):
        if self.data['idx'] is not None:
            # return os.path.join(self.proj_dir, self.data['annotation_path'])
            return os.path.join(self.proj_dir, 'annotations', self.data['idx'], 'anno'+ANNOTATION_EXT)
        else:
            return None

    def annotation_dir(self):
        if self.data['idx'] is not None:
            # return os.path.join(self.proj_dir, 'annotations', self.data['idx'])
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
                # with h5py.File(anno_path, 'a') as location:
                #     location.attrs['status'] = status
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
        self.proj_file = None
        self.annotation_dir = None
        self.data = {}
        self.index_id = {}
        self.index_folder = {}
        # self.index_checksum = {}
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
        self.project_open = True

    def close(self):
        if self.project_open:
            if self.annotationMgr is not None:
                self.annotationMgr.save()
            self.save()
        self.project_name = None
        self.proj_dir = None
        self.proj_file = None
        self.annotation_dir = None
        self.data = {}
        self.index_id = {}
        self.index_folder = {}
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
        if folder_name is not None and folder_name not in self.index_folder.keys():
            self.index_folder[folder_name] = []
    
    def delete_folder(self, folder_name, remove_image=True):
        if folder_name in self.index_folder.keys():
            # do not call self.remove_image for faster speed
            for item in self.index_folder[folder_name]:
                if remove_image:
                    if self.annotationMgr is not None and item.annotation_path() == self.annotationMgr.annotation_path:
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
        idx = uuid.uuid4().hex
        # set idx (annotation is also set here) 
        item.set_idx(idx) 
        # add image path (checksum is also set here)  
        item.set_image_path(image_path)
        # copy annotation file if exist 
        ## hdf5 compatible
        annotation_json = os.path.splitext(image_path)[0] + ANNOTATION_EXT
        annotation_hdf5 = os.path.splitext(image_path)[0] + '.hdf5'
        if os.path.isfile(annotation_json):
            item.set_status(get_status(annotation_json))
            anno_copy(item.annotation_path(), annotation_json)
        elif os.path.isfile(annotation_hdf5):
            item.set_status(get_status(annotation_json))
            anno_copy(item.annotation_path(), annotation_hdf5)
        # update index
        self.index_id[idx] = item
        self.add_folder(folder)
        if folder in self.index_folder.keys():
            item.set_folder(folder)
            self.index_folder[folder].append(item)
        return idx

    def remove_image(self, idx):
        if idx in self.index_id.keys():
            item = self.index_id[idx]
            if self.annotationMgr is not None and item.annotation_path == self.annotationMgr.annotation_path:
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
            if self.annotationMgr is not None and self.index_id[idx].annotation_path() == self.annotationMgr.annotation_path:
                self.annotationMgr.set_status(status)

    def get_status(self, idx):
        if idx in self.index_id.keys():
            return self.index_id[idx].status()
        else:
            return None

    ## compute index

    def get_files(self, folder, progressBar=False):
        files = []
        fnames = [str(path) for t in IMAGE_TYPES for path in Path(folder).rglob(t)]
        if progressBar:
            progress = ProgressDiag(len(fnames), 'Retrieving images...')
            progress.show()
        for f in fnames:
            if progressBar:
                progress.new_item('retrieved image: ' + f)
                # QCoreApplication.processEvents()
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
                # QCoreApplication.processEvents()
            if check_exist and not item.exists():
                continue
            attr = getattr(item, attr_name)()
            if attr is not None:
                if attr in index.keys():
                    index[attr].append(item)
                else:
                    index[attr] = [item]

        return index

    ## dataset report

    def report(self):
        if self.is_open():
            progress = ProgressDiag(len(self.index_id), 'Counting...')
            progress.show()

            total, stats = 0, {}
            for _, item in self.index_id.items():
                t, s = anno_report(item.annotation_path())
                progress.new_item('Counted: ' + item.image_path())
                total += t
                for k, v in s.items():
                    if k not in stats.keys():
                        stats[k] = {}
                    for kk, vv in v.items():
                        if kk not in stats[k].keys():
                            stats[k][kk] = vv
                        else:
                            stats[k][kk] += vv
        return total, stats        

    
    ## search missing images

    def search_image(self, folder):
        if os.path.exists(folder):
            files = self.get_files(folder, progressBar=True)
            index_checksum = self.get_index('checksum', files, progressBar=True)

            progress = ProgressDiag(len(self.index_id), 'Seaching missing images...')
            progress.show()

            for _, item in self.index_id.items():
                progress.new_item('processed: ' + item.image_path())
                # QCoreApplication.processEvents()
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
            # QCoreApplication.processEvents()
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

    ## export image list

    def export_image_list(self, path=None):
        if path is None:
            path = QFileDialog.getExistingDirectory(caption='Select Export Directory')
            if len(path) == 0:
                return
        with open(os.path.join(path, 'image_list.csv'), mode='w', newline='') as files:
            file_writer = csv.writer(files, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for idx, item in self.index_id.items():
                img_path = item.image_path()
                print(img_path)
                file_writer.writerow([idx, img_path])

    ## import seg list

    def import_seg_list(self, path):
        if path is None:
            seg_list = QFileDialog.getOpenFileName(caption='Select Segmentation List', filter="csv(*.csv)")[0]
        if len(seg_list) != 0:
            if self.annotationMgr is not None:
                self.annotationMgr.save()
            with open(seg_list, newline='') as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                examples = [e for e in csv_reader]
                progress = ProgressDiag(len(examples), 'Importing segmentations...')
                progress.show()
                for row in examples:
                    k, seg_path = row[0], row[1]
                    progress.new_item("processed: "+seg_path)
                    if k in self.index_id.keys() and os.path.isfile(seg_path):
                        # read annotations
                        anno_path = self.index_id[k].annotation_path()
                        with open(anno_path) as json_file:
                            anno = json.load(json_file)
                        k_anno, contours_anno = [], []
                        anno['labels']['IMPORT'] = {
                            'False Postive': IMPORT_FP,
                            'Checked': IMPORT_CHECKED,
                            'False Negative': IMPORT_FN,
                        }
                        for k, item in anno['annotations'].items():
                            if item['type'] == POLYGON: 
                                if 'IMPORT' not in item['labels'].keys():
                                    item['labels']['IMPORT'] = 'False Negative'
                                k_anno.append(k)
                                contours_anno.append(np.array(item['coords']))
                        # read image
                        seg = cv2.imread(seg_path, cv2.IMREAD_UNCHANGED)
                        contours_seg = mask2contour(seg)
                        match = match_contours(contours_seg, contours_anno)
                        for idx_seg, idx_anno in enumerate(np.argmax(match, axis=1)):
                            if match[idx_seg, idx_anno] > IMPORT_MATCH_DICE:
                                anno['annotations'][k_anno[idx_anno]]['labels']['IMPORT'] = 'Checked'
                            else:
                                data = {'timestamp': datim.today().isoformat('@'),  
                                        'type': POLYGON,  
                                        'labels': {'IMPORT': 'False Postive'},  
                                        'coords': contours_seg[idx_seg].tolist(),
                                        'bbx': list(cv2.boundingRect(contours_seg[idx_seg]))}
                                print(data['timestamp'])
                                anno['annotations'][data['timestamp']] = copy.deepcopy(data)
                                sleep(0.0001)
                        with open(anno_path, 'w') as f:
                            json.dump(anno, f)
                        







