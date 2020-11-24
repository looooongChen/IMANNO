from PyQt5.QtGui import QPen, QBrush, QColor
import time
from PyQt5.QtCore import Qt

color_code = '#00cc00'
s = time.time()
for i in range(10000):
    color = QColor(color_code)
    color.setAlpha(100)
    pen = QPen(color, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
print(time.time()-s)