import os
import importlib

# 新版 FeelUOwn 会在启动的时候，设置这个环境变量
qt_moduel_name = os.getenv('FEELUOWN_QT_API', 'pyqt5')

if qt_moduel_name == 'pyqt6':
    qt_moduel_name = 'PyQt6'
else:
    qt_moduel_name = 'PyQt5'

QtCore = importlib.import_module(qt_moduel_name + ".QtCore", package=qt_moduel_name)
QtGui = importlib.import_module(qt_moduel_name + ".QtGui", package=qt_moduel_name)
QtWidgets = importlib.import_module(qt_moduel_name + ".QtWidgets", package=qt_moduel_name)

QLineEdit = QtWidgets.QLineEdit
QLabel = QtWidgets.QLabel
QPushButton = QtWidgets.QPushButton
QDialog = QtWidgets.QDialog
QVBoxLayout = QtWidgets.QVBoxLayout
QFileDialog = QtWidgets.QFileDialog
QMessageBox = QtWidgets.QMessageBox

pyqtSignal = QtCore.pyqtSignal

if qt_moduel_name == 'pyqt5':
    RichText = QtCore.Qt.RichText
    Password = QLineEdit.Password
else:
    RichText = QtCore.Qt.TextFormat.RichText
    Password = QLineEdit.EchoMode.Password

