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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QProgressBar, QPushButton, QSizePolicy, QTextEdit,
    QWidget)

from vignette_overlay import VignetteOverlay
import fonts_rc
import images_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(943, 739)
        self.actionOpen_File = QAction(MainWindow)
        self.actionOpen_File.setObjectName(u"actionOpen_File")
        self.actionAdd_External_Flashing_Tool = QAction(MainWindow)
        self.actionAdd_External_Flashing_Tool.setObjectName(u"actionAdd_External_Flashing_Tool")
        self.actionAdd_External_Board_Directory = QAction(MainWindow)
        self.actionAdd_External_Board_Directory.setObjectName(u"actionAdd_External_Board_Directory")
        self.actionCheck_for_Updates = QAction(MainWindow)
        self.actionCheck_for_Updates.setObjectName(u"actionCheck_for_Updates")
        self.action_Reload_App = QAction(MainWindow)
        self.action_Reload_App.setObjectName(u"action_Reload_App")
        self.actionGithubPAT = QAction(MainWindow)
        self.actionGithubPAT.setObjectName(u"actionGithubPAT")
        self.actionRemote_Configurations = QAction(MainWindow)
        self.actionRemote_Configurations.setObjectName(u"actionRemote_Configurations")
        self.actionCANLib_Kvaser = QAction(MainWindow)
        self.actionCANLib_Kvaser.setObjectName(u"actionCANLib_Kvaser")
        self.action_Elf_Parser = QAction(MainWindow)
        self.action_Elf_Parser.setObjectName(u"action_Elf_Parser")
        self.action_Elf_Parser.setEnabled(True)
        self.action_Elf_Parser.setVisible(True)
        self.action_About = QAction(MainWindow)
        self.action_About.setObjectName(u"action_About")
        self.actionClear_All_Settings = QAction(MainWindow)
        self.actionClear_All_Settings.setObjectName(u"actionClear_All_Settings")
        self.action_Invalidate_Cache = QAction(MainWindow)
        self.action_Invalidate_Cache.setObjectName(u"action_Invalidate_Cache")
        self.action_Preferences = QAction(MainWindow)
        self.action_Preferences.setObjectName(u"action_Preferences")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.vignette = VignetteOverlay(self.centralwidget)
        self.vignette.setObjectName(u"vignette")
        self.vignette.setGeometry(QRect(0, 0, 925, 664))
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.containerWidget = QWidget(self.centralwidget)
        self.containerWidget.setObjectName(u"containerWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.containerWidget.sizePolicy().hasHeightForWidth())
        self.containerWidget.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QGridLayout(self.containerWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(18, 18, 27, 27)
        self.baudRateBox = QComboBox(self.containerWidget)
        self.baudRateBox.addItem("")
        self.baudRateBox.addItem("")
        self.baudRateBox.addItem("")
        self.baudRateBox.addItem("")
        self.baudRateBox.setObjectName(u"baudRateBox")

        self.gridLayout_2.addWidget(self.baudRateBox, 10, 2, 1, 1)

        self.label = QLabel(self.containerWidget)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 10, 3, 1, 1)

        self.serialMonitorButton = QPushButton(self.containerWidget)
        self.serialMonitorButton.setObjectName(u"serialMonitorButton")

        self.gridLayout_2.addWidget(self.serialMonitorButton, 11, 3, 1, 1)

        self.progressBar = QProgressBar(self.containerWidget)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(0)

        self.gridLayout_2.addWidget(self.progressBar, 7, 1, 1, 1)

        self.refreshCOMPortButton = QPushButton(self.containerWidget)
        self.refreshCOMPortButton.setObjectName(u"refreshCOMPortButton")

        self.gridLayout_2.addWidget(self.refreshCOMPortButton, 0, 2, 1, 1)

        self.logText = QTextEdit(self.containerWidget)
        self.logText.setObjectName(u"logText")
        font = QFont()
        font.setFamilies([u"FiraCode Nerd Font"])
        self.logText.setFont(font)
        self.logText.setReadOnly(True)

        self.gridLayout_2.addWidget(self.logText, 6, 1, 1, 1)

        self.comLabel = QLabel(self.containerWidget)
        self.comLabel.setObjectName(u"comLabel")

        self.gridLayout_2.addWidget(self.comLabel, 0, 0, 1, 1)

        self.boardSelectLabel = QLabel(self.containerWidget)
        self.boardSelectLabel.setObjectName(u"boardSelectLabel")

        self.gridLayout_2.addWidget(self.boardSelectLabel, 1, 0, 1, 1)

        self.sendTXDataButton = QPushButton(self.containerWidget)
        self.sendTXDataButton.setObjectName(u"sendTXDataButton")

        self.gridLayout_2.addWidget(self.sendTXDataButton, 11, 2, 1, 1)

        self.flashToolSubSettingsLabel = QLabel(self.containerWidget)
        self.flashToolSubSettingsLabel.setObjectName(u"flashToolSubSettingsLabel")

        self.gridLayout_2.addWidget(self.flashToolSubSettingsLabel, 3, 0, 1, 1)

        self.label_4 = QLabel(self.containerWidget)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_2.addWidget(self.label_4, 11, 0, 1, 1)

        self.boardSelect = QComboBox(self.containerWidget)
        self.boardSelect.setObjectName(u"boardSelect")

        self.gridLayout_2.addWidget(self.boardSelect, 1, 1, 1, 1)

        self.label_3 = QLabel(self.containerWidget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 6, 0, 1, 1)

        self.uploadButton = QPushButton(self.containerWidget)
        self.uploadButton.setObjectName(u"uploadButton")

        self.gridLayout_2.addWidget(self.uploadButton, 4, 2, 1, 1)

        self.versionLabel = QLabel(self.containerWidget)
        self.versionLabel.setObjectName(u"versionLabel")
        self.versionLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.versionLabel, 13, 1, 1, 1)

        self.flashToolSettings = QComboBox(self.containerWidget)
        self.flashToolSettings.setObjectName(u"flashToolSettings")

        self.gridLayout_2.addWidget(self.flashToolSettings, 2, 1, 1, 1)

        self.serialPortsBox = QComboBox(self.containerWidget)
        self.serialPortsBox.setObjectName(u"serialPortsBox")

        self.gridLayout_2.addWidget(self.serialPortsBox, 0, 1, 1, 1)

        self.clearLogsButton = QPushButton(self.containerWidget)
        self.clearLogsButton.setObjectName(u"clearLogsButton")

        self.gridLayout_2.addWidget(self.clearLogsButton, 6, 2, 1, 1)

        self.fileName = QLineEdit(self.containerWidget)
        self.fileName.setObjectName(u"fileName")

        self.gridLayout_2.addWidget(self.fileName, 4, 1, 1, 1)

        self.flashToolSettingsLabel = QLabel(self.containerWidget)
        self.flashToolSettingsLabel.setObjectName(u"flashToolSettingsLabel")

        self.gridLayout_2.addWidget(self.flashToolSettingsLabel, 2, 0, 1, 1)

        self.label_2 = QLabel(self.containerWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_2, 8, 2, 1, 2)

        self.flashToolSubSettingsBox = QComboBox(self.containerWidget)
        self.flashToolSubSettingsBox.setObjectName(u"flashToolSubSettingsBox")

        self.gridLayout_2.addWidget(self.flashToolSubSettingsBox, 3, 1, 1, 1)

        self.uploadBoardButton = QPushButton(self.containerWidget)
        self.uploadBoardButton.setObjectName(u"uploadBoardButton")

        self.gridLayout_2.addWidget(self.uploadBoardButton, 8, 1, 1, 1)

        self.serialTXBox = QLineEdit(self.containerWidget)
        self.serialTXBox.setObjectName(u"serialTXBox")
        self.serialTXBox.setFont(font)

        self.gridLayout_2.addWidget(self.serialTXBox, 11, 1, 1, 1)


        self.gridLayout.addWidget(self.containerWidget, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 943, 33))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuEdit = QMenu(self.menubar)
        self.menuEdit.setObjectName(u"menuEdit")
        self.menu_Help = QMenu(self.menubar)
        self.menu_Help.setObjectName(u"menu_Help")
        self.menu_Tools = QMenu(self.menubar)
        self.menu_Tools.setObjectName(u"menu_Tools")
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menu_Tools.menuAction())
        self.menubar.addAction(self.menu_Help.menuAction())
        self.menuFile.addAction(self.actionOpen_File)
        self.menuEdit.addAction(self.actionRemote_Configurations)
        self.menuEdit.addAction(self.actionGithubPAT)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.action_Invalidate_Cache)
        self.menuEdit.addAction(self.action_Reload_App)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.action_Preferences)
        self.menu_Help.addAction(self.action_About)
        self.menu_Help.addAction(self.actionCheck_for_Updates)
        self.menu_Tools.addAction(self.actionCANLib_Kvaser)
        self.menu_Tools.addAction(self.action_Elf_Parser)
        self.menu_Tools.addSeparator()

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Flash Wiz", None))
        self.actionOpen_File.setText(QCoreApplication.translate("MainWindow", u"&Open...", None))
        self.actionAdd_External_Flashing_Tool.setText(QCoreApplication.translate("MainWindow", u"Add External &Flashing Tool Directory", None))
        self.actionAdd_External_Board_Directory.setText(QCoreApplication.translate("MainWindow", u"Add External &Board Directory", None))
        self.actionCheck_for_Updates.setText(QCoreApplication.translate("MainWindow", u"Check for &Updates", None))
        self.action_Reload_App.setText(QCoreApplication.translate("MainWindow", u"&Reload App", None))
        self.actionGithubPAT.setText(QCoreApplication.translate("MainWindow", u"&Github Personal Access Token...", None))
        self.actionRemote_Configurations.setText(QCoreApplication.translate("MainWindow", u"Remote &Configurations...", None))
        self.actionCANLib_Kvaser.setText(QCoreApplication.translate("MainWindow", u"&CAN", None))
        self.action_Elf_Parser.setText(QCoreApplication.translate("MainWindow", u"&Elf Parser", None))
        self.action_About.setText(QCoreApplication.translate("MainWindow", u"&About", None))
        self.actionClear_All_Settings.setText(QCoreApplication.translate("MainWindow", u"Clear All &Settings", None))
        self.action_Invalidate_Cache.setText(QCoreApplication.translate("MainWindow", u"&Invalidate Cache", None))
        self.action_Preferences.setText(QCoreApplication.translate("MainWindow", u"&Preferences...", None))
        self.baudRateBox.setItemText(0, QCoreApplication.translate("MainWindow", u"9600", None))
        self.baudRateBox.setItemText(1, QCoreApplication.translate("MainWindow", u"115200", None))
        self.baudRateBox.setItemText(2, QCoreApplication.translate("MainWindow", u"38400", None))
        self.baudRateBox.setItemText(3, QCoreApplication.translate("MainWindow", u"57600", None))

        self.label.setText(QCoreApplication.translate("MainWindow", u"Baud Rate", None))
        self.serialMonitorButton.setText(QCoreApplication.translate("MainWindow", u"Connect", None))
        self.refreshCOMPortButton.setText(QCoreApplication.translate("MainWindow", u"Refresh", None))
        self.comLabel.setText(QCoreApplication.translate("MainWindow", u"COM PORT", None))
        self.boardSelectLabel.setText(QCoreApplication.translate("MainWindow", u"Board Select", None))
        self.sendTXDataButton.setText(QCoreApplication.translate("MainWindow", u"Send Data", None))
        self.flashToolSubSettingsLabel.setText(QCoreApplication.translate("MainWindow", u"Flash Tool Sub-Settings", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Serial TX", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Logs", None))
        self.uploadButton.setText(QCoreApplication.translate("MainWindow", u"Open File", None))
        self.versionLabel.setText(QCoreApplication.translate("MainWindow", u"Version 0.0.0", None))
        self.clearLogsButton.setText(QCoreApplication.translate("MainWindow", u"Clear Logs", None))
        self.flashToolSettingsLabel.setText(QCoreApplication.translate("MainWindow", u"Flash Tool Settings", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Serial Connection Settings", None))
        self.uploadBoardButton.setText(QCoreApplication.translate("MainWindow", u"Upload to Board", None))
        self.serialTXBox.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Type data to send here...", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"&File", None))
        self.menuEdit.setTitle(QCoreApplication.translate("MainWindow", u"&Edit", None))
        self.menu_Help.setTitle(QCoreApplication.translate("MainWindow", u"&Help", None))
        self.menu_Tools.setTitle(QCoreApplication.translate("MainWindow", u"&Tools", None))
    # retranslateUi

