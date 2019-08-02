from PyQt4 import uic
from PyQt4.QtGui import QDockWidget, QDialog, QMessageBox, QTreeWidgetItem, \
    QTableWidgetItem, QIcon, QFileDialog, QColorDialog, QColor, QPixmap, QMainWindow
from PyQt4.QtCore import Qt, QSize, pyqtSignal
import numpy as np
import h5py
import os
from random import randint

class LabelDock(QDockWidget):

    graphItemsUpdate = pyqtSignal()

    def __init__(self, annotationMgr, parent=None):

        super().__init__(parent=parent)
        self.annotationMgr = annotationMgr
        self.ui = uic.loadUi('uis/LabelDock.ui', baseinstance=self)
        # self.setWindowTitle("Label Manager")

        # add components
        self.newGroupDlg = NewLabelGroupDialog(self)
        self.newLabelDlg = NewLabelDialog(self.annotationMgr, self)
        self.renameDlg = RenameDialog()

        # initialization
        self.initialize()

        # connect signals and slots
        self.ui.btnNewGroup.clicked.connect(self.new_group)
        self.ui.btnNewLabel.clicked.connect(self.new_label)
        self.ui.btnRemove.clicked.connect(self.remove)
        self.ui.btnRename.clicked.connect(self.rename)
        self.ui.labelTree.itemDoubleClicked.connect(lambda p1,p2: self.add_label())

        # self.ui.btnImport.clicked.connect(lambda :self.import_labels(None))
        # self.ui.btnExport.clicked.connect(lambda :self.export_labels(None))
        self.ui.btnAsDefault.clicked.connect(self.save_default_labels)
        self.ui.btnDefault.clicked.connect(self.load_default_labels)
        self.ui.btnDeleteGivenLabel.clicked.connect(self.remove_given_label)

    #######################
    #### label editing ####
    #######################

    def new_group(self):
        self.newGroupDlg.clear()
        if self.newGroupDlg.exec() == QDialog.Accepted:
            group_name = self.newGroupDlg.get_name()
            if group_name in self.annotationMgr.attributes.keys():
                QMessageBox.information(self, 'Message', "The group name is taken")
            else:
                self.annotationMgr.new_attribute(group_name)
                self.ui.channel.addItem(group_name)
            self.update_label_tree()

    def new_label(self):
        self.newLabelDlg.initialize()
        if self.newLabelDlg.exec() == QDialog.Accepted:
            attr_name, label_name = self.newLabelDlg.get_name()
            label_color = self.newLabelDlg.get_color()
            self.annotationMgr.new_label(attr_name, label_name, label_color)
            self.update_label_tree()

    def remove(self):
        item, type = self.get_current_item()
        if item is not None:
            if type == 'attr':
                self.annotationMgr.remove_attr(item.text(0))
                index = self.ui.channel.findText(item.text(0))
                if index != -1:
                    self.ui.channel.removeItem(index)
            elif type == 'label':
                self.annotationMgr.remove_label(item.text(0), item.parent().text(0))
            self.update()

    def remove_given_label(self):
        row = self.ui.infoTable.currentRow()
        if row < 2:
            return
        table = self.ui.infoTable
        self.annotationMgr.remove_label_from_selected_annotation(table.item(row,1).text(),table.item(row,0).text())
        self.update_info_table()
        self.graphItemsUpdate.emit()

    def rename(self):
        self.renameDlg.clear()
        if self.renameDlg.exec () == QDialog.Accepted:
            item, type = self.get_current_item()
            name = self.renameDlg.get_name()
            if item is not None:
                if type == 'attr':
                    self.annotationMgr.rename_attr(name, item.text(0))
                    index = self.ui.channel.findText(name)
                    if index != -1:
                        self.ui.channel.removeItem(index)
                        self.ui.channel.addItem(item.text(0))
                elif type == 'label':
                    self.annotationMgr.rename_label(name, item.text(0), item.parent().text(0))
                self.update()

    def get_current_item(self):
        try:
            item = self.ui.labelTree.selectedItems()[0]
            if item.parent() is None:
                return item, 'attr'
            else:
                return item, 'label'
        except Exception as e:
            return None, None


    def add_label(self):
        item, type = self.get_current_item()
        if item is not None and type == 'label':
            self.annotationMgr.add_label_to_selected_annotations(item.text(0), item.parent().text(0))
        self.update_info_table()
        self.graphItemsUpdate.emit()


    ################################
    #### import export methods  ####
    ################################

    def import_labels(self, filename=None):
        if filename is None:
            filename = QFileDialog.getOpenFileName(None, "Select HDF5 File")
            filename = str(filename)
        if len(filename) == 0:
            return
        if filename.endswith('.hdf5'):
            location = h5py.File(filename)
            if len(self.annotationMgr.attributes) != 0:
                answer =  QMessageBox.question(self, 'Warning',
                                               "You want to overwrite all labels, the labels added to annotations will get lost!",
                                               QMessageBox.Yes, QMessageBox.No)
                if answer == QMessageBox.Yes:
                    for attr_name in self.annotationMgr.attributes.keys():
                        self.annotationMgr.remove_attr(attr_name)
                else:
                    return

            self.annotationMgr.load_attributes(location)
            location.flush()
            location.close()
            self.initialize()
        else:
            print('(error) Not a HDF5 file... nothing was imported.')

    def export_labels(self, filename=None):
        if filename is None:
            filename = QFileDialog.getSaveFileName(parent=self, caption='Select Export File...', filter='HDF5 Files (*.hdf5)')
            filename = str(filename)
        if len(filename) == 0:
            return
        location = h5py.File(filename)
        for attr_name, attr in self.annotationMgr.attributes.items():
            # attr.save() has its own clean-ups
            attr.save(location)
        location.flush()
        location.close()

    def save_default_labels(self):
        path = "./config/default_labels.hdf5"
        if os.path.exists(path):
            os.remove(path)
        self.export_labels(path)

    def load_default_labels(self):
        self.import_labels("./config/default_labels.hdf5")

    #############################################
    #### initialization and update functions ####
    #############################################

    def resize_column_width(self):
        table = self.ui.infoTable
        table_width = table.width()
        table.resizeColumnsToContents()
        cell_size = [table.columnWidth(i) for i in range(table.columnCount())]
        if sum(cell_size) > table_width:
            return
        ratio = table_width/sum(cell_size)
        for i in range(len(cell_size)):
            table.setColumnWidth(i, cell_size[i]*ratio)

    def table_disable_edit(self):
        for i in range(self.ui.infoTable.rowCount()):
            for j in range(2):
                item = self.ui.infoTable.item(i, j)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    def initialize_info_table(self):
        self.ui.infoTable.clear()
        self.ui.infoTable.setColumnCount(2)
        self.resize_column_width()
        self.ui.infoTable.setHorizontalHeaderLabels(('Attribute', 'Value'))
        self.ui.infoTable.setRowCount(2)
        self.ui.infoTable.verticalHeader().setVisible(False)

    def update_info_table(self, annotation=None):
        self.initialize_info_table()
        if annotation is None:
            annotation = self.annotationMgr.get_selected_annotations()
            if annotation is not None:
                annotation = annotation[0]
            else:
                return

        self.ui.infoTable.setItem(0, 0, QTableWidgetItem('type'))
        self.ui.infoTable.setItem(0, 1, QTableWidgetItem(annotation.type))
        self.ui.infoTable.setItem(1, 0, QTableWidgetItem('time stamp'))
        self.ui.infoTable.setItem(1, 1, QTableWidgetItem(annotation.timestamp))
        row = 2
        for lable_obj in annotation.labels:
            self.ui.infoTable.insertRow(row)
            self.ui.infoTable.setItem(row, 0, QTableWidgetItem(lable_obj.attr_name))
            self.ui.infoTable.setItem(row, 1, QTableWidgetItem(lable_obj.label_name))
            row += 1
        self.table_disable_edit()
        self.resize_column_width()

    def update_label_tree(self):
        self.ui.labelTree.clear()
        for attr_name in self.annotationMgr.attributes.keys():
            attr_node = QTreeWidgetItem([attr_name])
            attr_node.setIcon(0, QIcon("./icons/arrow.png"))
            self.ui.labelTree.addTopLevelItem(attr_node)
            for label_name, label in self.annotationMgr.attributes[attr_name].labels.items():
                label_node = QTreeWidgetItem([label_name])
                pixmap = QPixmap(20,20)
                pixmap.fill(QColor(label.color[0],label.color[1],label.color[2]))
                # label_node.setIcon(0, QIcon("./icons/arrow.png"))
                label_node.setIcon(0, QIcon(pixmap))
                attr_node.addChild(label_node)
            self.ui.labelTree.expandToDepth(2)

    def update_channel_box(self):
        self.ui.channel.clear()
        self.ui.channel.addItem("Display without a certain channel.")
        self.ui.channel.addItem("Do not display masks.")
        self.ui.channel.addItems(list(self.annotationMgr.attributes.keys()))

    def initialize(self):
        self.update_label_tree()
        self.update_channel_box()

    def update(self):
        self.update_info_table()
        self.update_label_tree()
        self.update_channel_box()


