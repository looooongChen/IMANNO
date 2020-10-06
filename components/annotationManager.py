from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsScene, QMessageBox  
from datetime import datetime as datim
from .project import Project
from .labelDisp import LabelDispDock
import h5py
import os

from .annotations import *

class AnnotationManager(object):
    def __init__(self, config, project=None, scene=None, labelDisp=None):

        self.config = config
        self.attributes = {} # name - Attribute object
        self.annotations = {} # timestamp - Annotation object

        self.set_project(project)
        self.set_scene(scene)
        self.set_labelDisp(labelDisp)

        self.saved = True # save status
        self.annotation_file = None

    def set_project(self, project):
        if isinstance(project, Project):
            self.project = project
            self.project.set_annotationMgr(self) 
        else:
            self.project = None

    def set_scene(self, scene):
        if isinstance(scene, QGraphicsScene):
            self.scene = scene
            self.scene.set_annotationMgr(self)  
        else: 
            self.scene = None

    def set_labelDisp(self, labelDisp):
        if isinstance(labelDisp, LabelDispDock):
            self.labelDisp = labelDisp
            self.labelDisp.set_annotationMgr(self)
        else:
            self.labelDisp = None


    ##############################################
    #### annotation file seaching and opening ####
    ##############################################

    def get_annotation_file(self, image_id, mode='project'):
        '''
        Args:
            image_id: image identifer, it will be the series number in 'project' mode, file path in 'file' mode
            mode: 'project' or 'file'
        '''
        if mode == 'project' and self.project.is_open():
            self.annotation_file = self.project.get_annotation_path(image_id)
        else:
            currentDir = os.path.dirname(image_id)
            basefilename, _ = os.path.splitext(os.path.basename(image_id))
            self.annotation_file = os.path.join(currentDir, basefilename + '.hdf5')
        return self.annotation_file
    
    def load_annotation(self, image_id):
        if self.project.is_open():
            self.annotation_file = self.get_annotation_file(image_id, mode='project')
        else:
            self.annotation_file = self.get_annotation_file(image_id, mode='file')
        self.load(self.annotation_file)
        self.scene.add_graphItems()
        self.scene.refresh()
        self.labelDisp.refresh()

    ############################
    #### method for add new ####
    ############################

    def new_attribute(self, attr_name, label_list=None):
        if attr_name not in self.attributes.keys():
            self.attributes[attr_name] = Attribute(attr_name, label_list)
        else:
            print("Attribute has existed!")
        self.saved = False

    def new_label(self, attr_name, label_name, label_color=None):
        if attr_name in self.attributes.keys():
            self.attributes[attr_name].add_label(label_name, label_color)
        else:
            print("Attribute does not exist")

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
        self.scene.add_graphItem(annotation, display_channel)


    def add_label_to_selected_annotations(self, label_name, attr_name):

        if attr_name not in (self.attributes.keys()):
            return
        if label_name not in list(self.attributes[attr_name].labels.keys()):
            return
        annotations = self.get_selected_annotations()
        if annotations:
            for annotation in annotations:
                label_obj = self.attributes[attr_name].labels[label_name]
                annotation.add_label(label_obj)
            self.saved = False

    ############################
    #### methods for get ####
    ############################

    def get_annotation_by_graphItem(self, graphItem):
        timestamp = [timestamp for timestamp, item in self.annotations.items() if graphItem is item.graphObject][0]
        return self.annotations[timestamp]

    def get_selected_annotations(self):
        if self.scene is None:
            return None
        if len(self.scene.selectedItems) == 0:
            return None
        annotations = []
        for item in self.scene.selectedItems:
            annotations.append(self.get_annotation_by_graphItem(item))
        return annotations

    ############################
    #### methods for remove ####
    ############################

    def delete_annotation_by_graphItem(self, graphItem):
        timestamp = [timestamp for timestamp, item in self.annotations.items() if graphItem is item.graphObject][0]
        del self.annotations[timestamp]
        if self.scene:
            self.scene.removeItem(graphItem)
        self.saved = False

    def remove_label(self, label, attr_name=None):
        if attr_name is None:
            assert isinstance(label, Label)
            label_obj = label
            attr_name = label.attr_name
        elif attr_name in list(self.attributes.keys()):
            label_obj = self.attributes[attr_name].get_label(label)
        else:
            return
        self._remove_label_from_all_annotations(label_obj)
        self.attributes[attr_name].remove_label(label_obj)

        self.saved = False

    def remove_label_from_selected_annotation(self, label_name, attr_name):
        if attr_name not in (self.attributes.keys()):
            return
        if label_name not in list(self.attributes[attr_name].labels.keys()):
            return
        annotations = self.get_selected_annotations()
        if annotations:
            annotation = annotations[0]
            label_obj = self.attributes[attr_name].labels[label_name]
            annotation.remove_label(label_obj)
            self.saved = False

    def remove_attr(self, attr):
        if isinstance(attr, Attribute):
            attr_name = attr.attr_name
            attr_obj = attr
        elif attr in list(self.attributes.keys()):
            attr_name = attr
            attr_obj = self.attributes[attr]
        else:
            return
        for label_obj in attr_obj.labels.values():
            self._remove_label_from_all_annotations(label_obj)
        del self.attributes[attr_name]

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
        elif attr_name in self.attributes.keys():
            label = self.attributes[attr_name].get_label(label)
            if label is not None:
                label.rename(name)
        self.saved = False

    def rename_attr(self, name, attr):
        if name not in self.attributes.keys():
            if isinstance(attr, Attribute):
                attr_obj = attr.rename(name)
                self.attributes[name] = self.attributes.pop(attr.attr_name)
                self.saved = False
            elif attr in self.attributes.keys():
                self.attributes[attr].rename(name)
                self.attributes[name] = self.attributes.pop(attr)
                self.saved = False


    ##################################
    #### method for save and load ####
    ##################################

    def close(self):
        self.attributes = {} 
        self.annotations = {}
        self.saved = True
        self.annotation_file = None

    def save(self, inquiry=True):
        if not self.saved:
            save = QMessageBox.Yes == QMessageBox.question(None, "Important...", "Would you like to save the changes in your annotations?", QMessageBox.Yes | QMessageBox.No) if inquiry else True
            if save and self.annotation_file is not None:
                self.save_to_file(self.annotation_file)
                self.annotation_file = None

    def save_to_file(self, filename):

        if self.saved is True:
            return
        if filename is None:
            return

        with h5py.File(filename, 'w') as location:
            to_save = []
            # save the annotations
            for timestamp in self.annotations.keys():
                self.annotations[timestamp].save(location)
                to_save.append(timestamp)
            if 'attributes' in location.keys():
                del location['attributes']
            for attr_name, attr in self.attributes.items():
                # attr.save() has its own clean-ups
                attr.save(location)
            # some clean-up, same annotations may be deleted
            annotation_grp = location.require_group('annotations')
            for timestamp in annotation_grp.keys():
                if timestamp not in to_save:
                    del annotation_grp[timestamp]

            location.flush()
            location.close()

        self.saved = True


    def load(self, filename):
        self.saved = True
        self.attributes.clear()
        self.annotations.clear()

        with h5py.File(filename) as location:
            self.load_attributes(location)

            if 'annotations' in location.keys():
                for timestamp in location['annotations']:
                    annotation = self.load_single_annotation(location['annotations'][timestamp], self.attributes)
                    if annotation is not None:
                        self.add_annotation(annotation)

            location.flush()
            location.close()


    def load_attributes(self, location):

        if 'attributes' not in location.keys():
            print("Attributes not found !")
            return
        attributes = location['attributes']
        for attr_name in attributes.keys():
            self.attributes[attr_name] = Attribute(attr_name)
            for label_name in attributes[attr_name].keys():
                # print(attributes[label_name])
                color = [attributes[attr_name][label_name][0],attributes[attr_name][label_name][1],
                         attributes[attr_name][label_name][2]]
                self.attributes[attr_name].add_label(label_name, color)

    def load_single_annotation(self, location, attr_group):

        type = location.attrs['type']
        if type == POLYGON:
            return PolygonAnnotation.load(location, attr_group)
        elif type == BBX:
            return BBXAnnotation.load(location, attr_group)
        elif type == OVAL:
            return OVALAnnotation.load(location, attr_group)
        elif type == POINT:
            return PointAnnotation.load(location, attr_group)
        elif type == LINE:
            return LineAnnotation.load(location, attr_group)
        else:
            print("Unknown annotation type")

    def appearance(self, anno, display_channel=None):
        if isinstance(display_channel, str):
            for label in anno.labels:
                if display_channel == label.attr_name:
                    c = label.color
                    linePen = QPen(QColor(c[0], c[1], c[2], 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    areaBrush = QBrush(QColor(c[0], c[1], c[2], 70))
                    return linePen, areaBrush
            linePen = QPen(QColor(0, 0, 0, 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 0, 0, 70))
        elif display_channel == 1:
            linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 200, 0, 70))
        else:
            linePen = QPen(QColor(0, 0, 0, 0), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 0, 0, 0))
        
        if anno.type == LINE:
            linePen.setWidth(int(self.config['lineAnnotationWidth']))
            areaBrush = QBrush(QColor(0, 200, 0, 0))

        return linePen, areaBrush










