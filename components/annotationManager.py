from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsScene, QMessageBox  
import h5py
import json
import os

from .base import Table
from .annotations import *
from .canvas import Canvas

class AnnotationManager(Table):
    def __init__(self, config, labelMgr, canvas=None):
        super().__init__()

        self.config = config
        self.labelMgr = labelMgr
        self.canvas = canvas

        self.status = UNFINISHED
        self.annotation_path = None
        self.index_graphItem = {}
    
    def set_canvas(self, canvas):
        if isinstance(canvas, Canvas):
            self.canvas = canvas

    def clear(self):
        if self.canvas is not None:
            self.canvas.clear()
        super().clear()
        self.labelMgr.clear()

    def get_annotation_by_graphItem(self, graphItem):
        if graphItem in self.index_graphItem.keys():
            return self.index_graphItem[graphItem]
        else:
            return None

    ##########################
    #### get / set status ####
    ##########################
    
    def set_status(self, status, annotation_path=None):
        if status in [FINISHED, UNFINISHED, CONFIRMED, PROBLEM]:
            if annotation_path is None:
                self.status = status
            elif os.path.isfile(annotation_path):
                with open(annotation_path, "r") as f:
                    anno_file = json.load(f)
                anno_file['status'] = status
                with open(annotation_path, "w") as f:
                    json.dump(anno_file, f)

    def get_status(self, annotation_path=None):
        if annotation_path is None:
            return self.status
        status = UNFINISHED
        if os.path.isfile(annotation_path):
            ext = os.path.splitext(annotation_path)[1]
            ## hdf5 compatible
            if ext == '.hdf5':
                with h5py.File(annotation_path, 'r') as anno_file:
                    if 'status' in anno_file.attrs.keys():
                        status = anno_file.attrs['status']
            if ext == ANNOTATION_EXT:
                with open(annotation_path, mode='r') as f:
                    anno_file = json.load(f)
                    if 'status' in anno_file.keys():
                        status = anno_file['status']    
        return status


    ##########################################
    #### method for annotation management ####
    ##########################################

    def new_annotation(self, dataObject):

        anno_type = dataObject['type']
        timestamp = dataObject['timestamp']
        if anno_type == POLYGON:
            anno = PolygonAnnotation(timestamp, dataObject, self.labelMgr)
        elif anno_type == BBX:
            anno = BBXAnnotation(timestamp, dataObject, self.labelMgr)
        elif anno_type == ELLIPSE:
            anno = EllipseAnnotation(timestamp, dataObject, self.labelMgr)
        elif anno_type == DOT:
            anno = DotAnnotation(timestamp, dataObject, self.labelMgr)
            # anno.adjust_graphObject(self.config['DotAnnotationRadius'])
        elif anno_type == CURVE:
            anno = CurveAnnotation(timestamp, dataObject, self.labelMgr)
        else:
            print("Unknown annotation type")
            return

        self.add_annotation(anno)
        self.config.saved = False
    
    def add_annotation(self, anno, graphItem=True):
        self[anno.timestamp] = anno
        self.index_graphItem[anno.graphObject] = anno
        if self.canvas is not None and graphItem:
            self.canvas.add_item(anno)
            anno.sync_disp(self.config)
    
    def remove_annotation(self, anno):
        if anno.timestamp in self.keys():
            if self.canvas is not None:
                self.canvas.removeItem(anno.graphObject)
            del self[anno.timestamp]
            del self.index_graphItem[anno.graphObject]
            self.config.saved = False
        
    def remove_annotation_by_graphItem(self, graphItem):
        if graphItem in self.index_graphItem.keys():
            self.remove_annotation(self.index_graphItem[graphItem])

    #########################
    #### annotation save ####
    #########################

    def save(self, inquiry=True):
        if not self.config.saved and self.annotation_path is not None:
            save = QMessageBox.Yes == QMessageBox.question(None, "Important...", "Would you like to save the changes in your annotations?", QMessageBox.Yes | QMessageBox.No) if inquiry else True
            if save and self.annotation_path is not None:
                self.save_to_file(self.annotation_path)
            self.config.saved = True

    def save_to_file(self, filename):

        if self.config.saved is False:
            anno_file = {'status': self.status,
                         'labels': self.labelMgr.render_save(),
                         'annotations': {}}
            for timestamp, anno in self.items():
                anno_file['annotations'][timestamp] = anno.render_save()
            with open(filename, 'w') as f:
                json.dump(anno_file, f)

            self.config.saved = True

    def close(self):
        self.clear()
        self.labelMgr.clear()
        self.config.saved = True
        self.annotation_path = None

    ##########################
    #### annotation load #####
    ##########################

    def load(self, annotation_path, graphItem=True):

        if self.config.saved is False:
            self.save(inquiry=True)

        ## hdf5 
        fname, ext = os.path.splitext(annotation_path)
        if not os.path.isfile(annotation_path) and ext == ANNOTATION_EXT:
            self.load(fname  + '.hdf5')
            self.annotation_path = annotation_path
            self.config.saved = False
            self.save(inquiry=False)
            if os.path.isfile(fname  + '.hdf5'):
                os.remove(fname  + '.hdf5')
        
        if os.path.isfile(annotation_path):
            self.annotation_path = annotation_path
            self.clear()

            ## hdf5 compatible
            if ext == '.hdf5':
                with h5py.File(annotation_path, 'r') as location:
                    # load annotation status
                    if 'status' in location.attrs.keys():
                        self.status = location.attrs['status']
                    # load attritubutes and labels
                    self.labelMgr.parse_labels(location, increment=False, mode='hdf5') 
                    # load annotations
                    if 'annotations' in location.keys():
                        for timestamp in location['annotations']:
                            annotation = self._load_annotation(location['annotations'][timestamp], mode='hdf5')
                            if annotation is not None:
                                self.add_annotation(annotation, graphItem)

                    location.flush()
                    location.close()
            else:
                with open(annotation_path, mode='r') as f:
                    anno_file = json.load(f)
                    # load status
                    self.status = anno_file['status']
                    # load property and label list
                    self.labelMgr.parse_labels(anno_file['labels'], increment=False) 
                    # load annotations
                    for timestamp, anno in anno_file['annotations'].items():
                        annotation = self._load_annotation(anno)
                        if annotation is not None:
                            self.add_annotation(annotation, graphItem)

    def _load_annotation(self, anno, mode='json'):

        ## hdf5 compatible
        if mode == 'hdf5':
            anno_type = anno.attrs['type']
            if anno_type == 'polygon':
                anno = PolygonAnnotation.dataObject_from_hdf5(anno)
            elif anno_type == 'bouding box':
                anno = BBXAnnotation.dataObject_from_hdf5(anno)
            elif anno_type == 'oval':
                anno = EllipseAnnotation.dataObject_from_hdf5(anno)
            elif anno_type == 'point':
                anno = DotAnnotation.dataObject_from_hdf5(anno)
            elif anno_type == 'line':
                anno = CurveAnnotation.dataObject_from_hdf5(anno)
            else:
                print("Unknown annotation type")
                return None

        anno_type = anno['type']
        timestamp = anno['timestamp']
        if anno_type == POLYGON:
            return PolygonAnnotation(timestamp, anno, self.labelMgr)
        elif anno_type == BBX:
            return BBXAnnotation(timestamp, anno, self.labelMgr)
        elif anno_type == ELLIPSE:
            return EllipseAnnotation(timestamp, anno, self.labelMgr)
        elif anno_type == DOT:
            anno = DotAnnotation(timestamp, anno, self.labelMgr)
            # anno.adjust_graphObject(self.config['DotAnnotationRadius'])
            return anno
        elif anno_type == CURVE:
            return CurveAnnotation(timestamp, anno, self.labelMgr)
        else:
            print("Unknown annotation type")
            return None