class NewLabelGroupDialog(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/NewLabelGroupDialog.ui', self)
        self.setWindowTitle("New Label Group")

    def clear(self):
        self.ui.groupName.clear()

    def get_name(self):
        return str(self.ui.groupName.text())

class NewLabelDialog(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, annotationMgr, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/NewLabelDialog.ui', self)
        self.setWindowTitle("New Label")
        self.annotationMgr = annotationMgr

        # self.color = QColor(255, 255, 255, 0)
        self.color = None
        self.color_icon = QPixmap(20, 20)

        self.ui.btnColor.clicked.connect(self.select_color)

        self.initialize()

    def initialize(self):
        self.ui.groupName.clear()
        self.groupName.addItems(list(self.annotationMgr.attributes))
        self.ui.labelName.clear()
        self.set_random_color()

    def get_name(self):
        return [str(self.ui.groupName.currentText()),str(self.ui.labelName.text())]

    def get_color(self):
        return [self.color.red(), self.color.green(), self.color.blue()]

    def select_color(self):
        dlg = QColorDialog()
        if QDialog.Accepted == dlg.exec ():
            self.set_color(dlg.selectedColor())

    def set_color(self, color):
        self.color = color
        self.color_icon.fill(color)
        self.ui.btnColor.setIcon(QIcon(self.color_icon))

    def random_color(self):
        return QColor.fromHsv(randint(0,255), 200, 200)

    def set_random_color(self):
        self.set_color(self.random_color())

class RenameDialog(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/renameDialog.ui', baseinstance=self)
        self.setWindowTitle("New Name")

    def clear(self):
        self.ui.newName.clear()

    def get_name(self):
        return str(self.ui.newName.text())


