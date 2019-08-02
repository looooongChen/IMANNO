from PyQt4 import uic
from PyQt4.QtGui import QDialog, QFileDialog


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

        self.import_dir = None
        self.export_dir = None

    def get_import_dir(self):
        self.import_dir = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        self.ui.import_line.setText(self.import_dir)

    def get_export_dir(self):
        self.export_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        self.ui.export_line.setText(self.export_dir)