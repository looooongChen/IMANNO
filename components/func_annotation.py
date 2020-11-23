import os 
import h5py
import shutil
import json
import numpy as np
from .enumDef import *
from .annotations import *

def read_anno_item_hdf(anno_item):
    anno_type = anno_item.attrs['type']
    if anno_type == 'polygon':
        return PolygonAnnotation.dataObject_from_hdf5(anno_item)
    elif anno_type == 'bouding box':
        return BBXAnnotation.dataObject_from_hdf5(anno_item)
    elif anno_type == 'oval':
        return EllipseAnnotation.dataObject_from_hdf5(anno_item)
    elif anno_type == 'point':
        return DotAnnotation.dataObject_from_hdf5(anno_item)
    elif anno_type == 'line':
        return CurveAnnotation.dataObject_from_hdf5(anno_item)
    else:
        return None

def save_anno_item_hdf(anno_item, anno_hdf):
    anno_grp = anno_hdf.require_group('/annotations/'+anno_item['timestamp'])
    anno_grp.attrs['timestamp'] = anno_item['timestamp']
    # save data
    anno_type = anno_item['type']
    if anno_type == POLYGON:
        anno_grp.attrs['type'] = 'polygon'
        bbx = np.array(anno_item['bbx'])
        anno_grp.create_dataset('boundingBox', shape=(4,), data=bbx)
        coords = np.array(anno_item['coords'])
        coords[:,0] -= anno_item['bbx'][0] 
        coords[:,1] -= anno_item['bbx'][1] 
        anno_grp.create_dataset('polygon', shape=coords.shape, data=coords)
    elif anno_type == BBX:
        anno_grp.attrs['type'] = 'bouding box'
        bbx = np.array(anno_item['bbx'])
        anno_grp.create_dataset('boundingBox', shape=(4,), data=bbx)
    elif anno_type == ELLIPSE:
        anno_grp.attrs['type'] = 'oval'
        coords = np.array(anno_item['coords'])
        anno_grp.create_dataset('center', shape=(2,), data=coords)
        angle = np.array(anno_item['angle'])
        anno_grp.create_dataset('angle', shape=(1,), data=angle)
        axis = np.array(anno_item['axis'])
        anno_grp.create_dataset('axis', shape=(2,), data=axis)
    elif anno_type == DOT:
        anno_grp.attrs['type'] = 'point'
        coords = np.array(anno_item['coords'])
        anno_grp.create_dataset('pt', shape=(2,), data=coords)
    elif anno_type == CURVE:
        anno_grp.attrs['type'] = 'line'
        bbx = np.array(anno_item['bbx'])
        anno_grp.create_dataset('boundingBox', shape=(4,), data=bbx)
        coords = np.array(anno_item['coords'])
        coords[:,0] -= bbx[0] 
        coords[:,1] -= bbx[1] 
        anno_grp.create_dataset('line', shape=coords.shape, data=coords)
    # save labels
    label_grp = anno_grp.require_group('labels')
    for prop, label in anno_item['labels'].items():
        label_grp.require_group(prop)
        label_grp[prop].attrs['label_name'] = label

def anno_read(anno_path):
    if not os.path.isfile(anno_path):
        return None
    if os.path.splitext(anno_path)[1] == '.hdf5':
        anno = {'status': 'unfinished',
                'labels': {},  
                'annotations': {}}
        with h5py.File(anno_path, 'r') as anno_hdf:
            # read status
            if 'status' in anno_hdf.attrs.keys():
                anno['status'] = anno_hdf.attrs['status']
            # read labels:
            if 'attributes' in anno_hdf:
                for prop, _ in anno_hdf['/attributes'].items():
                    anno['labels'][prop] = {}
                    for label, color in anno_hdf['attributes/'+prop].items():
                        anno['labels'][prop][label] = [int(c) for c in color]
            # read annotations
            if 'annotations' in anno_hdf.keys():
                for timestamp in anno_hdf['annotations']:
                    anno['annotations'][timestamp] = read_anno_item_hdf(anno_hdf['annotations'][timestamp])
    elif os.path.splitext(anno_path)[1] == ANNOTATION_EXT:
        with open(anno_path, mode='r') as f:
            anno = json.load(f)
    else:
        anno = None
    return anno

