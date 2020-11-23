from .base import Table
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtCore import Qt

class LabelManager(Table):

    def __init__(self, config, label_dict=None):
        super().__init__()
        self.config = config

    #######################################
    #### parse / render save structure ####
    #######################################

    def parse_labels(self, label_dict, increment=True, mode='json', saved=True):
        if not increment:
            self.clear()
        saved = self.config.saved
        ## hdf5 compatible
        if mode == 'hdf5':
            if 'attributes' in label_dict.keys():
                props = label_dict['attributes']
                for prop in props.keys():
                    self.add_property(prop)
                    for label in props[prop].keys():
                        color = [props[prop][label][0], props[prop][label][1], props[prop][label][2]]
                        self.add_label(prop, label, color)
        else:
            for prop, labels in label_dict.items():
                self.add_property(prop)
                for label, color in labels.items():
                    self.add_label(prop, label, color)
        if not saved:
            self.config.saved = False
        else:
            self.config.saved = saved

    def render_save(self):
        label_dict = {}
        for prop_name, prop in self.items():
            label_dict[prop_name] = {}
            for label_name, label in prop.items():
                label_dict[prop_name][label_name] = [int(c) for c in label.color]
        return label_dict

    ###############################
    #### add / remove property ####
    ###############################

    def add_property(self, prop_name, saved=False):
        if prop_name not in self.keys():
            if not saved:
                self.config.saved = False
            return Property(self, prop_name)
    
    def remove_property(self, prop, saved=False):
        '''
        remove property, lables belonging to the property will also be removed
        Args:
            prop: property name or a Property object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        if prop_name in self.keys():
            self[prop_name].remove_all()
            del self[prop_name]
            if not saved:
                self.config.saved = False
    
    def rename_property(self, prop, new_name, saved=False):
        prop_name = prop.name if isinstance(prop, Property) else prop
        if prop_name in self.keys():
            self[prop_name].rename(new_name, saved)

    ############################
    #### add / remove label ####
    ############################
            
    def add_label(self, prop, label_name, color=None, saved=False):
        '''
        Args:
            prop: property name or a Property object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        if prop_name in self.keys():
            return self[prop_name].add_label(label_name, color, saved)
    
    def remove_label(self, prop, label, saved=False):
        '''
        Args:
            prop: property name or a Property object
            label: label name or a Label object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        if prop_name in self.keys():
            self[prop_name].remove_label(label, saved)
    
    def rename_label(self, prop, label, new_name, saved=False):
        prop_name = prop.name if isinstance(prop, Property) else prop
        label_name = label.name if isinstance(label, Label) else label
        if prop_name in self.keys():
            if label_name in self[prop_name].keys():
                self[prop_name][label_name].rename(new_name, saved)

    ##################################
    #### assign / withdraw labels ####
    ##################################

    def assign(self, annotation, prop, label, saved=False):
        '''
        Args:
            annotation: an annotions.Annotation object
            prop: property name or a Property object
            label: label name or a Label object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        label_name = label.name if isinstance(label, Label) else label
        if prop_name in self.keys():
            if label_name in self[prop_name].keys():
                self[prop_name][label_name].assign(annotation, saved)

    def withdraw(self, annotation, prop, label, saved=False):
        '''
        Args:
            annotation: an annotions.Annotation object
            prop: property name or a Property object
            label: label name or a Label object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        label_name = label.name if isinstance(label, Label) else label
        if prop_name in self.keys():
            if label_name in self[prop_name].keys():
                self[prop_name][label_name].withdraw(annotation, saved)

    ################
    #### others ####
    ################

    def clear(self, saved=True):
        '''
        all assigned lables will also be cleared
        '''
        for _, prop in self.items():
            prop.remove_all(saved)
        super().clear()
        if not saved:
            self.config.saved = False

class Property(Table):

    def __init__(self, labelMgr, prop_name):
        """
        Args:
            prop_name: name of a property e.g. Color
        """
        super().__init__()
        assert prop_name not in labelMgr.keys()
        self.labelMgr = labelMgr
        self.name = prop_name
        self.labelMgr[prop_name] = self
    
    def rename(self, prop_name, saved=False):
        if prop_name not in self.labelMgr.keys():
            self.labelMgr[prop_name] = self.labelMgr.pop(self.name)
            self.name = prop_name
            if not saved:
                self.labelMgr.config.saved = False

    def add_label(self, label_name, label_color=None, saved=False):
        if label_name not in self.keys():
            if not saved:
                self.labelMgr.config.saved = False
            return Label(self, label_name, label_color)
        else:
            return None

    def remove_label(self, label, saved=False):
        '''
        Args:
            label: label name or a Label object 
        '''
        label_name = label.name if isinstance(label, Label) else label
        if label_name in self.keys():
            self[label_name].withdraw_all(saved)
            del self[label_name]
            if not saved:
                self.labelMgr.config.saved = False
    
    def remove_all(self, saved=False):
        for _, label in self.items():
            label.withdraw_all(saved)
        self.clear()

    def withdraw_all(self, saved=False):
        for _, label in self.items():
            label.withdraw_all(saved)
    
class Label(Table):

    def __init__(self, prop, label_name, label_color=None):
        '''
        Args:
            prop: a Property object
            label_name: name of a label
            color: [r, g, b]
        '''
        super().__init__()
        assert label_name not in prop.keys()
        self.property = prop
        self.name = label_name
        self.color = label_color
        self.property[label_name] = self
    
    def linePen(self):
        return QPen(QColor(self.color[0], self.color[1], self.color[2], 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def areaBrush(self):
        return QBrush(QColor(self.color[0], self.color[1], self.color[2], 70))

    def rename(self, label_name, saved=False):
        if label_name not in self.property.keys():
            self.property[label_name] = self.property.pop(self.name)
            self.name = label_name
            if not saved:
                self.property.labelMgr.config.saved = False

    def set_color(self, r, g, b, saved=False):
        self.color = [r,g,b]
        if not saved:
            self.property.labelMgr.config.saved = False

    def assign(self, anno, saved=False):
        '''
        Args:
            anno: an annotation.Annotation object
            saved: if saved is True, changed will not be tracked
        '''
        if self.property not in anno.labels.keys() or anno.labels[self.property] is not self:
            anno.labels[self.property] = self
            self[anno.timestamp] = anno
            if not saved:
                self.property.labelMgr.config.saved = False

    def withdraw(self, anno, saved=False):
        '''
        Args:
            anno: timestamp or annotation.Annotation object
            saved: if saved is True, changed will not be tracked
        '''
        timestamp = anno if isinstance(anno, str) else anno.timestamp
        if timestamp in self.keys():
            anno = self[timestamp]
            del anno.labels[self.property]
            del self[timestamp]
            if not saved:
                self.property.labelMgr.config.saved = False

    def withdraw_all(self, saved=False):
        for _, anno in self.items():
            if self.property in anno.labels.keys():
                del anno.labels[self.property]
        self.clear()
        if not saved:
            self.property.labelMgr.config.saved = False


if __name__ == "__main__":
    from annotations import *
    import pprint
    DD = {'color': {'red': [255,0,0], 'blue': [0,255,0]}, 'shape': {'round': [12,35,123]}}
    pprint.pprint(DD)
    labelMgr = LabelManager({})
    labelMgr.parse_labels(DD)
    print('==== regenerated ====')
    pprint.pprint(labelMgr.render_save())
    print('==== operation test ====')
    anno = DotAnnotation('timestamp', {'coords':[100,100]}, labelMgr)
    labelMgr.assign(anno, 'shape', 'round')
    print(labelMgr['shape']['round'], anno.labels)
    # labelMgr['shape'].remove_all()
    labelMgr.withdraw(anno, 'shape', 'round')
    print(labelMgr['shape']['round'], anno.labels)
    # labelMgr.remove_property('shape')
    # print(labelMgr, anno.labels)