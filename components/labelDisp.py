from PyQt5 import uic
from PyQt5.QtGui import QIcon, QColor, QPixmap
from PyQt5.QtWidgets import QDockWidget, QDialog, QMessageBox, QTreeWidgetItem, \
    QTableWidgetItem, QFileDialog, QColorDialog, QGraphicsScene
from PyQt5.QtCore import Qt
from random import randint
import h5py
import os
# from .annotationManager import AnnotationManager


class LabelDispDock(QDockWidget):

    def __init__(self, config, annotationMgr=None, scene=None, parent=None):

        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/labelDisp.ui', baseinstance=self)
        self.config = config
        self.setContentsMargins(1,0,6,0)

        self.set_scene(scene)
        self.set_annotationMgr(annotationMgr)

        # connect signals and slots
        self.btnNewGroup.clicked.connect(self.new_group)
        self.btnNewLabel.clicked.connect(self.new_label)
        self.btnRemove.clicked.connect(self.remove)
        self.btnRename.clicked.connect(self.rename)
        self.labelTree.itemDoubleClicked.connect(lambda p1,p2: self.add_label())
        self.btnDeleteGivenLabel.clicked.connect(self.remove_given_label)
        self.channel.currentIndexChanged.connect(self.change_display_channel)
    
    def set_scene(self, scene):
        # self.scene = scene if isinstance(scene, QGraphicsScene) else None
        self.scene = scene
    
    def set_annotationMgr(self, annotationMgr):
        # self.annotationMgr = annotationMgr if isinstance(annotationMgr, AnnotationManager) else None
        self.annotationMgr = annotationMgr
        if annotationMgr is not None:
            self.refresh()

    #################
    #### refresh ####
    #################

    def change_display_channel(self, index=None):
        index = self.channel.currentIndex()
        attr_name = self.channel.itemText(index)
        if len(attr_name) == 0:
            return
        if attr_name == "All":
            self.config['display_channel'] = 1
        elif attr_name == "Hidden":
            self.config['display_channel'] = None
        else:
            self.config['display_channel'] = attr_name
        self.scene.refresh()

    #######################
    #### label editing ####
    #######################

    def new_group(self):
        # self.newGroupDlg.clear()
        newGroupDlg = NewLabelGroupDialog(self)
        if newGroupDlg.exec() == QDialog.Accepted:
            group_name = newGroupDlg.get_name()
            if group_name in self.annotationMgr.attributes.keys():
                QMessageBox.information(self, 'Message', "The group name is taken")
            else:
                self.annotationMgr.new_attribute(group_name)
                self.channel.addItem(group_name)
            self.refresh_labelTree()

    def new_label(self):
        # self.newLabelDlg.reset()
        if self.annotationMgr is not None:
            newLabelDlg = NewLabelDialog(self.annotationMgr, self)
            if newLabelDlg.exec() == QDialog.Accepted:
                attr_name, label_name = newLabelDlg.get_name()
                label_color = newLabelDlg.get_color()
                self.annotationMgr.new_label(attr_name, label_name, label_color)
                self.refresh_labelTree()

    def remove(self):
        item, type = self.get_current_item()
        if item is not None:
            if type == 'attr':
                self.annotationMgr.remove_attr(item.text(0))
                index = self.channel.findText(item.text(0))
                if index != -1:
                    self.channel.removeItem(index)
            elif type == 'label':
                self.annotationMgr.remove_label(item.text(1), item.parent().text(0))
            self.refresh()

    def remove_given_label(self):
        row = self.infoTable.currentRow()
        if row < 2:
            return
        table = self.infoTable
        self.annotationMgr.remove_label_from_selected_annotation(table.item(row,1).text(),table.item(row,0).text())
        self.refresh_infoTable()
        self.change_display_channel()

    def rename(self):
        # self.renameDlg.clear()
        renameDlg = RenameDialog()
        if renameDlg.exec () == QDialog.Accepted:
            item, type = self.get_current_item()
            name = renameDlg.get_name()
            if item is not None:
                if type == 'attr':
                    self.annotationMgr.rename_attr(name, item.text(0))
                    index = self.channel.findText(name)
                    if index != -1:
                        self.channel.removeItem(index)
                        self.channel.addItem(item.text(0))
                elif type == 'label':
                    print(name, item.text(1), item.parent().text(0))
                    self.annotationMgr.rename_label(name, item.text(1), item.parent().text(0))
                self.refresh()

    def get_current_item(self):
        try:
            item = self.labelTree.selectedItems()[0]
            if item.parent() is None:
                return item, 'attr'
            else:
                return item, 'label'
        except Exception as e:
            return None, None


    def add_label(self):
        item, type = self.get_current_item()
        if item is not None and type == 'label':
            self.annotationMgr.add_label_to_selected_annotations(item.text(1), item.parent().text(0))
        self.refresh_infoTable()
        self.change_display_channel()


    ################################
    #### import export methods  ####
    ################################

    def import_labels(self, filename=None):
        if filename is None:
            filename = QFileDialog.getOpenFileName(None, "Select HDF5 File", directory=self.config['defaultLabelListDir'])[0]
        if len(filename) == 0:
            return
        if filename.endswith('.hdf5'):
            location = h5py.File(filename)
            if len(self.annotationMgr.attributes) != 0:
                answer =  QMessageBox.question(self, 'Warning',
                                               "You want to overwrite all labels, the labels added to annotations will get lost!",
                                               QMessageBox.Yes, QMessageBox.No)
                if answer == QMessageBox.Yes:
                    for attr_name in list(self.annotationMgr.attributes.keys()):
                        self.annotationMgr.remove_attr(attr_name)
                else:
                    return

            self.annotationMgr.load_attributes(location)
            location.flush()
            location.close()
            self.refresh()
        else:
            print('(error) Not a HDF5 file... nothing was imported.')

    def export_labels(self, filename=None):
        if filename is None:
            filename = QFileDialog.getSaveFileName(parent=self, caption='Select Export File...', filter='HDF5 Files (*.hdf5)', directory=self.config['defaultLabelListDir'])[0]
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

    ##############################################
    #### initialization and refresh functions ####
    ##############################################

    def resize_column_width(self):
        table = self.infoTable
        table_width = table.width()
        table.resizeColumnsToContents()
        cell_size = [table.columnWidth(i) for i in range(table.columnCount())]
        if sum(cell_size) > table_width:
            return
        ratio = table_width/sum(cell_size)
        for i in range(len(cell_size)):
            table.setColumnWidth(i, cell_size[i]*ratio)

    def table_disable_edit(self):
        for i in range(self.infoTable.rowCount()):
            for j in range(2):
                item = self.infoTable.item(i, j)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    def refresh_infoTable(self, annotation=None):
        self.infoTable.clear()
        self.infoTable.setColumnCount(2)
        self.resize_column_width()
        self.infoTable.setHorizontalHeaderLabels(('Attribute', 'Value'))
        self.infoTable.setRowCount(2)
        self.infoTable.verticalHeader().setVisible(False)
        if annotation is None:
            annotation = self.annotationMgr.get_selected_annotations()
            if annotation is not None:
                annotation = annotation[0]
            else:
                return

        self.infoTable.setItem(0, 0, QTableWidgetItem('type'))
        self.infoTable.setItem(0, 1, QTableWidgetItem(annotation.type))
        self.infoTable.setItem(1, 0, QTableWidgetItem('time stamp'))
        self.infoTable.setItem(1, 1, QTableWidgetItem(annotation.timestamp))
        row = 2
        for lable_obj in annotation.labels:
            self.infoTable.insertRow(row)
            self.infoTable.setItem(row, 0, QTableWidgetItem(lable_obj.attr_name))
            self.infoTable.setItem(row, 1, QTableWidgetItem(lable_obj.label_name))
            row += 1
        self.table_disable_edit()
        self.resize_column_width()

    def refresh_labelTree(self):
        self.labelTree.clear()
        self.labelTree.setHeaderLabels(['Property', 'Value (Label)'])
        for attr_name in self.annotationMgr.attributes.keys():
            attr_node = QTreeWidgetItem([attr_name, ''])
            attr_node.setIcon(0, QIcon("./icons/arrow.png"))
            self.labelTree.addTopLevelItem(attr_node)
            for label_name, label in self.annotationMgr.attributes[attr_name].labels.items():
                label_node = QTreeWidgetItem(['', label_name])
                pixmap = QPixmap(120,60)
                pixmap.fill(QColor(label.color[0],label.color[1],label.color[2]))
                # label_node.setIcon(0, QIcon("./icons/arrow.png"))
                label_node.setIcon(0, QIcon(pixmap))
                attr_node.addChild(label_node)
            self.labelTree.expandToDepth(2)

    def refresh_channelBox(self):
        currentText = self.channel.currentText()
        self.channel.clear()
        self.channel.addItem("All")
        self.channel.addItem("Hidden")
        self.channel.addItems(list(self.annotationMgr.attributes.keys()))
        ind = self.channel.findText(currentText)
        if ind != -1:
            self.channel.setCurrentIndex(ind)

    def refresh(self):
        self.refresh_infoTable()
        self.refresh_labelTree()
        self.refresh_channelBox()


class NewLabelGroupDialog(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/NewLabelGroupDialog.ui', self)
        self.setWindowTitle("New Label Group")

    def clear(self):
        self.groupName.clear()

    def get_name(self):
        return str(self.groupName.text())

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

        self.btnColor.clicked.connect(self.select_color)
        self.reset()

    def reset(self):
        self.groupName.clear()
        self.groupName.addItems(list(self.annotationMgr.attributes))
        self.labelName.clear()
        self.set_random_color()

    def get_name(self):
        return [str(self.groupName.currentText()),str(self.labelName.text())]

    def get_color(self):
        return [self.color.red(), self.color.green(), self.color.blue()]

    def select_color(self):
        dlg = QColorDialog()
        if QDialog.Accepted == dlg.exec ():
            self.set_color(dlg.selectedColor())

    def set_color(self, color):
        self.color = color
        self.color_icon.fill(color)
        self.btnColor.setIcon(QIcon(self.color_icon))

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
        self.newName.clear()

    def get_name(self):
        return str(self.newName.text())


