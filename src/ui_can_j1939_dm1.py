# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'can_j1939_dm1.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QGridLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(404, 308)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.openFMIFile = QPushButton(Dialog)
        self.openFMIFile.setObjectName(u"openFMIFile")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.openFMIFile.sizePolicy().hasHeightForWidth())
        self.openFMIFile.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.openFMIFile, 2, 3, 1, 1)

        self.dM1FMILabel = QLabel(Dialog)
        self.dM1FMILabel.setObjectName(u"dM1FMILabel")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.dM1FMILabel.sizePolicy().hasHeightForWidth())
        self.dM1FMILabel.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.dM1FMILabel, 2, 0, 1, 1)

        self.dM1SPNLabel = QLabel(Dialog)
        self.dM1SPNLabel.setObjectName(u"dM1SPNLabel")
        sizePolicy1.setHeightForWidth(self.dM1SPNLabel.sizePolicy().hasHeightForWidth())
        self.dM1SPNLabel.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.dM1SPNLabel, 0, 0, 1, 1)

        self.dM1SPNLineEdit = QLineEdit(Dialog)
        self.dM1SPNLineEdit.setObjectName(u"dM1SPNLineEdit")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.dM1SPNLineEdit.sizePolicy().hasHeightForWidth())
        self.dM1SPNLineEdit.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.dM1SPNLineEdit, 0, 1, 1, 2)

        self.openSPNFile = QPushButton(Dialog)
        self.openSPNFile.setObjectName(u"openSPNFile")
        sizePolicy.setHeightForWidth(self.openSPNFile.sizePolicy().hasHeightForWidth())
        self.openSPNFile.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.openSPNFile, 0, 3, 1, 1)

        self.dM1FMILineEdit = QLineEdit(Dialog)
        self.dM1FMILineEdit.setObjectName(u"dM1FMILineEdit")
        sizePolicy2.setHeightForWidth(self.dM1FMILineEdit.sizePolicy().hasHeightForWidth())
        self.dM1FMILineEdit.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.dM1FMILineEdit, 2, 2, 1, 1)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        sizePolicy2.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy2)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setCenterButtons(True)

        self.gridLayout.addWidget(self.buttonBox, 3, 2, 1, 1)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.openFMIFile.setText(QCoreApplication.translate("Dialog", u"Open File", None))
        self.dM1FMILabel.setText(QCoreApplication.translate("Dialog", u"DM1 FMI", None))
        self.dM1SPNLabel.setText(QCoreApplication.translate("Dialog", u"DM1 SPN", None))
        self.openSPNFile.setText(QCoreApplication.translate("Dialog", u"Open File", None))
    # retranslateUi

