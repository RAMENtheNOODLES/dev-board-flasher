# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preferences.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QFontComboBox, QGridLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QTabWidget, QWidget)

class Ui_PreferencesWindow(object):
    def setupUi(self, PreferencesWindow):
        if not PreferencesWindow.objectName():
            PreferencesWindow.setObjectName(u"PreferencesWindow")
        PreferencesWindow.setWindowModality(Qt.WindowModality.ApplicationModal)
        PreferencesWindow.resize(400, 293)
        PreferencesWindow.setModal(True)
        self.gridLayout_2 = QGridLayout(PreferencesWindow)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.tabWidget = QTabWidget(PreferencesWindow)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setTabBarAutoHide(False)
        self.general = QWidget()
        self.general.setObjectName(u"general")
        self.gridLayout = QGridLayout(self.general)
        self.gridLayout.setObjectName(u"gridLayout")
        self.saveSettingsBtn = QPushButton(self.general)
        self.saveSettingsBtn.setObjectName(u"saveSettingsBtn")

        self.gridLayout.addWidget(self.saveSettingsBtn, 4, 1, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer_2, 0, 1, 1, 1)

        self.defaultsBtn = QPushButton(self.general)
        self.defaultsBtn.setObjectName(u"defaultsBtn")

        self.gridLayout.addWidget(self.defaultsBtn, 3, 1, 1, 1)

        self.fontComboBox = QFontComboBox(self.general)
        self.fontComboBox.setObjectName(u"fontComboBox")

        self.gridLayout.addWidget(self.fontComboBox, 1, 1, 1, 1)

        self.label = QLabel(self.general)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)

        self.fontSizeBox = QSpinBox(self.general)
        self.fontSizeBox.setObjectName(u"fontSizeBox")
        self.fontSizeBox.setMinimum(8)
        self.fontSizeBox.setMaximum(48)

        self.gridLayout.addWidget(self.fontSizeBox, 2, 1, 1, 1)

        self.label_2 = QLabel(self.general)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)

        self.tabWidget.addTab(self.general, "")
        self.advanced = QWidget()
        self.advanced.setObjectName(u"advanced")
        self.gridLayout_3 = QGridLayout(self.advanced)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_3.addItem(self.verticalSpacer, 0, 0, 1, 1)

        self.clearAllSettingsBtn = QPushButton(self.advanced)
        self.clearAllSettingsBtn.setObjectName(u"clearAllSettingsBtn")

        self.gridLayout_3.addWidget(self.clearAllSettingsBtn, 3, 0, 1, 1)

        self.importSettingsBtn = QPushButton(self.advanced)
        self.importSettingsBtn.setObjectName(u"importSettingsBtn")

        self.gridLayout_3.addWidget(self.importSettingsBtn, 1, 0, 1, 1)

        self.exportSettingsBtn = QPushButton(self.advanced)
        self.exportSettingsBtn.setObjectName(u"exportSettingsBtn")

        self.gridLayout_3.addWidget(self.exportSettingsBtn, 2, 0, 1, 1)

        self.tabWidget.addTab(self.advanced, "")

        self.gridLayout_2.addWidget(self.tabWidget, 1, 1, 1, 1)


        self.retranslateUi(PreferencesWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(PreferencesWindow)
    # setupUi

    def retranslateUi(self, PreferencesWindow):
        PreferencesWindow.setWindowTitle(QCoreApplication.translate("PreferencesWindow", u"Preferences", None))
        self.saveSettingsBtn.setText(QCoreApplication.translate("PreferencesWindow", u"Save Settings", None))
        self.defaultsBtn.setText(QCoreApplication.translate("PreferencesWindow", u"Revert to Defaults", None))
        self.label.setText(QCoreApplication.translate("PreferencesWindow", u"App Font", None))
        self.fontSizeBox.setSuffix(QCoreApplication.translate("PreferencesWindow", u"pt", None))
        self.label_2.setText(QCoreApplication.translate("PreferencesWindow", u"Font Size", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.general), QCoreApplication.translate("PreferencesWindow", u"General", None))
        self.clearAllSettingsBtn.setText(QCoreApplication.translate("PreferencesWindow", u"Clear All Settings", None))
        self.importSettingsBtn.setText(QCoreApplication.translate("PreferencesWindow", u"Import Settings", None))
        self.exportSettingsBtn.setText(QCoreApplication.translate("PreferencesWindow", u"Export Settings", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.advanced), QCoreApplication.translate("PreferencesWindow", u"Advanced", None))
    # retranslateUi

