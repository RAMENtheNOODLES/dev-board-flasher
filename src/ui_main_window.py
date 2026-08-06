# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QLabel, QLineEdit, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QTextEdit,
    QWidget)

from vignette_overlay import VignetteOverlay

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(943, 715)
        self.actionOpen_File = QAction(MainWindow)
        self.actionOpen_File.setObjectName(u"actionOpen_File")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.containerWidget = QFrame(self.centralwidget)
        self.containerWidget.setObjectName(u"containerWidget")
        self.containerWidget.setGeometry(QRect(9, 9, 925, 664))
        self.containerWidget.setFrameShape(QFrame.Shape.StyledPanel)
        self.containerWidget.setFrameShadow(QFrame.Shadow.Raised)
        self.actualWidget = QWidget(self.containerWidget)
        self.actualWidget.setObjectName(u"actualWidget")
        self.actualWidget.setGeometry(QRect(1, 1, 523, 402))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.actualWidget.sizePolicy().hasHeightForWidth())
        self.actualWidget.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QGridLayout(self.actualWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(18, 18, 27, 27)
        self.refreshCOMPortButton = QPushButton(self.actualWidget)
        self.refreshCOMPortButton.setObjectName(u"refreshCOMPortButton")

        self.gridLayout_2.addWidget(self.refreshCOMPortButton, 0, 2, 1, 1)

        self.uploadButton = QPushButton(self.actualWidget)
        self.uploadButton.setObjectName(u"uploadButton")

        self.gridLayout_2.addWidget(self.uploadButton, 2, 2, 1, 1)

        self.logText = QTextEdit(self.actualWidget)
        self.logText.setObjectName(u"logText")
        self.logText.setReadOnly(True)

        self.gridLayout_2.addWidget(self.logText, 3, 1, 1, 1)

        self.boardSelect = QComboBox(self.actualWidget)
        self.boardSelect.setObjectName(u"boardSelect")

        self.gridLayout_2.addWidget(self.boardSelect, 1, 1, 1, 1)

        self.label_2 = QLabel(self.actualWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_2, 5, 2, 1, 2)

        self.uploadBoardButton = QPushButton(self.actualWidget)
        self.uploadBoardButton.setObjectName(u"uploadBoardButton")

        self.gridLayout_2.addWidget(self.uploadBoardButton, 5, 1, 1, 1)

        self.serialPortsBox = QComboBox(self.actualWidget)
        self.serialPortsBox.setObjectName(u"serialPortsBox")

        self.gridLayout_2.addWidget(self.serialPortsBox, 0, 1, 1, 1)

        self.comLabel = QLabel(self.actualWidget)
        self.comLabel.setObjectName(u"comLabel")

        self.gridLayout_2.addWidget(self.comLabel, 0, 0, 1, 1)

        self.label_3 = QLabel(self.actualWidget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 3, 0, 1, 1)

        self.baudRateBox = QComboBox(self.actualWidget)
        self.baudRateBox.addItem("")
        self.baudRateBox.addItem("")
        self.baudRateBox.addItem("")
        self.baudRateBox.addItem("")
        self.baudRateBox.setObjectName(u"baudRateBox")

        self.gridLayout_2.addWidget(self.baudRateBox, 6, 2, 1, 1)

        self.label = QLabel(self.actualWidget)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 6, 3, 1, 1)

        self.sendTXDataButton = QPushButton(self.actualWidget)
        self.sendTXDataButton.setObjectName(u"sendTXDataButton")

        self.gridLayout_2.addWidget(self.sendTXDataButton, 7, 2, 1, 1)

        self.fileName = QLineEdit(self.actualWidget)
        self.fileName.setObjectName(u"fileName")

        self.gridLayout_2.addWidget(self.fileName, 2, 1, 1, 1)

        self.boardSelectLabel = QLabel(self.actualWidget)
        self.boardSelectLabel.setObjectName(u"boardSelectLabel")

        self.gridLayout_2.addWidget(self.boardSelectLabel, 1, 0, 1, 1)

        self.label_4 = QLabel(self.actualWidget)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_2.addWidget(self.label_4, 7, 0, 1, 1)

        self.serialMonitorButton = QPushButton(self.actualWidget)
        self.serialMonitorButton.setObjectName(u"serialMonitorButton")

        self.gridLayout_2.addWidget(self.serialMonitorButton, 7, 3, 1, 1)

        self.serialTXBox = QLineEdit(self.actualWidget)
        self.serialTXBox.setObjectName(u"serialTXBox")

        self.gridLayout_2.addWidget(self.serialTXBox, 7, 1, 1, 1)

        self.clearLogsButton = QPushButton(self.actualWidget)
        self.clearLogsButton.setObjectName(u"clearLogsButton")

        self.gridLayout_2.addWidget(self.clearLogsButton, 3, 2, 1, 1)

        self.vignette = VignetteOverlay(self.centralwidget)
        self.vignette.setObjectName(u"vignette")
        self.vignette.setGeometry(QRect(600, 600, 120, 80))
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 943, 33))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuEdit = QMenu(self.menubar)
        self.menuEdit.setObjectName(u"menuEdit")
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menuFile.addAction(self.actionOpen_File)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Upload WIz", None))
        self.actionOpen_File.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.refreshCOMPortButton.setText(QCoreApplication.translate("MainWindow", u"Refresh", None))
        self.uploadButton.setText(QCoreApplication.translate("MainWindow", u"Open File", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Serial Connection Settings", None))
        self.uploadBoardButton.setText(QCoreApplication.translate("MainWindow", u"Upload to Board", None))
        self.comLabel.setText(QCoreApplication.translate("MainWindow", u"COM PORT", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Logs", None))
        self.baudRateBox.setItemText(0, QCoreApplication.translate("MainWindow", u"9600", None))
        self.baudRateBox.setItemText(1, QCoreApplication.translate("MainWindow", u"115200", None))
        self.baudRateBox.setItemText(2, QCoreApplication.translate("MainWindow", u"38400", None))
        self.baudRateBox.setItemText(3, QCoreApplication.translate("MainWindow", u"57600", None))

        self.label.setText(QCoreApplication.translate("MainWindow", u"Baud Rate", None))
        self.sendTXDataButton.setText(QCoreApplication.translate("MainWindow", u"Send Data", None))
        self.boardSelectLabel.setText(QCoreApplication.translate("MainWindow", u"Board Select", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Serial TX", None))
        self.serialMonitorButton.setText(QCoreApplication.translate("MainWindow", u"Connect", None))
        self.serialTXBox.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Type data to send here...", None))
        self.clearLogsButton.setText(QCoreApplication.translate("MainWindow", u"Clear Logs", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuEdit.setTitle(QCoreApplication.translate("MainWindow", u"Edit", None))
    # retranslateUi

