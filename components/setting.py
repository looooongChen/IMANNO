from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog


class MaskDirDialog(QDialog):
    """
    Lets you select a name and color for a new classification-LABEL.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/MaskDirSetting.ui', baseinstance=self)
        self.setWindowTitle("Mask Imp./Exp. Directories")
        self.ui.import_button.clicked.connect(self.get_import_dir)
        self.ui.export_button.clicked.connect(self.get_export_dir)
        self.accepted.connect(self.accept_change)
        self.rejected.connect(self.reject_change)

        self.import_dir = None
        self.export_dir = None

    def get_import_dir(self):
            self.ui.import_line.setText(QFileDialog.getExistingDirectory(self, "Select Source Directory"))

    def get_export_dir(self):
            self.ui.export_line.setText(QFileDialog.getExistingDirectory(self, "Select Save Directory"))

    def accept_change(self):
        im = self.ui.import_line.text().strip()
        if len(im) != 0:
            self.import_dir = im
        ex = self.ui.export_line.text().strip()
        if len(ex) != 0:
            self.export_dir = ex
        print("Import dir: " + str(self.import_dir), "Export dir: "+str(self.export_dir))
        
    def reject_change(self):
        if self.import_dir is not None:
            self.ui.import_line.setText(self.import_dir)
        else:
            self.ui.import_line.clear()
        if self.export_dir is not None:
            self.ui.export_line.setText(self.export_dir)
        else:
            self.ui.export_line.clear()
        print("Import dir: " + str(self.import_dir), "Export dir: "+str(self.export_dir))