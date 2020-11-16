import os 
import h5py
import shutil
from .enumDef import *

def anno_merge(file1, file2):
    '''
    merge content of file2 into file1
    '''
    if not os.path.isfile(file1) and os.path.isfile(file2):
        shutil.copy(file2, file1)
    if os.path.isfile(file1) and os.path.isfile(file2):
        with h5py.File(file1, 'a') as f1:
            with h5py.File(file2, 'a') as f2:
                # status
                if 'status' in f1.attrs.keys() and 'status' in f2.attrs.keys():
                    s1, s2 = f1.attrs['status'], f2.attrs['status']
                    if s1 == FINISHED or s2 == FINISHED:
                        f1.attrs['status'] = FINISHED
                    if s1 == PROBLEM or s2 == PROBLEM:
                        f1.attrs['status'] = PROBLEM
                    if s1 == CONFIRMED and s2 == CONFIRMED:
                        f1.attrs['status'] = CONFIRMED
                # merge attritbutes
                if 'attributes' in f2:
                    if 'attributes' not in f1:
                        f2.copy('/attributes', f1)
                    else:
                        for k, v in f2['/attributes'].items():
                            if k not in f1['/attributes']:
                                v.copy(v, f1['/attributes'])
                            else:
                                for kk, vv in f2['attributes/'+k].items():
                                    if kk not in f1['/attributes/'+k]:
                                        vv.copy(vv, f1['/attributes/'+k])
                # merge annotations
                if 'annotations' in f2:
                    if 'annotations' not in f1:
                        f2.copy('/annotations', f1)
                    else:
                        for k, v in f2['/annotations'].items():
                            if k not in f1['/annotations']:
                                v.copy(v, f1['/annotations'])
                            else:
                                for kk, vv in f2['annotations/'+k+'/labels'].items():
                                    if kk not in f1['annotations/'+k+'/labels']:
                                        vv.copy(vv, f1['annotations/'+k+'/labels'])
                                    elif f1['annotations/'+k+'/labels/'+kk].attrs['label_name'] != f2['annotations/'+k+'/labels/'+kk].attrs['label_name']:
                                        # if label conflict happens
                                        del f1['annotations/'+k+'/labels/'+kk]

def get_status(annotation_path):
    if os.path.isfile(annotation_path) and annotation_path[-4:] == ANNOTATION_EXT:
        with h5py.File(annotation_path, 'a') as location:
            if 'status' in location.attrs.keys():
                return location.attrs['status']
            else:
                return UNFINISHED


def anno_report(file):
    stats = {}
    if not os.path.isfile(file):
        return 0, stats
    with h5py.File(file, 'r') as f:
        if not 'annotations' in f:
            return 0, stats
        for k, _ in f['/annotations'].items():
            for kk, vv in f['annotations/'+k+'/labels'].items():
                if kk not in stats.keys():
                    stats[kk] = {}
                label_name = vv.attrs['label_name']
                if label_name not in stats[kk].keys():
                    stats[kk][label_name] = 1
                else:
                    stats[kk][label_name] += 1
        return len(f['/annotations']), stats