def anno_save(anno, anno_path):

    if os.path.splitext(anno_path)[1] == '.hdf5':
        with h5py.File(anno_path, 'w') as anno_hdf:
            # save status
            anno_hdf.attrs['status'] = anno['status']
            # read labels:
            prop_grp = anno_hdf.require_group('attributes')
            for prop, labels in anno['labels'].items():
                label_group = prop_grp.require_group(prop)
                for label, color in labels.items():
                    label_group.create_dataset(label, shape=(3,), dtype='uint8')
                    label_group[label][0] = color[0]
                    label_group[label][1] = color[1]
                    label_group[label][2] = color[2]
            # save annotations
            annotation_grp = anno_hdf.require_group('annotations')
            for _, anno_item in anno['annotations'].items():
                save_anno_item_hdf(anno_item, anno_hdf)
            anno_hdf.flush()
    elif os.path.splitext(anno_path)[1] == ANNOTATION_EXT:
        with open(anno_path, mode='w') as f:
            json.dump(anno, f)


def anno_copy(file1, file2):
    '''
    copy file2 to file1
    '''
    if os.path.splitext(file1)[1] == os.path.splitext(file2)[1]:
        shutil.copy(file2, file1)
    else:
        anno = anno_read(file2)
        anno_save(anno, file1)


def anno_merge(file1, file2):
    '''
    merge content of file2 into file1
    '''
    if not os.path.isfile(file1) and os.path.isfile(file2):
        anno_copy(file1, file2)
    
    anno1 = anno_read(file1)
    anno2 = anno_read(file2)

    # merge status
    s1, s2 = anno1['status'], anno2['status']
    if s1 == FINISHED or s2 == FINISHED:
        anno1['status'] = FINISHED
    if s1 == PROBLEM or s2 == PROBLEM:
        anno1['status'] = PROBLEM
    if s1 == CONFIRMED and s2 == CONFIRMED:
        anno1['status'] = CONFIRMED
    # merge labels
    for prop, labels in anno2['labels'].items():
        if prop not in anno1['labels'].keys():
            anno1['labels'][prop] = labels
        else:
            for label, color in anno2['labels'][prop].items():
                if label not in anno1['labels'][prop].keys():
                    anno1['labels'][prop][label] = color
    # merge annotations
    for timestamp, anno in anno2['annotations'].items():
        if timestamp not in anno1['annotations'].keys():
            anno1['annotations'][timestamp] = anno
        else:
            for prop, label in anno['labels'].items():
                if prop not in anno1['annotations'][timestamp]['labels'].keys():
                    anno1['annotations'][timestamp]['labels'][prop] = label
                # if label conflict happens
                elif anno1['annotations'][timestamp]['labels'][prop] != label:
                    del anno1['annotations'][timestamp]['labels'][prop]
    anno_save(anno1, file1)

def get_status(anno_path):
    status = UNFINISHED
    if os.path.isfile(anno_path):
        ## hdf5 compatible
        ext = os.path.splitext(anno_path)[1]
        if ext == '.hdf5':
            with h5py.File(anno_path, 'r') as location:
                if 'status' in location.attrs.keys():
                    status = location.attrs['status']
        if ext == ANNOTATION_EXT:
            with open(anno_path, mode='r') as f:
                anno = json.load(f)
                status = anno['status']
        return status


def anno_report(anno_path):
    total, stats = 0, {}
    if not os.path.isfile(anno_path):
        return total, stats
    ## hdf5 compatible
    ext = os.path.splitext(anno_path)[1]
    if ext == '.hdf5':
        with h5py.File(anno_path, 'r') as f:
            if 'annnotations' not in f.keys():
                return total, stats
            total = len(f['/annotations'])
            for k, _ in f['/annotations'].items():
                for prop, vv in f['annotations/'+k+'/labels'].items():
                    if prop not in stats.keys():
                        stats[prop] = {}
                    label = vv.attrs['label_name']
                    if label_name not in stats[kk].keys():
                        stats[prop][label] = 1
                    else:
                        stats[prop][label] += 1
    if ext == ANNOTATION_EXT:
        with open(anno_path, mode='r') as f:
            anno = json.load(f)
            total = len(anno['annotations'])
            for _, anno_item in anno['annotations'].items():
                for prop, label in anno_item['labels'].items():
                    if prop not in stats.keys():
                        stats[prop] = {}
                    if label not in stats[prop].keys():
                        stats[prop][label] = 1
                    else:
                        stats[prop][label] += 1

    return total, stats
