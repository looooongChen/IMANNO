import os 
import h5py

def anno_merge(file1, file2):
    '''
    merge content of file2 into file1
    '''
    if os.path.isfile(file1) and os.path.isfile(file2):
        with h5py.File(file1) as f1:
            with h5py.File(file2) as f2:
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
                if 'annotations' in f2:
                    if 'annotations' not in f2:
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


