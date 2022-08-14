#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Version personnalisée du sélecteur de fichier :
Ajout d'une case à cocher.
L'utilisation de " ne pose pas de souci."""

# 220707 :
    # Refonte complète

# 220622 :
    # Remplacement de Path par QFileInfo
    # Création de la fonction Translation et modification de createWindow
    # Suppression de if __name__ == '__main__':

import sys

from PyQt5.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox, QLineEdit, QTreeView, QListView, QFileSystemModel, QPushButton
from PyQt5.QtCore import QCoreApplication, Qt, QFileInfo, QTranslator
from PyQt5.QtGui import QStandardItemModel


#############################################################################
class QFileDialogCustom(QFileDialog):
    #========================================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialisation de la valeur de retour
        self.FileSelected = ""


    #========================================================================
    def translation(self, App=None, Language="en_EN"):
        """Fonction de traduction des textes."""
        # App est l'application mère
        if not App:
            return

        # Dossier du logiciel
        AppFolder = QFileInfo(sys.argv[0]).absolutePath() + "/QFileDialogCustom"

        # Création d'un QTranslator
        appTranslator = QTranslator()

        # Traductions disponibles
        if Language in ("fr_FR", "cs_CZ", "es_ES", "tr_TR"):
            find = appTranslator.load("QFileDialogCustom{}".format(Language), AppFolder)

            # Chargement de la traduction si elle est dispo
            if find:
                App.installTranslator(appTranslator)


        # Dictionnaire des traductions
        self.Trad = {"OverWriteTitle": QCoreApplication.translate("QFileDialogCustom", "Already existing file"),
                     "OverWriteText": QCoreApplication.translate("QFileDialogCustom", "The <b>{}</b> file is already existing, overwrite it?")}


    #========================================================================
    def accept(self):
        """Vérification de la sélection avant acceptation définitive."""
        AcceptValide = True

        # lineEdit du nom du fichier, utilise pour ne pas être gêné avec l'utilisation de "
        lineEdit = self.findChild(QLineEdit, "fileNameEdit")

        # Si le texte est vide
        if not lineEdit.text():
            # Si c'est un fichier ce n'est pas normal
            if self.Type == "File":
                self.FileSelected = ""
                AcceptValide = False

            else:
                self.FileSelected = self.directory().absolutePath()

        else:
            self.FileSelected = "{}/{}".format(self.directory().absolutePath(), lineEdit.text())

        # Fonction d'écrasement
        if self.Action == "Save" \
            and self.Type == "File" \
            and (self.Options is None or not "DontConfirmOverwrite" in self.Options) \
            and self.AlreadyExistsTest \
            and QFileInfo(self.FileSelected).exists():
                # Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, self.Trad["OverWriteTitle"], self.Trad["OverWriteText"].format(self.FileSelected), QMessageBox.NoButton, self)
                dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                dialog.setDefaultButton(QMessageBox.Yes)
                dialog.setEscapeButton(QMessageBox.No)
                Choix = dialog.exec()

                # Si on ne remplace pas
                if Choix != QMessageBox.Yes:
                    AcceptValide = False

        # Bloque la validation si le fichier à ouvrir n'existe pas
        if self.Type == "File" and self.Action == "Open" and not QFileInfo(self.FileSelected).isFile():
            self.FileSelected = ""
            AcceptValide = False

        # Bloque la validation si ce n'est pas un dossier valide
        elif self.Type == "Folder" and not QFileInfo(self.FileSelected).isDir():
            self.FileSelected = ""
            AcceptValide = False

        # Valide ou non l'acceptation finale
        if AcceptValide:
            self.done(1)

        # Si rien n'est fait, la fenêtre de sélection reste affichée et fonctionnelle


    #========================================================================
    def createWindow(self, Type="File", Action="Open", WidgetToAdd=None, Flags=None, FileName=None, Options=None, AlreadyExistsTest=True, Language="en_EN", App=None):
        """Fonction affichant la fenêtre."""
        # Chargement de la langue
        if App:
            self.translation(App, Language)

        # Récupération des valeurs pour la fonction accept
        self.Type = Type
        self.Action = Action
        self.Options = Options
        self.AlreadyExistsTest = AlreadyExistsTest


        if Action == "Open":
            self.setAcceptMode(QFileDialog.AcceptOpen)

        elif Action == "Save":
            self.setAcceptMode(QFileDialog.AcceptSave)

        # La fenêtre indiquant que le fichier existe déjà n'indique pas l'adresse du fichier, j'en crée une moi-même
        self.setOption(QFileDialog.DontConfirmOverwrite, True)

        # Permet la customisation de la fenêtre comme l'ajout de d'un widget et ne bloque pas l'utilisation de " dans les noms
        self.setOption(QFileDialog.DontUseNativeDialog, True)

        self.setOption(QFileDialog.DontUseCustomDirectoryIcons, True)

        if Type == "File":
            self.setOption(QFileDialog.HideNameFilterDetails)

            if Action == "Open":
                self.setFileMode(QFileDialog.ExistingFile)

            elif Action == "Save":
                self.setFileMode(QFileDialog.AnyFile)

        elif Type == "Folder":
            self.setFileMode(QFileDialog.Directory)
            self.setOption(QFileDialog.ShowDirsOnly, True)

        if Flags != None:
            self.setWindowFlags(Flags)

        if Options != None:
            self.setOptions(Options)

         # Nécessaire car si on utilise HideNameFilterDetails et save, il utilise la 1ere extension dans le fichier
        if FileName != None:
            self.selectFile(FileName)

        # Ajout du widget à la fenêtre de dialogue
        if WidgetToAdd != None:
            layout = self.layout()
            layout.addWidget(WidgetToAdd, 4, 0, 4, 3)


        # Affichage de la fenêtre
        self.exec()


        # Renvoi du texte final
        return self.FileSelected

