# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'can.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QCheckBox,
    QComboBox, QGridLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QStatusBar, QWidget)

from can_logging import CanLogging

class Ui_CANViewer(object):
    def setupUi(self, CANViewer):
        if not CANViewer.objectName():
            CANViewer.setObjectName(u"CANViewer")
        CANViewer.resize(800, 666)
        self.action_Load_DBC = QAction(CANViewer)
        self.action_Load_DBC.setObjectName(u"action_Load_DBC")
        self.action_Start_Logging = QAction(CANViewer)
        self.action_Start_Logging.setObjectName(u"action_Start_Logging")
        self.actionSto_p_Logging = QAction(CANViewer)
        self.actionSto_p_Logging.setObjectName(u"actionSto_p_Logging")
        self.centralwidget = QWidget(CANViewer)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.channelSelect = QComboBox(self.centralwidget)
        self.channelSelect.setObjectName(u"channelSelect")

        self.gridLayout.addWidget(self.channelSelect, 11, 4, 1, 1)

        self.openDBCFileBtn = QPushButton(self.centralwidget)
        self.openDBCFileBtn.setObjectName(u"openDBCFileBtn")

        self.gridLayout.addWidget(self.openDBCFileBtn, 1, 3, 1, 1)

        self.canLogs = CanLogging(self.centralwidget)
        self.canLogs.setObjectName(u"canLogs")
        self.canLogs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.canLogs.setAlternatingRowColors(True)
        self.canLogs.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.canLogs.setSortingEnabled(True)

        self.gridLayout.addWidget(self.canLogs, 3, 0, 6, 5)

        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 12, 0, 1, 1)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 11, 3, 1, 1)

        self.deviceInfo = QPlainTextEdit(self.centralwidget)
        self.deviceInfo.setObjectName(u"deviceInfo")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.deviceInfo.sizePolicy().hasHeightForWidth())
        self.deviceInfo.setSizePolicy(sizePolicy)
        self.deviceInfo.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.deviceInfo.setUndoRedoEnabled(False)
        self.deviceInfo.setReadOnly(True)
        self.deviceInfo.setBackgroundVisible(False)

        self.gridLayout.addWidget(self.deviceInfo, 12, 1, 4, 1)

        self.baudRateComboBox = QComboBox(self.centralwidget)
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.setObjectName(u"baudRateComboBox")

        self.gridLayout.addWidget(self.baudRateComboBox, 12, 4, 1, 1)

        self.baudRateLabel = QLabel(self.centralwidget)
        self.baudRateLabel.setObjectName(u"baudRateLabel")

        self.gridLayout.addWidget(self.baudRateLabel, 12, 3, 1, 1)

        self.deviceSelect = QComboBox(self.centralwidget)
        self.deviceSelect.setObjectName(u"deviceSelect")

        self.gridLayout.addWidget(self.deviceSelect, 11, 1, 1, 1)

        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 11, 0, 1, 1)

        self.dBCFileLabel = QLabel(self.centralwidget)
        self.dBCFileLabel.setObjectName(u"dBCFileLabel")

        self.gridLayout.addWidget(self.dBCFileLabel, 1, 0, 1, 1)

        self.useDBCCheckBox = QCheckBox(self.centralwidget)
        self.useDBCCheckBox.setObjectName(u"useDBCCheckBox")
        self.useDBCCheckBox.setChecked(True)
        self.useDBCCheckBox.setTristate(False)

        self.gridLayout.addWidget(self.useDBCCheckBox, 1, 4, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.gridLayout.addItem(self.verticalSpacer, 10, 1, 1, 1)

        self.dBCFileLineEdit = QLineEdit(self.centralwidget)
        self.dBCFileLineEdit.setObjectName(u"dBCFileLineEdit")

        self.gridLayout.addWidget(self.dBCFileLineEdit, 1, 1, 1, 1)

        self.connectButton = QPushButton(self.centralwidget)
        self.connectButton.setObjectName(u"connectButton")

        self.gridLayout.addWidget(self.connectButton, 16, 1, 1, 1)

        CANViewer.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(CANViewer)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.menu_File = QMenu(self.menubar)
        self.menu_File.setObjectName(u"menu_File")
        CANViewer.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(CANViewer)
        self.statusbar.setObjectName(u"statusbar")
        CANViewer.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_File.menuAction())
        self.menu_File.addAction(self.action_Load_DBC)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.action_Start_Logging)
        self.menu_File.addAction(self.actionSto_p_Logging)

        self.retranslateUi(CANViewer)

        self.baudRateComboBox.setCurrentIndex(3)


        QMetaObject.connectSlotsByName(CANViewer)
    # setupUi

    def retranslateUi(self, CANViewer):
        CANViewer.setWindowTitle(QCoreApplication.translate("CANViewer", u"CAN Viewer", None))
        self.action_Load_DBC.setText(QCoreApplication.translate("CANViewer", u"&Load DBC...", None))
