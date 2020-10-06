import os
import json
from datetime import date
from .image import compute_checksum, Image
from .enumDef import *
import glob
import shutil
from pathlib import Path
from .func_annotation import *

ITEM = {'id': None, 'name': None, 'ext': None, 'checksum': None, 'image_path': None, 'rel_path': False, 'annotation_path': None, 'status': MARKER}

class Project(object):
    def __init__(self, annotationMgr=None):
        self.set_annotationMgr(annotationMgr)
        self.project_name = None
        self.project_dir = None
        self.project_file = None
        self.annotation_dir = None
        self.data = {}
        self.index_id = {}
        # self.index_checksum = {}
        self.idx = 0
        self.project_open = False

    def set_annotationMgr(self, annotationMgr):
        self.annotationMgr = annotationMgr
    
    def is_open(self):
        return self.project_open

    def open(self, path):
        '''
        path to the project directory / project file
        '''
        if os.path.splitext(path)[1] == '.improj':
            self.project_dir = os.path.abspath(os.path.realpath(os.path.dirname(path))) 
            self.project_file = path
        else:
            self.project_dir = os.path.abspath(os.path.realpath(path))
            f = glob.glob(os.path.join(path, '*.improj'))
            if len(f) > 0:
                self.project_file = f[0]
            else:
                self.project_file = os.path.join(path, os.path.basename(path)+'.improj')
        # create directories when necessary
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)
        self.annotation_dir = os.path.join(self.project_dir, 'annotations')
        if not os.path.exists(self.annotation_dir):
            os.makedirs(self.annotation_dir)
        # load project file if exists
        if not os.path.exists(self.project_file):
            self.data = {'project_name': os.path.basename(self.project_file)[:-7]}
        else:
            with open(self.project_file) as json_file:
                self.data = json.load(json_file)
            self.index_id = {e['id']: e for e in self.data['images'] if e['id'] is not None}
        self.project_name = self.data['project_name']
        # compute current idx
        ids = [int(idx) for idx in self.index_id.keys()]
        self.idx = max(ids) + 1 if len(ids) != 0 else 0
        self.project_open = True

    def close(self):
        self.annotationMgr.save()
        self.save()
        self.project_name = None
        self.project_dir = None
        self.project_file = None
        self.annotation_dir = None
        self.data = {}
        self.index_id = {}
        # self.index_checksum = {}
        self.idx = 0
        self.project_open = False
    
    def save(self):
        if self.is_open():
            self.data['images'] = []
            for item in self.index_id.values():
                self.data['images'].append(item)
            with open(self.project_file, 'w') as outfile:
                json.dump(self.data, outfile, indent=4)

    def add_images(self, images):
        idxs, fnames = [], []
        for img in images:
            idx, fname = self.add_image(img)
            if idx is not None:
                idxs.append(idx)
                fnames.append(fname)
        return idxs, fnames
    
    def add_image(self, image_path):
        if image_path not in self.index_id.keys():
            item = ITEM.copy()
            item['id'] = '{:08d}'.format(self.idx)
            self.idx += 1
            # add image path
            self.set_item_image_path(item, image_path)
            self.index_id[item['id']] = item
            # add annotation path
            self.set_annotation_path(item['id'])
            # set checksum
            self.set_checksum(item['id'], item['image_path'])
            return item['id'], item['name']
        else:
            return None, None

    def remove_image(self, idx):
        if os.path.exists(os.path.join(self.project_dir, 'annotations', idx)):
            shutil.rmtree(os.path.join(self.project_dir, 'annotations', idx))
        if self.index_id[idx]['annotation_path'] == self.annotationMgr.annotation_file:
            self.annotationMgr.close()
        # check_sum = self.index_id[idx]['checksum']
        del self.index_id[idx]
    
    def filenames(self, check_exist=False):
        fnames, ids, status, exist = [], [], [], []
        for idx, e in self.index_id.items():
            ids.append(idx)
            fnames.append(e['name']+e['ext'])
            status.append(e['status'])
            if check_exist:
                exist.append(os.path.exists(self.get_item_image_path(e)))
            else:
                exist.append(True)
        return fnames, ids, status, exist

    ## image path setter and getter

    def set_item_image_path(self, item, path):
        path = os.path.abspath(os.path.realpath(path))
        if path.startswith(self.project_dir):
            item['rel_path'] = True
            path = os.path.relpath(path, start=self.project_dir)
        item['image_path'] = path
        item['name'], item['ext'] = os.path.splitext(os.path.basename(path))

    def get_item_image_path(self, item):
        if item['rel_path']:
            return os.path.join(self.project_dir, item['image_path'])
        else:
            return item['image_path']

    def set_image_path(self, id, path):
        if id in self.index_id.keys():
            self.set_item_image_path(self.index_id[id], path)

    def get_image_path(self, id):
        if id in self.index_id.keys():
            return self.get_item_image_path(self.index_id[id])
        else:
            return None
    
    def get_image_name(self, id):
        if id in self.index_id.keys():
            return self.index_id[id]['name'] + self.index_id[id]['ext'] 
        else:
            return None

    ## annotation path setter and getter

    def set_annotation_path(self, id):
        if id in self.index_id.keys():
            anno_dir = os.path.join(self.project_dir, 'annotations', id)
            if not os.path.exists(anno_dir):
                os.makedirs(anno_dir)
            self.index_id[id]['annotation_path'] = os.path.join('annotations', id, 'anno.'+ANNOTATION_EXT)
    
    def get_annotation_path(self, id):
        if id in self.index_id.keys():
            return os.path.join(self.project_dir, self.index_id[id]['annotation_path'])
        else:
            return None
    
    ## chechsum setter and getter
    
    def set_checksum(self, id, image):
        '''
        Args:
            id: image item id
            image: object of class components.image.Image / image path (string)
        '''
        if id in self.index_id.keys():
            if isinstance(image, Image):
                self.index_id[id]['checksum'] = image.get_checksum()
            else:
                self.index_id[id]['checksum'] = compute_checksum(image)

    def get_checksum(self, id):
        return self.index_id[id]['checksum'] if id in self.index_id.keys() else None

    ## status setter and getter

    def set_status(self, id, status):
        if id in self.index_id.keys():
            self.index_id[id]['status'] = status

    def get_status(self, id):
        return self.index_id[id]['status'] if id in self.index_id.keys() else None

    ## compute index
    
    def get_name_index(self, files=None, check_exist=False):
        index_name = {}
        if files is not None:
            file_items = []
            for f in files:
                name, ext = os.path.splitext(os.path.basename(f))
                item = ITEM.copy()
                item['name'], item['ext'], item['image_path'] = name, ext, f
                file_items.append(item)
        else:
            file_items = list(self.index_id.items)

        for item in file_items:
            if check_exist and not os.path.isfile(item['image_path']):
                continue
            if item['name'] in index_name.keys():
                index_name[item['name']].append(item)
            else:
                index_name[item['name']] = [item]

        return index_name
    
    def get_checksum_index(self, files=None, check_exist=False):
        index_checksum = {}
        for _, item in self.index_id.items():
            if item['checksum'] is None:
                self.set_checksum(item['id'], self.get_item_image_path(item))
            if item['checksum'] is not None:
                if item['checksum'] in index_checksum.keys():
                    index_checksum[item['checksum']].append(item)
                else:
                    index_checksum[item['checksum']] = [item]
        return index_checksum
    
    ## reimport images

    def reimport_image(self, folder):
        if os.path.exists(folder):
            # project item match imported file
            files = [str(path) for t in IMAGE_TYPES for path in Path(folder).rglob(t)]
            index_name = self.get_name_index(files)
            for _, item in self.index_id.items():
                if os.path.isfile(item['image_path']):
                    continue
                name = item['name']
                if name in index_name.keys():
                    if len(index_name[name]) == 1:
                        self.set_item_image_path(item, index_name[name][0]['image_path'])
                    else:
                        if item['checksum'] is None:
                            continue
                        for candidate in index_name[name]:
                            if candidate['checksum'] is None:
                                candidate['checksum'] = compute_checksum(candidate['image_path'])
                            if item['checksum'] == candidate['checksum']:
                                self.set_item_image_path(item, candidate['image_path'])
            # imported files match project files

    
    ## check duplicates

    def check_duplicate(self):
        index_checksum = self.get_checksum_index()
        for items in index_checksum.values():
            if len(items) > 1:
                index_remain = 0
                for idx, item in enumerate(items):
                    if item['rel_path']:
                        index_remain = idx
                        break
                for idx, item in enumerate(items):
                    if idx == index_remain:
                        continue
                    anno_merge(items[index_remain]['annotation_path'], item['annotation_path'])
                    self.remove_image(item['id'])


                            



