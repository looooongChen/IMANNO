from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsScene, QMessageBox  
from datetime import datetime as datim
import h5py
import json
import os

from .labelManager import LabelManager
from .annotations import *
from .canvas import Canvas

class AnnotationManager(object):
    def __init__(self, config, labelMgr, canvas=None):

        self.config = config
        self.status = UNFINISHED
        self.labelMgr = labelMgr
        self.annotations = {} # timestamp - Annotation object

        self.canvas = canvas

        self.saved = True # save status
        self.annotation_path = None
    
    def set_canvas(self, canvas):
        if isinstance(canvas, Canvas):
            self.canvas = canvas
    
    def set_status(self, status, annotation_path=None):
        if status in [FINISHED, UNFINISHED, CONFIRMED, PROBLEM]:
            if annotation_path is None:
                self.status = status
            elif isinstance(annotation_path, str) and annotation_path[-4:] == ANNOTATION_EXT:
                with h5py.File(annotation_path, 'a') as location:
                    location.attrs['status'] = status

    def get_status(self, annotation_path=None):
        if annotation_path is None:
            return self.status
        if os.path.isfile(annotation_path) and annotation_path[-4:] == ANNOTATION_EXT:
            with h5py.File(annotation_path, 'a') as location:
                if 'status' in location.attrs.keys():
                    return location.attrs['status']
                else:
                    return UNFINISHED
        else:
            return UNFINISHED


    ############################
    #### method for add new ####
    ############################

    def new_attribute(self, attr_name, label_list=None):
        if attr_name not in self.labels.keys():
            self.labels[attr_name] = Property(attr_name, label_list)
        else:
            print("Property has existed!")
        self.saved = False

    def new_label(self, attr_name, label_name, label_color=None):
        if attr_name in self.labels.keys():
            self.labels[attr_name].add_label(label_name, label_color)
        else:
            print("Property does not exist")

    def new_annotation(self, type, dataObject, skip_dlg=False):

        timestamp = datim.today().isoformat('@')
        while timestamp in self.annotations.keys():
            timestamp = datim.today().isoformat('@')

        if type == POLYGON:
            annotation = PolygonAnnotation(timestamp, dataObject)
        elif type == BBX:
            annotation = BBXAnnotation(timestamp, dataObject)
        elif type == OVAL:
            annotation = OVALAnnotation(timestamp, dataObject)
        elif type == POINT:
            annotation = PointAnnotation(timestamp, dataObject)
        elif type == LINE:
            annotation = LineAnnotation(timestamp, dataObject)
        else:
            print("Unknown annotation type")

        self.add_annotation(annotation, self.config['display_channel'])
        self.saved = False
    
    def add_annotation(self, annotation, display_channel=None):
        self.annotations[annotation.timestamp] = annotation
        if self.canvas is not None:
            self.canvas.add_graphItem(annotation, display_channel)


    def add_label_to_selected_annotations(self, label_name, attr_name):

        if attr_name not in (self.labels.keys()):
            return
        if label_name not in list(self.labels[attr_name].labels.keys()):
            return
        annotations = self.get_selected_annotations()
        if annotations:
            for annotation in annotations:
                label_obj = self.labels[attr_name].labels[label_name]
                annotation.add_label(label_obj)
            self.saved = False

    ############################
    #### methods for get ####
    ############################

    def get_annotation_by_graphItem(self, graphItem):
        for timestamp, item in self.annotations.items():
            if graphItem is item.graphObject:
                return self.annotations[timestamp]
        return None

    def get_selected_annotations(self):
        if self.canvas is None:
            return None
        if len(self.canvas.selectedItems) == 0:
            return None
        annotations = []
        for item in self.canvas.selectedItems:
            anno = self.get_annotation_by_graphItem(item)
            if anno is not None:
                annotations.append(anno)
        return annotations

    ############################
    #### methods for remove ####
    ############################

    def delete_annotation_by_graphItem(self, graphItem):
        timestamp = [timestamp for timestamp, item in self.annotations.items() if graphItem is item.graphObject]
        if len(timestamp) > 0:
            del self.annotations[timestamp[0]]
        if self.canvas is not None:
            self.canvas.removeItem(graphItem)
        self.saved = False

    def remove_label(self, label, attr_name=None):
        if attr_name is None:
            assert isinstance(label, Label)
            label_obj = label
            attr_name = label.attr_name
        elif attr_name in list(self.labels.keys()):
            label_obj = self.labels[attr_name].get_label(label)
        else:
            return
        self._remove_label_from_all_annotations(label_obj)
        self.labels[attr_name].remove_label(label_obj)

        self.saved = False

    def remove_label_from_selected_annotation(self, label_name, attr_name):
        if attr_name not in (self.labels.keys()):
            return
        if label_name not in list(self.labels[attr_name].labels.keys()):
            return
        annotations = self.get_selected_annotations()
        if annotations:
            annotation = annotations[0]
            label_obj = self.labels[attr_name].labels[label_name]
            annotation.remove_label(label_obj)
            self.saved = False

    def remove_attr(self, attr):
        if isinstance(attr, Property):
            attr_name = attr.attr_name
            attr_obj = attr
        elif attr in list(self.labels.keys()):
            attr_name = attr
            attr_obj = self.labels[attr]
        else:
            return
        for label_obj in attr_obj.labels.values():
            self._remove_label_from_all_annotations(label_obj)
        del self.labels[attr_name]

        self.saved = False

    def _remove_label_from_all_annotations(self, label_obj):
        for timestamp in self.annotations.keys():
            self.annotations[timestamp].remove_label(label_obj)

    ############################
    #### methods for rename ####
    ############################

    def rename_label(self, name, label, attr_name=None):
        if isinstance(label, Label):
            label.rename(name)
        elif attr_name in self.labels.keys():
            label = self.labels[attr_name].get_label(label)
            if label is not None:
                label.rename(name)
        self.saved = False

    def rename_property(self, prop, new_name):
        if prop in self.labels.keys() and new_name not in self.labels.keys():
            self.labels[new_name] = self.labels.pop(prop)


    #########################
    #### annotation save ####
    #########################


    def save(self, inquiry=True):
        if not self.saved:
            save = QMessageBox.Yes == QMessageBox.question(None, "Important...", "Would you like to save the changes in your annotations?", QMessageBox.Yes | QMessageBox.No) if inquiry else True
            if save and self.annotation_path is not None:
                self.save_to_file(self.annotation_path)

    def save_to_file(self, filename):

        if self.saved is True or filename is None:
            return

        anno_file = {'status': self.status,
                     'labels': self.labelMgr.render_save(),
                     'annotations': {}}
        for timestamp, anno in self.annotations.items():
            anno_file['annotations'][timestamp] = anno.render_save()

        with open(filename, 'w') as f:
            json.dump(anno_file, f)

        self.saved = True

    def close(self):
        self.labels = {} 
        self.annotations = {}
        self.saved = True
        self.annotation_path = None

    ##########################
    #### annotation load #####
    ##########################


    def load(self, annotation_path):

        if annotation_path is not None:
            self.annotation_path = annotation_path

            self.saved = True
            self.labels.clear()
            self.annotations.clear()

            ## hdf5 compatible
            ext = os.path.splitext(annotation_path)[-1]
            if ext == '.hdf5':
                with h5py.File(annotation_path, 'a') as location:
                    # load annotation status
                    if 'status' in location.attrs.keys():
                        self.status = location.attrs['status']
                    # load attritubutes and labels
                    self.labelMgr.parse_labels(location, mode='hdf5') 
                    # load annotations
                    if 'annotations' in location.keys():
                        for timestamp in location['annotations']:
                            annotation = self._load_annotation(location['annotations'][timestamp], mode='hdf5')
                            if annotation is not None:
                                self.add_annotation(annotation)

                    location.flush()
                    location.close()
            else:
                with open(annotation_path, mode='r') as f:
                    anno_file = json.load(f)
                    # load status
                    self.status = anno_file['status']
                    # load property and label list
                    self.labelMgr.parse_labels(anno_file['labels']) 
                    # load annotations
                    for timestamp, anno in anno_file['annotations'].items():
                        annotation = self._load_annotation(anno)
                        if annotation is not None:
                            self.add_annotation(annotation)

            print('Annotation loaded:', annotation_path)

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
            return DotAnnotation(timestamp, anno, self.labelMgr)
        elif anno_type == CURVE:
            return CurveAnnotation(timestamp, anno, self.labelMgr)
        else:
            print("Unknown annotation type")
            return None

    #################
    #### display ####
    #################

    def appearance(self, anno, display_channel):
        if isinstance(display_channel, str):
            for label in anno.labels:
                if display_channel == label.attr_name:
                    c = label.color
                    linePen = QPen(QColor(c[0], c[1], c[2], 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    areaBrush = QBrush(QColor(c[0], c[1], c[2], 70))
                    if anno.type == LINE:
                        linePen.setWidth(int(self.config['lineAnnotationWidth']))
                    return linePen, areaBrush
            linePen = QPen(QColor(0, 0, 0, 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 0, 0, 70))
        elif display_channel == HIDE_ALL:
            linePen = QPen(QColor(0, 0, 0, 0), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 0, 0, 0))
        else: # SHOW_ALL
            linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 200, 0, 70))
        
        if anno.type == LINE:
            linePen.setWidth(int(self.config['lineAnnotationWidth']))
            areaBrush = QBrush(QColor(0, 200, 0, 0))

        return linePen, areaBrush










