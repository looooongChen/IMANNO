from PyQt5 import uic
from PyQt5.QtGui import QIcon, QColor, QPixmap
from PyQt5.QtWidgets import QDockWidget, QDialog, QTreeWidgetItem, QTableWidgetItem, QFileDialog, QColorDialog, QWidget, QMenu, QComboBox, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal

from .labelManager import Label, Property
from .enumDef import *

import random
import json
import h5py
import os

class LabelDispDock(QDockWidget):

    signalLabelAssign = pyqtSignal(Label)
    signalDispChannelChanged = pyqtSignal()

    def __init__(self, config, labelMgr, parent=None):

        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/labelDisp.ui', baseinstance=self)
        self.config = config
        self.labelMgr = labelMgr
        self.annotation = None
        self.setContentsMargins(1,0,6,0)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())
        # label list setup
        self.labelList.setColumnCount(1)
        self.labelList.setHeaderHidden(True)
        self.labelList.setIndentation(20)
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)

        self.labelMenu = QMenu(self)
        self.actionLoadDefault = self.labelMenu.addAction('Load Default')
        self.actionNewProperty = self.labelMenu.addAction(self.config.icons[NEW], 'New Property')
        self.actionNewLabel = self.labelMenu.addAction(self.config.icons[LABEL], 'New Label')
        self.actionRename = self.labelMenu.addAction(self.config.icons[RENAME], 'Rename')
        self.actionRemove = self.labelMenu.addAction(self.config.icons[DELETE], 'Remove')
        self.actionClear = self.labelMenu.addAction(self.config.icons[SYM_WARNING], 'Clear')
        self.actionSetDefault = self.labelMenu.addAction('Set As Default')
        self.labelList.customContextMenuRequested.connect(self.show_label_menu)
        
        self.actionLoadDefault.triggered.connect(self.load_default_labels)
        self.actionSetDefault.triggered.connect(self.save_default_labels)
        self.actionNewProperty.triggered.connect(self.new_property)
        self.actionNewLabel.triggered.connect(self.new_label)
        self.actionRename.triggered.connect(lambda : self.rename_label(None))
        self.actionRemove.triggered.connect(lambda : self.remove_label(None))
        self.actionClear.triggered.connect(self.clear_label)
        self.labelList.itemChanged.connect(self.on_labelItem_change, Qt.QueuedConnection)
        self.labelList.itemDoubleClicked.connect(self.assign_label)
        # annotation disp setup
        self.annotationDisp.setColumnCount(2)
        self.annotationDisp.horizontalHeader().setVisible(False)
        self.annotationDisp.verticalHeader().setVisible(False)
        self.annotationDisp.setContextMenuPolicy(Qt.CustomContextMenu)

        self.annoMenu = QMenu(self)
        self.actionWithdraw = self.annoMenu.addAction(QIcon(ICONS[DELETE]), 'Remove')

        self.actionWithdraw.triggered.connect(self.withdraw)
        self.annotationDisp.customContextMenuRequested.connect(self.show_anno_menu)
        # channel setup
        self.channel.currentIndexChanged.connect(self.on_channel_change)

    def sync(self):
        self.sync_annotationDisp()
        self.sync_labelDisp()
        self.sync_dispChannel()

    ##########################
    #### load/save labels ####
    ##########################

    def load_labels(self, filename=None):
        if filename is None:
            filename = QFileDialog.getOpenFileName(None, "Select .json/.hdf5 File", directory=self.config['configDirectory'])[0]
        ext = os.path.splitext(filename)[1]
        ## hdf5 compatible
        if ext == '.hdf5':
            with h5py.File(filename, 'r') as label_list:
                self.labelMgr.parse_labels(label_list, increment=True, mode='hdf5')
        elif ext == ANNOTATION_EXT:
            with open(filename, mode='r') as f:
                label_list = json.load(f)
                self.labelMgr.parse_labels(label_list, increment=True)
        self.sync_labelDisp()
        self.sync_dispChannel()

    def load_default_labels(self):
        ## hdf5 compatible
        if os.path.isfile("./config/default_labels.json"):
            self.load_labels("./config/default_labels.json")
        elif os.path.isfile("./config/default_labels.hdf5"):
            self.load_labels("./config/default_labels.hdf5")

    def save_labels(self, filename=None):
        if filename is None:
            filename = QFileDialog.getSaveFileName(parent=self, caption='Select Export File...', filter='JSON Files (*.json)', directory=self.config['configDirectory'])[0]
        label_list = self.labelMgr.render_save()
        with open(filename, mode='w') as f:
            json.dump(label_list, f, indent=2)
    
    def save_default_labels(self):
        self.save_labels("./config/default_labels.json")


    ######################################
    #### annotation display functions ####
    ######################################

    def sync_annotationDisp(self, anno=None):
        if anno is None:
            anno = self.annotation
        self.annotationDisp.clear()
        if anno is not None:
            self.annotation = anno
            # add info
            self.annotationDisp.setRowCount(2)
            self.annotationDisp.setItem(0, 0, QTableWidgetItem('Type'))
            self.annotationDisp.setItem(0, 1, QTableWidgetItem(anno.dataObject['type']))
            self.annotationDisp.setItem(1, 0, QTableWidgetItem('Timestamp'))
            self.annotationDisp.setItem(1, 1, QTableWidgetItem(anno.dataObject['timestamp']))
            for idx, prop in enumerate(anno.labels, 2):
                label = anno.labels[prop]
                self.annotationDisp.insertRow(idx)
                self.annotationDisp.setItem(idx, 0, QTableWidgetItem(prop.name))
                self.annotationDisp.setItem(idx, 1, QTableWidgetItem(label.name))
                # comboBox = QComboBox()
                # for name in prop.keys():
                #     comboBox.addItem(name)
                # comboBox.setCurrentText(label.name)
                # self.annotationDisp.setCellWidget(idx, 1, comboBox)
            # disable edit
            for i in range(self.annotationDisp.rowCount()):
                item = self.annotationDisp.item(i, 0)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item = self.annotationDisp.item(i, 1)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.annotationDisp.resizeColumnsToContents()

    def clear_annotationDisp(self):
        self.annotation = None
        self.annotationDisp.clear()
        self.annotationDisp.setRowCount(0)

    def show_anno_menu(self, pos):
        item = self.annotationDisp.itemAt(pos)
        if item is not None and item.row() >= 2:
            self.annoMenu.exec(self.annotationDisp.mapToGlobal(pos))
    
    def withdraw(self):
        row = self.annotationDisp.currentRow()
        prop_name = self.annotationDisp.item(row, 0).text()
        label_name = self.annotationDisp.item(row, 1).text()
        # timestamp = self.annotationDisp.item(1, 1).text()
        self.labelMgr[prop_name][label_name].withdraw(self.annotation)
        self.annotation.sync_disp(self.config)
        self.annotationDisp.removeRow(row)

    ##############################
    #### label list functions ####
    ##############################

    def sync_labelDisp(self):
        self.labelList.clear()
        label_color = QPixmap(120,60)
        for prop_name, prop in self.labelMgr.items():
            prop_item = QTreeWidgetItem(PROPERTY)
            prop_item.setData(0, Qt.UserRole, prop_name)
            prop_item.setText(0, prop_name)
            self.labelList.addTopLevelItem(prop_item)
            for label_name, label in prop.items():
                label_item = QTreeWidgetItem(LABEL)
                label_item.setData(0, Qt.UserRole, label_name)
                label_item.setText(0, label_name)
                label_color.fill(QColor(label.color[0],label.color[1],label.color[2]))
                label_item.setIcon(0, QIcon(label_color))
                prop_item.addChild(label_item)
            prop_item.setExpanded(True)
    
    def show_label_menu(self, pos):
        # enable new label only right click at a property item
        itemIndex = self.labelList.indexAt(pos)
        if itemIndex.row() == -1:
            self.labelList.clearSelection()
        self.actionNewLabel.setEnabled(False)
        if len(self.labelList.selectedItems())>0:
            item = self.labelList.selectedItems()[0]
            if item.type() == PROPERTY:
                self.actionNewLabel.setEnabled(True)
        # show the menu
        self.labelMenu.exec(self.labelList.mapToGlobal(pos))

    def new_property(self):
        index = 0
        while True:
            prop_name = 'property ' + str(index)
            if prop_name not in self.labelMgr.keys():
                break
            index += 1
        self.labelMgr.add_property(prop_name)
        prop_item = QTreeWidgetItem(PROPERTY)
        prop_item.setData(0, Qt.UserRole, prop_name)
        prop_item.setText(0, prop_name)
        self.labelList.addTopLevelItem(prop_item)
        self.rename_label(prop_item)
        self.sync_dispChannel()
    
    def new_label(self):
        if len(self.labelList.selectedItems()) > 0:
            prop_item = self.labelList.selectedItems()[0]
            if prop_item.type() == PROPERTY:
                prop_item.setExpanded(True)
                prop_name = prop_item.data(0, Qt.UserRole)
                dlg = ColorPicker()
                if QDialog.Accepted == dlg.exec ():
                    qcolor = dlg.selectedColor()
                    color = [qcolor.red(), qcolor.green(), qcolor.blue()]
                    index = 0
                    while True:
                        label_name = 'label ' + str(index)
                        if label_name not in self.labelMgr[prop_name].keys():
                            break
                        index += 1
                    self.labelMgr.add_label(prop_name, label_name, color)
                    label_item = QTreeWidgetItem(LABEL)
                    label_item.setData(0, Qt.UserRole, label_name)
                    label_item.setText(0, label_name)
                    label_color = QPixmap(120,60)
                    label_color.fill(qcolor)
                    label_item.setIcon(0, QIcon(label_color))
                    prop_item.addChild(label_item)
                    self.rename_label(label_item)

    def remove_label(self, item=None):
        if item is None and len(self.labelList.selectedItems()) > 0:
            item = self.labelList.selectedItems()[0]
        if item is not None:
            sync = False
            if item.type() == PROPERTY:
                prop_name = item.data(0, Qt.UserRole)
                prop = self.labelMgr[prop_name]
                if self.annotation is not None and self.annotation.has(prop):
                    sync = True
                self.labelMgr.remove_property(prop_name)
                self.labelList.invisibleRootItem().removeChild(item)
                self.sync_dispChannel()
            elif item.type() == LABEL:
                label_name = item.data(0, Qt.UserRole)
                prop_name = item.parent().data(0, Qt.UserRole)
                label = self.labelMgr[prop_name][label_name]
                if self.annotation is not None and self.annotation.has(label):
                    sync = True
                self.labelMgr.remove_label(prop_name, label_name)
                item.parent().removeChild(item)
            if sync:
                self.sync_annotationDisp()
                self.sync_dispChannel()

    def rename_label(self, item=None):
        if item is None and len(self.labelList.selectedItems()) > 0:
            item = self.labelList.selectedItems()[0]
        if item is not None:
            self.labelList.blockSignals(True)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.labelList.editItem(item, 0)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.labelList.blockSignals(False)

    def clear_label(self):
        if QMessageBox.Yes == QMessageBox.question(None, "Warning", "Assigned labels will also be removed!!!", QMessageBox.Yes | QMessageBox.No):
            self.labelMgr.clear(saved=False)
            self.labelList.clear()
            self.sync_annotationDisp()
            self.sync_dispChannel()

    def on_labelItem_change(self, item, col):
        if item.data(0, Qt.UserRole) != item.text(0): 
            if item.type() == PROPERTY:
                prop_name = item.data(0, Qt.UserRole)
                prop = self.labelMgr[prop_name]
                if item.text(0) not in self.labelMgr.keys() and not item.text(0).isupper():
                    # all upper string is preserved 
                    self.labelMgr.rename_property(prop_name, item.text(0))
                    self.labelList.blockSignals(True)
                    item.setData(0, Qt.UserRole, item.text(0))
                    self.labelList.blockSignals(False)
                    if self.annotation is not None and self.annotation.has(prop):
                        self.sync_annotationDisp()
                    self.sync_dispChannel()
                else:
                    self.labelList.blockSignals(True)
                    item.setText(0, prop_name)
                    self.labelList.blockSignals(False)
                    self.rename_label(item)
            elif item.type() == LABEL:
                prop_name = item.parent().text(0)
                label_name = item.data(0, Qt.UserRole)
                label = self.labelMgr[prop_name][label_name]
                if item.text(0) not in self.labelMgr[prop_name].keys():
                    self.labelMgr.rename_label(prop_name, label_name, item.text(0))
                    self.labelList.blockSignals(True)
                    item.setData(0, Qt.UserRole, item.text(0))
                    self.labelList.blockSignals(False)
                    if self.annotation is not None and self.annotation.has(label):
                        self.sync_annotationDisp()
                else:
                    self.labelList.blockSignals(True)
                    item.setText(0, label_name)
                    self.labelList.blockSignals(False)
                    self.rename_label(item)

    def assign_label(self, item, col):
        if item.type() == LABEL:
            prop_name = item.parent().data(0, Qt.UserRole)
            label_name = item.data(0, Qt.UserRole)
            self.signalLabelAssign.emit(self.labelMgr[prop_name][label_name])
        

    ##################################
    #### display channel function ####
    ##################################

    def sync_dispChannel(self):
        currentText = self.channel.currentText()
        self.channel.blockSignals(True)
        self.channel.clear()
        self.channel.addItem("All", userData=SHOW_ALL)
        self.channel.addItem("Hidden", userData=HIDE_ALL)
        for prop_name, _ in self.labelMgr.items():
            self.channel.addItem("property: " + prop_name, userData=prop_name)
        # ind = self.channel.findText(currentText)
        # ind = 0 if ind == -1 else ind
        # print(currentText, ind)
        self.channel.blockSignals(False)
        self.set_channel(currentText)

    def set_channel(self, channel):
        '''
        Args:
            channel: string of property or an property object
        '''
        channel = channel.name if isinstance(channel, Property) else channel
        if isinstance(channel, str):
            if channel.startswith("property: "):
                channel = channel[10:]
            if channel in self.labelMgr.keys():
                ind = self.channel.findText("property: " + channel)
            elif channel == 'Hidden':
                ind = 1
            else:
                ind = 0
        elif channel == HIDE_ALL:
            ind = 1
        else:
            ind = 0
        self.channel.blockSignals(True)
        self.channel.setCurrentIndex(ind)
        self.channel.blockSignals(False)
        self.on_channel_change(ind)


    def on_channel_change(self, ind):
        name = self.channel.itemData(ind, Qt.UserRole)
        if name in self.labelMgr.keys():
            self.config.disp = self.labelMgr[name]
        elif name == HIDE_ALL:
            self.config.disp = HIDE_ALL
        else:
            self.config.disp = SHOW_ALL
        self.signalDispChannelChanged.emit()
        

class ColorPicker(QColorDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # for children in self.findChildren(QWidget):
        #     classname = children.metaObject().className()
        #     if classname not in ("QColorPicker", "QColorLuminancePicker"):
        #         children.hide()

        customs_colors = list(LABEL_COLORS.values())
        for idx, color in enumerate(customs_colors):
            self.setCustomColor(idx, QColor(color))
        
        self.setCurrentColor(QColor(random.choice(customs_colors)))