#if QT_CONFIG(statustip)
        self.action_Load_DBC.setStatusTip(QCoreApplication.translate("CANViewer", u"Load a DBC file from disk to use when receiving CAN messages.", None))
#endif // QT_CONFIG(statustip)
        self.action_Start_Logging.setText(QCoreApplication.translate("CANViewer", u"&Start Logging...", None))
#if QT_CONFIG(statustip)
        self.action_Start_Logging.setStatusTip(QCoreApplication.translate("CANViewer", u"Start logging the CANBUS.", None))
#endif // QT_CONFIG(statustip)
        self.actionSto_p_Logging.setText(QCoreApplication.translate("CANViewer", u"Sto&p Logging", None))
#if QT_CONFIG(statustip)
        self.actionSto_p_Logging.setStatusTip(QCoreApplication.translate("CANViewer", u"Stop logging the CANBUS.", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(statustip)
        self.openDBCFileBtn.setStatusTip(QCoreApplication.translate("CANViewer", u"Open a DBC file from disk to use when receiving CAN messages.", None))
#endif // QT_CONFIG(statustip)
        self.openDBCFileBtn.setText(QCoreApplication.translate("CANViewer", u"Open File", None))
        self.label_3.setText(QCoreApplication.translate("CANViewer", u"Device Information", None))
        self.label.setText(QCoreApplication.translate("CANViewer", u"Channel", None))
        self.deviceInfo.setPlaceholderText(QCoreApplication.translate("CANViewer", u"No device found", None))
        self.baudRateComboBox.setItemText(0, QCoreApplication.translate("CANViewer", u"125 kBits/s", None))
        self.baudRateComboBox.setItemText(1, QCoreApplication.translate("CANViewer", u"250 kBits/s", None))
        self.baudRateComboBox.setItemText(2, QCoreApplication.translate("CANViewer", u"500 kBits/s", None))
        self.baudRateComboBox.setItemText(3, QCoreApplication.translate("CANViewer", u"1000 kBits/s", None))

        self.baudRateLabel.setText(QCoreApplication.translate("CANViewer", u"Baud Rate", None))
        self.label_2.setText(QCoreApplication.translate("CANViewer", u"Device", None))
        self.dBCFileLabel.setText(QCoreApplication.translate("CANViewer", u"DBC File", None))
#if QT_CONFIG(statustip)
        self.useDBCCheckBox.setStatusTip(QCoreApplication.translate("CANViewer", u"Use the loaded dbc file.", None))
#endif // QT_CONFIG(statustip)
        self.useDBCCheckBox.setText(QCoreApplication.translate("CANViewer", u"Use DBC File", None))
#if QT_CONFIG(statustip)
        self.connectButton.setStatusTip(QCoreApplication.translate("CANViewer", u"Connect/Disconnect from the CANBUS.", None))
#endif // QT_CONFIG(statustip)
        self.connectButton.setText(QCoreApplication.translate("CANViewer", u"Connect", None))
        self.menu_File.setTitle(QCoreApplication.translate("CANViewer", u"&File", None))
    # retranslateUi

