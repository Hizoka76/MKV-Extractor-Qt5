#!/usr/bin/python3
# -*- coding: utf-8 -*-


"""Logiciel graphique d'extraction des pistes de fichiers MKV."""

###############################
### Importation des modules ###
###############################
try:
    import sys
except:
    exit("Error: Impossible to find the sys module !")

# Utilisé pour envoyer plusieurs infos via les connexions
try:
    from functools import partial
except:
    exit("Error: Impossible to find partial from the functools module !")

# Utile pour le calcul de la progression de la conversion en ac3
try:
    from datetime import timedelta
except:
    exit("Error: Impossible to find timedelta from the datetime module !")

# Nécessaire au traitement des infos de mkvmerge
try:
    import json
except:
    exit("Error: Impossible to find the json module !")

# Pour le reboot, facultatif
try:
    from os import execl
except:
    print("Warning: Impossible to find execl from the os module ! Impossible to reboot with the right click on exit button.")
    pass

# Pour la gestion de la pause
try:
    import psutil
except:
    print("Warning: Impossible to find the psutil module ! Impossible to use pause button.")
    pass


# Modules Qt
from PyQt5.QtWidgets import QAction,QActionGroup, QApplication, QCheckBox, QComboBox, QDesktopWidget, QDialog, QDialogButtonBox, QDockWidget, QFileDialog, QHBoxLayout, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QShortcut, QStyleFactory, QSystemTrayIcon, QTableWidgetItem, QTextEdit, QToolButton, QVBoxLayout, QWidget

from PyQt5.QtCore import pyqtSignal as Signal, QCoreApplication, QDir, QFile, QFileInfo, QLibraryInfo, QLocale, QMimeDatabase, QMimeType, QProcess, QSettings, QSize, QStandardPaths, QStorageInfo, Qt, QTemporaryDir, QThread, QTranslator, QUrl

from PyQt5.QtGui import QCursor, QDesktopServices, QFont, QIcon, QKeySequence, QPainter, QPixmap, QTextCursor


# Modules maisons
from QFileDialogCustom.QFileDialogCustom import QFileDialogCustom # Version personnalisée de sélecteur de fichier
from WhatsUp.WhatsUp import WhatsUp
from ui_MKVExtractorQt5 import Ui_mkv_extractor_qt5 # Utilisé pour la fenêtre principale
from CodecListFile import CodecList # Liste des codecs



#############################################################################
def MultiVar(*Values):
    """Fonction permettant d'utiliser la 1ere valeur valide d'une liste."""
    for Value in Values:
        if Value:
            return Value



#############################################################################
class QuitButton(QPushButton):
    """Sous classement d'un QPushButton permettant la prise en charge du clic droit sur le bouton quitter."""
    ### Création du signal de reboot
    signalReboot = Signal()

    def mousePressEvent(self, event):
        """Fonction de récupération des touches souris utilisées."""
        ### Animation du clic sur le bouton lors du clic droit
        MKVExtractorQt5Class.ui.soft_quit.animateClick()

        ### Envoi du signal reboot si utilisation du clic droit
        if event.button() == Qt.RightButton:
            self.signalReboot.emit()

        ### Acceptation de l'événement
        return super(type(self), self).mousePressEvent(event)



#############################################################################
class QActionCustom(QAction):
    """Sous classement d'un QAction pour y modifier l'affichage de l'info-bulle en fonction de l'état de l'action."""
    def __init__(self, Parent=None):
        super().__init__(Parent)

        ### Info-bulle par défaut
        self.ToolTip = ""

        ### État par défaut de l'action
        self.Enabled = self.isEnabled()


    #========================================================================
    def setEnabled(self, State):
        """Sous-classement de la fonction pour mise à jour de l'info-bulle."""
        ### État de la coche pour être sûr d'avoir le bon état
        self.Enabled = State

        ### Cache l'info-bulle
        if State:
            self.setToolTip("")

        ### Affiche l'info-bulle
        else:
            self.setToolTip(self.ToolTip)

        ### Continue normalement la fonction
        super().setEnabled(State)


    #========================================================================
    def setToolTip(self, ToolTip):
        """Sous-classement de la fonction pour prise en compte de l'état de l'action."""
        ### Mise à jour du texte (lors des changements de langue)
        if ToolTip:
            self.ToolTip = ToolTip

        ### Si l'action est dégrisée, on n'envoie pas l'info-bulle
        if self.Enabled:
            super().setToolTip("")

        ### Si l'action est grisée, on affiche l'info-bulle
        else:
            super().setToolTip(ToolTip)



#############################################################################
class QActionMenuCustom(QAction):
    """Sous classement d'un QAction pour automatiser l'activation du ToolButton en fonction de l'état de l'action."""
    def __init__(self, Parent=None, *args, **kwargs):
        super().__init__(Parent, *args, **kwargs)

        ### ToolButton parent
        self.ToolButton = None

        ### Connexion de la fonction au changement d'état du QAction
        self.triggered.connect(self.toolButtonCheck)


    #========================================================================
    def toolButtonCheck(self, value):
        """Fonction cochant le ToolButton automatiquement si besoin."""
        ### Si la case est décochée, on ne fait rien de particulier
        if not value:
            return

        ### Si on ne connaît pas le ToolButton, on le recherche
        if not self.ToolButton:
            # Parent 1 : QMenu
            # Parent 2 : QToolButton
            self.ToolButton = self.parent().parent()

            # Si ce n'est pas un QToolButton, on ne fait rien
            if not isinstance(self.ToolButton, QToolButton):
                return

        ### Si le ToolButton est actif et non coché, on le coche
        if self.ToolButton.isEnabled() and not self.ToolButton.isChecked():
            self.ToolButton.setChecked(True)



#############################################################################
class QTextEditCustom(QTextEdit):
    """Sous classement d'un QTextEdit pour y modifier le menu du clic droit."""
    def __init__(self, Parent=None):
        super().__init__(Parent)

        ### Création des raccourcis claviers qui serviront aux actions
        ExportShortcut = QShortcut("ctrl+e", self)
        ExportShortcut.activated.connect(self.ExportAction)

        CleanShortcut = QShortcut("ctrl+d", self)
        CleanShortcut.activated.connect(self.CleanAction)


    #========================================================================
    def contextMenuEvent(self, event):
        """Fonction de la création du menu contextuel."""
        ### Chargement du fichier qm de traduction (anglais utile pour les textes singulier/pluriel)
        appTranslator = QTranslator() # Création d'un QTranslator

        ## Pour les traductions disponibles
        if Configs.value("Language") in ("fr_FR", "cs_CZ", "es_ES", "tr_TR"):
            # Chargement de la traduction
            if appTranslator.load("Languages/MKVExtractorQt5_{}".format(Configs.value("Language")), AppFolder):
                app.installTranslator(appTranslator)

        ### Création d'un menu standard
        Menu = self.createStandardContextMenu()

        ### Création et ajout de l'action de nettoyage (icône, nom, raccourci)
        Clean = QAction(QIcon.fromTheme("edit-clear", QIcon(":/img/edit-clear.png")), QCoreApplication.translate("QTextEditCustom", "Clean the information fee&dback box"), Menu)
        Clean.setShortcut(QKeySequence("ctrl+d"))
        Clean.triggered.connect(self.CleanAction)
        Menu.addSeparator()
        Menu.addAction(Clean)

        ### Création et ajout de l'action d'export (icône, nom, raccourci)
        Export = QAction(QIcon.fromTheme("document-export", QIcon(":/img/document-export.png")), QCoreApplication.translate("QTextEditCustom", "&Export info to ~/InfoMKVExtractorQt5.txt"), Menu)
        Export.setShortcut(QKeySequence("ctrl+e"))
        Export.triggered.connect(self.ExportAction)
        Menu.addSeparator()
        Menu.addAction(Export)

        ### Grise les actions si le texte est vide
        if not self.toPlainText():
            Export.setEnabled(False)
            Clean.setEnabled(False)

        ### Affichage du menu là où se trouve la souris
        Menu.exec(QCursor.pos())

        event.accept()


    #========================================================================
    def CleanAction(self, *args):
        """Fonction de nettoyage du texte."""
        self.clear()


    #========================================================================
    def ExportAction(self, *args):
        """Fonction d'exportation du texte."""
        ### Récupération du texte
        text = self.toPlainText()

        ### Arrêt de la fonction si pas de texte
        if not text:
            return

        ### Création du lien vers le fichier
        ExportedFile = QFile(QDir.homePath() + '/InfoMKVExtractorQt5.txt')

        ### Ouverture du fichier en écriture
        ExportedFile.open(QFile.WriteOnly)

        ### Envoie du texte au format bytes
        ExportedFile.write(text.encode())

        ### Fermeture du fichier
        ExportedFile.close()



#############################################################################
class MKVExtractorQt5(QMainWindow):
    """Fenêtre principale du logiciel."""
    def __init__(self, parent=None):
        """Fonction d'initialisation appelée au lancement de la classe."""

        ### Variables
        self.CloseMode = ""
        self.SoftwareChangedDone = False

        ### Commandes à ne pas toucher
        super(MKVExtractorQt5, self).__init__(parent)
        self.ui = Ui_mkv_extractor_qt5()
        self.ui.setupUi(self) # Lance la fonction définissant tous les widgets du fichier UI
        self.setWindowTitle('MKV Extractor Qt v{}'.format(app.applicationVersion())) # Nom de la fenêtre
        self.show() # Affichage de la fenêtre principale

        ### Création du QTextEditCustom affichant le retour avec un menu custom
        self.ui.reply_info = QTextEditCustom(self.ui.dockWidgetContents)
        self.ui.reply_info.setReadOnly(True)
        self.ui.reply_info.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.ui.reply_info.setLineWrapMode(QTextEdit.WidgetWidth)
        self.ui.reply_info.setTextInteractionFlags(Qt.TextSelectableByKeyboard|Qt.TextSelectableByMouse)
        self.ui.reply_info.resize(100, 150)
        self.ui.verticalLayout_8.addWidget(self.ui.reply_info)

        ### Gestion de la fenêtre
        # Remet les widgets comme ils l'étaient
        if Configs.contains("WinState"):
            self.restoreState(Configs.value("WinState"))

        # Repositionne et donne la bonne taille à la fenêtre
        if Configs.value("WindowAspect") and Configs.contains("WinGeometry"):
            self.restoreGeometry(Configs.value("WinGeometry"))

        # Centrage de la fenêtre, en fonction de sa taille et de la taille de l'écran
        else:
            size_ecran = QDesktopWidget().screenGeometry() # Taille de l'écran
            self.move(int((size_ecran.width() - self.geometry().width()) / 2), int((size_ecran.height() - self.geometry().height()) / 2))

        ### Modifications graphiques de boutons
        self.ui.mkv_stop.setVisible(False) # Cache le bouton d'arrêt
        self.ui.mkv_pause.setVisible(False) # Cache le bouton de pause

        # Grise le bouton pause si psutil n'est pas présent
        if not 'psutil' in globals():
            self.ui.mkv_pause.setEnabled(False)


        ### Active les tooltips des actions dans les menus
        for Widget in (self.ui.menuFichier, self.ui.menuActions, self.ui.menuAide, self.ui.menuAide):
            Widget.setToolTipsVisible(True)

        ### Remplissage du menu des styles Qt disponibles
        for Style in QStyleFactory.keys(): # Styles disponibles
            QtStyleList[Style] = QAction(Style, self) # Création d'une action stockée dans le dico
            QtStyleList[Style].triggered.connect(partial(self.StyleChange, Style)) # Action créée pour cet élément
            self.ui.option_style.addAction(QtStyleList[Style]) # Ajout de l'action à la liste

            # Si c'est le style actuel
            if Style.lower() == Configs.value("QtStyle").lower():
                self.StyleChange(Style)

        ### Mise en place du system tray
        menulist = QMenu() # Création d'un menu
        icon = QIcon.fromTheme("application-exit", QIcon(":/img/application-exit.png"))
        self.SysTrayQuit = QAction(icon, '', self,) # Création d'un item sans texte
        menulist.addAction(self.SysTrayQuit) # Ajout de l'action à la liste

        self.SysTrayIcon = QSystemTrayIcon(QIcon.fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")), self)
        self.SysTrayIcon.setContextMenu(menulist)

        if not Configs.value("SysTray"):
            self.ui.option_systray.setChecked(False)

        else:
            self.SysTrayIcon.show()

        ### Menu du bouton de conversion des sous titres
        menulist = QMenu(self.ui.option_subtitles) # Création d'un menu
        menulist.setToolTipsVisible(True) # Active les tooltips des actions

        ## SUP/PGS => SUB
        ag = QActionGroup(self) # Création d'un actiongroup

        # Conversion FFMpeg
        Sup2Sub[1] = QActionMenuCustom('', menulist, checkable=True) # Création d'un item sans texte
        Sup2Sub[1].setIcon(QIcon.fromTheme("ffmpeg", QIcon(":/img/ffmpeg.png")))
        menulist.addAction(ag.addAction(Sup2Sub[1])) # Ajout de l'item radio dans la sous liste

        # Conversion BDSup2Sub
        Sup2Sub[2] = QActionMenuCustom('', menulist, checkable=True) # Création d'un item sans texte
        Sup2Sub[2].setIcon(QIcon.fromTheme("BDSup2Sub", QIcon(":/img/BDSup2Sub.png")))
        menulist.addAction(ag.addAction(Sup2Sub[2])) # Ajout de l'item radio dans la sous liste

        # Ouvrir BDSup2Sub lors de la conversion
        Sup2Sub[3] = QActionMenuCustom('', menulist, checkable=True) # Création d'un item sans texte
        Sup2Sub[3].setIcon(QIcon.fromTheme("BDSup2Sub", QIcon(":/img/BDSup2Sub.png")))
        menulist.addAction(ag.addAction(Sup2Sub[3])) # Ajout de l'item radio dans la sous liste

        menulist.addSeparator()

        ## SUB => SRT
        ag = QActionGroup(self) # Création d'un actiongroup

        # Conversion
        Sub2Srt[1] = QActionMenuCustom('', menulist, checkable=True) # Création d'un item sans texte
        Sub2Srt[1].setIcon(QIcon.fromTheme("Qtesseract5", QIcon(":/img/qtesseract5.png")))
        menulist.addAction(ag.addAction(Sub2Srt[1])) # Ajout de l'item radio dans la sous liste

        # Ouvrir Qtesseract5 lors de la conversion
        Sub2Srt[2] = QActionMenuCustom('', menulist, checkable=True) # Création d'un item sans texte
        Sub2Srt[2].setIcon(QIcon.fromTheme("Qtesseract5", QIcon(":/img/qtesseract5.png")))
        menulist.addAction(ag.addAction(Sub2Srt[2])) # Ajout de l'item radio dans la sous liste

        self.ui.option_subtitles.setMenu(menulist) # Envoie de la liste dans le bouton

        ### Menu du bouton de conversion audio
        menulist = QMenu(self.ui.option_audio) # Création d'un menu
        menulist.setToolTipsVisible(True) # Active les tooltips des actions

        icon = QIcon.fromTheme("ffmpeg", QIcon(":/img/ffmpeg.png"))
        self.option_ffmpeg = QActionMenuCustom(icon, '', menulist, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_ffmpeg) # Ajout de l'action à la liste

        icon = QIcon.fromTheme("audio-ac3", QIcon(":/img/audio-ac3.png"))
        self.option_to_ac3 = QActionMenuCustom(icon, '', menulist, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_to_ac3) # Ajout de l'action à la liste

        icon = QIcon.fromTheme("stereo", QIcon(":/img/stereo.png"))
        self.option_stereo = QActionMenuCustom(icon, '', menulist, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_stereo) # Ajout de l'action à la liste

        self.RatesMenu = QMenu(self) # Création d'un sous menu
        ag = QActionGroup(self) # Création d'un actiongroup

        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]: # Qualités utilisables
            QualityList[nb] = QActionMenuCustom('', menulist, checkable=True) # Création d'un item radio sans nom
            self.RatesMenu.addAction(ag.addAction(QualityList[nb])) # Ajout de l'item radio dans la sous liste

        menulist.addMenu(self.RatesMenu) # Ajout du sous menu dans le menu

        self.PowerMenu = QMenu(self) # Création d'un sous menu
        ag = QActionGroup(self) # Création d'un actiongroup

        for nb in [2, 3, 4, 5]: # Puissances utilisables
            PowerList[nb] = QActionMenuCustom('', menulist, checkable=True) # Création d'un item radio sans nom
            self.PowerMenu.addAction(ag.addAction(PowerList[nb])) # Ajout de l'item radio dans la sous liste

        menulist.addMenu(self.PowerMenu) # Ajout du sous menu dans le menu

        self.ui.option_audio.setMenu(menulist) # Envoie de la liste dans le bouton

        ### Menu du bouton de ré-encapsulage
        menulist = QMenu(self.ui.option_reencapsulate) # Création d'un menu

        icon = QIcon.fromTheme("document-edit", QIcon(":/img/document-edit.png"))
        self.option_subtitles_open = QActionMenuCustom(icon, '', menulist, checkable=True) # Création d'une action cochable sans texte
        menulist.addAction(self.option_subtitles_open) # Ajout de l'action à la liste

        self.ui.option_reencapsulate.setMenu(menulist) # Envoie de la liste dans le bouton

        ### Création des actions personnalisées
        self.mkv_info = QActionCustom(self.ui.menuActions)
        self.mkv_info.setEnabled(False)
        icon = QIcon.fromTheme("mkvinfo", QIcon(":/img/mkvinfo.png"))
        self.mkv_info.setIcon(icon)
        self.mkv_info.setShortcut("F5")
        self.mkv_info.setObjectName("mkv_info")
        self.ui.menuActions.addAction(self.mkv_info)

        self.mkv_mkvtoolnix = QActionCustom(self.ui.menuActions)
        self.mkv_mkvtoolnix.setEnabled(False)
        icon = QIcon.fromTheme("mkvmerge", QIcon(":/img/mkvmerge.png"))
        self.mkv_mkvtoolnix.setIcon(icon)
        self.mkv_mkvtoolnix.setShortcut("F6")
        self.mkv_mkvtoolnix.setObjectName("mkv_mkvtoolnix")
        self.ui.menuActions.addAction(self.mkv_mkvtoolnix)

        self.ui.menuActions.addSeparator()

        self.mk_validator = QActionCustom(self.ui.menuActions)
        self.mk_validator.setEnabled(False)
        icon = QIcon.fromTheme("dialog-ok", QIcon(":/img/dialog-ok.png"))
        self.mk_validator.setIcon(icon)
        self.mk_validator.setShortcut("F7")
        self.mk_validator.setObjectName("mk_validator")
        self.ui.menuActions.addAction(self.mk_validator)

        self.mk_clean = QActionCustom(self.ui.menuActions)
        self.mk_clean.setEnabled(False)
        icon = QIcon.fromTheme("draw-eraser", QIcon(":/img/draw-eraser.png"))
        self.mk_clean.setIcon(icon)
        self.mk_clean.setShortcut("F8")
        self.mk_clean.setObjectName("mk_clean")
        self.ui.menuActions.addAction(self.mk_clean)

        self.ui.menuActions.addSeparator()

        self.mkv_view = QActionCustom(self.ui.menuActions)
        self.mkv_view.setEnabled(False)
        icon = QIcon.fromTheme("document-preview", QIcon(":/img/document-preview.png"))
        self.mkv_view.setIcon(icon)
        self.mkv_view.setShortcut("F9")
        self.mkv_view.setObjectName("mkv_view")
        self.ui.menuActions.addAction(self.mkv_view)

        self.ui.menuActions.addSeparator()

        self.mkv_execute_2 = QActionCustom(self.ui.menuActions)
        self.mkv_execute_2.setEnabled(False)
        icon = QIcon.fromTheme("run-build", QIcon(":/img/run-build.png"))
        self.mkv_execute_2.setIcon(icon)
        self.mkv_execute_2.setShortcut("F4")
        self.mkv_execute_2.setObjectName("mkv_execute_2")
        self.ui.menuActions.addAction(self.mkv_execute_2)

        ### Désactive le bouton whatsup s'il n'y a pas de changelog
        if not QFileInfo('/usr/share/doc/mkv-extractor-qt5/changelog.Debian.gz').exists():
            self.ui.whatsup.setEnabled(False)

        ### Recherche ffmpeg et avconv qui font la même chose
        # Désactive les radiobutton et l'option de conversion
        if not self.SoftIsExec("FFMpeg|AvConv"):
            TempValues.setValue("FFMpeg", False)
            self.option_ffmpeg.setEnabled(False)
            self.ui.option_audio.setEnabled(False)

        # Sélection automatique ffmpeg
        elif self.SoftIsExec("FFMpeg") and not self.SoftIsExec("AvConv"):
            TempValues.setValue("FFMpeg", True)
            self.option_ffmpeg.setEnabled(False)

        # Sélection automatique avconv
        elif not self.SoftIsExec("FFMpeg") and self.SoftIsExec("AvConv"):
            TempValues.setValue("FFMpeg", False)
            self.option_ffmpeg.setEnabled(False)

        # Les deux sont dispo, utilisation de ffmpeg par défaut
        else:
            TempValues.setValue("FFMpeg", True)
            self.option_ffmpeg.setChecked(True)

        ### Activation et modifications des préférences
        if TempValues.value("AudioQuality") in [2, 3, 4, 5]:
            QualityList[TempValues.value("AudioQuality")].setChecked(True) # Coche de la bonne valeur

        if TempValues.value("AudioBoost") in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
            PowerList[TempValues.value("AudioBoost")].setChecked(True) # Coche de la bonne valeur

        if not Configs.value("RecentInfos"):
            self.ui.option_recent_infos.setChecked(True)

        if not Configs.value("WindowAspect"):
            self.ui.option_aspect.setChecked(False)

        if not Configs.value("DelTempFiles"):
            self.ui.option_del_temp_files.setChecked(False)

        if Configs.value("DebugMode"):
            self.ui.option_debug.setChecked(True)

        if Configs.value("SysTrayMinimise") and Configs.value("SysTray"):
            self.ui.option_minimise_systray.setChecked(True)

        if not Configs.value("Feedback"):
            self.ui.option_feedback.setChecked(False)
            self.ui.feedback_widget.hide()

        if Configs.value("FeedbackBlock"):
            self.ui.option_feedback_block.setChecked(True)
            self.ui.feedback_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)

        ### Définition des liens location et widget
        self.WidgetsLocation = {
            "Location/BDSup2Sub": Sup2Sub[2],
            "Location/FFMpeg": self.option_ffmpeg,
            "Location/MKClean": self.mk_clean,
            "Location/MKVInfo": self.mkv_info,
            "Location/MKVToolNix": self.mkv_mkvtoolnix,
            "Location/MKValidator": self.mk_validator,
            "Location/Qtesseract5": Sub2Srt[1]
            }

        ### Gestion la traduction, le widget n'est pas encore connecté
        Langue = Configs.value("Language")[0:2].lower()
        if Langue in ("fr", "cs", "es", "tr"):
            Infos = {
                "fr": [self.ui.lang_fr, "fr_FR"],
                "cs": [self.ui.lang_cs, "cs_CZ"],
                "es": [self.ui.lang_es, "es_ES"],
                "tr": [self.ui.lang_tr, "tr_TR"]
                }

            # Sélection de la langue
            Infos[Langue][0].setChecked(True)
            self.OptionLanguage(Infos[Langue][1])

        # Force le chargement de traduction si c'est la langue anglaise (par défaut)
        else:
            self.OptionLanguage("en_US")

        ### Réinitialisation du dossier de sortie s'il n'existe pas
        if not Configs.contains("OutputFolder") or not QFileInfo(Configs.value("OutputFolder")).isDir():
            Configs.setValue("OutputFolder", QDir.homePath())
            Configs.setValue("OutputSameFolder", True)

        ### Définition de la taille des colonnes du tableau des pistes
        largeur = int((self.ui.mkv_tracks.size().width() - 75) / 3) # Calcul pour définir la taille des colonnes
        self.ui.mkv_tracks.setMouseTracking(True) # Nécessaire à l'affichage des statustip
        self.ui.mkv_tracks.hideColumn(0) # Cache la 1ere colonne
        self.ui.mkv_tracks.setColumnWidth(1, 25) # Définit la colonne 1 à 25px
        self.ui.mkv_tracks.setColumnWidth(2, 25) # Définit la colonne 2 à 25px
        self.ui.mkv_tracks.setColumnWidth(3, largeur + 30) # Définit la colonne 4
        self.ui.mkv_tracks.setColumnWidth(4, largeur + 15) # Définit la colonne 5
        self.ui.mkv_tracks.horizontalHeader().setStretchLastSection(True) # Définit la place restante à la dernière colonne

        ### Récupération du retour de MKVMerge
        for line in self.LittleProcess('mkvmerge', ['--list-languages']):
            ## Exclue la ligne contenant les ---
            if line[0] != "-":
                # Récupère la 2eme colonne, la langue en 3 lettres
                line = line.split('|')[1].strip()

                # Vérifie que le résultat est bien de 3 caractères puis ajoute la langue
                if len(line) == 3:
                    MKVLanguages.append(line)

        # Range les langues dans l'ordre alphabétique
        MKVLanguages.sort()

        ### QProcess (permet de lancer les jobs en fond de taches)
        self.process = QProcess() # Création du QProcess
        self.process.setProcessChannelMode(1) # Unification des 2 sorties (normale + erreur) du QProcess

        ### Connexions de la grande partie des widgets (les autres sont ci-dessus ou via le fichier UI)
        self.ConnectActions()

        ### Recherche et mise à jour de leurs adresses dans softwares locations
        # => La fonction est appelée via les langages
        #self.SoftwareFinding()

        ### Création du dossier temporaire
        self.FolderTempCreate()

        ### Cache les boutons non fonctionnels
        if Configs.value("HideOptions"):
            self.ui.option_hide_options.setChecked(True)

        ### Dans le cas du lancement du logiciel avec ouverture de fichier
        # En cas d'argument simple
        if len(sys.argv) == 2:
            # Teste le fichier avant de l'utiliser
            if QFileInfo(sys.argv[1]).exists():
                Configs.setValue("InputFile", sys.argv[1])

            # En cas d'erreur
            else:
                QMessageBox(QMessageBox.Critical, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgExist"].format(sys.argv[1]), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

        # En cas arguments multiples
        elif len(sys.argv) > 2:
            # Suppression du fichier d'entrée
            Configs.remove("InputFile")

            # Message d'erreur
            QMessageBox(QMessageBox.Critical, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgNb"].format("<br/> - ".join(sys.argv[1:])), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

        # En cas de l'utilisation du dernier fichier ouvert
        elif Configs.value("InputFile") and Configs.value("LastFile"):
            # Si le fichier n'existe plus et qu'on ne cache pas le message, on affiche le message d'erreur
            if not QFileInfo(Configs.value("InputFile")).isFile() and not Configs.value("ConfirmErrorLastFile"):
                Configs.remove("InputFile")

                # Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, self.Trad["ErrorLastFileTitle"], self.Trad["ErrorLastFileText"], QMessageBox.NoButton, self)
                CheckBox = QCheckBox(self.Trad["Convert5"]) # Reprise du même texte
                dialog.setCheckBox(CheckBox)
                dialog.setStandardButtons(QMessageBox.Close)
                dialog.setDefaultButton(QMessageBox.Close)
                dialog.exec()

                Configs.setValue("ConfirmErrorLastFile", CheckBox.isChecked()) # Mise en mémoire de la case à cocher

        # Dans les autres cas, on vire le nom du fichier
        elif Configs.contains("InputFile"):
            Configs.remove("InputFile")


        QCoreApplication.processEvents()

        ### Ouverture du fichier indiqué en entrée
        if Configs.contains("InputFile"):
            QCoreApplication.processEvents()
            self.InputFile(Configs.value("InputFile"))


    #========================================================================
    def LittleProcess(self, Program, Arguments):
        """Petite fonction récupérant les retours de process simples."""
        # Command est le nom du logiciel à utiliser
        # Arguments est la liste des arguments
        # Utilisation de ce système plutôt qu'une simple string donnée à start() qui ne comprend pas les " dans les noms'

        ### Envoie d'information en mode debug
        if Configs.value("DebugMode"):
            self.SetInfo(self.Trad["WorkCmd"].format(Program + ' ' + ' '.join(Arguments)), newline=True)

        ### Liste qui contiendra les retours
        reply = []

        ### Création du QProcess avec unification des 2 sorties (normale + erreur)
        process = QProcess()
        process.setProcessChannelMode(1)

        ### Préparation de la commande
        process.setProgram(Program)
        process.setArguments(Arguments)

        ### Exécution de la commande et attente de sa fin
        process.start()
        process.waitForFinished()

        ### Ajoute les lignes du retour dans la liste
        for line in bytes(process.readAllStandardOutput()).decode('utf-8').splitlines():
            reply.append(line)

        ### Renvoie le résultat
        return reply


    #========================================================================
    def ConnectActions(self):
        """Fonction faisant les connexions non faites par qtdesigner."""
        ### Connexions du menu File (au clic)
        self.ui.input_file.triggered.connect(self.InputFile)
        self.ui.output_folder.triggered.connect(self.OutputFolder)
        self.mkv_execute_2.triggered.connect(self.ui.mkv_execute.click)

        ### Connexions du menu Actions (au clic)
        self.mkv_info.triggered.connect(self.MKVInfoGui)
        self.mkv_mkvtoolnix.triggered.connect(self.MKVMergeGui)
        self.mk_validator.triggered.connect(self.MKValidator)
        self.mk_clean.triggered.connect(self.MKClean)
        self.mkv_view.triggered.connect(self.MKVView)

        ### Connexions du menu Options (au clic ou au coche)
        self.ui.option_recent_infos.toggled.connect(partial(self.OptionsValue, "RecentInfos"))
        self.ui.option_del_temp_files.toggled.connect(partial(self.OptionsValue, "DelTempFiles"))
        self.ui.option_configuration_table.triggered.connect(self.Configuration)
        self.ui.option_feedback.toggled.connect(partial(self.OptionsValue, "Feedback"))
        self.ui.option_feedback_block.toggled.connect(partial(self.OptionsValue, "FeedbackBlock"))
        self.ui.option_aspect.toggled.connect(partial(self.OptionsValue, "WindowAspect"))
        self.ui.option_hide_options.toggled.connect(partial(self.OptionsValue, "HideOptions"))
        self.ui.option_softwares_locations.triggered.connect(lambda: (self.ui.stackedMiddle.setCurrentIndex(2)))
        self.ui.lang_en.triggered.connect(partial(self.OptionLanguage, "en_US"))
        self.ui.lang_fr.triggered.connect(partial(self.OptionLanguage, "fr_FR"))
        self.ui.lang_cs.triggered.connect(partial(self.OptionLanguage, "cs_CZ"))
        self.ui.lang_es.triggered.connect(partial(self.OptionLanguage, "es_ES"))
        self.ui.lang_tr.triggered.connect(partial(self.OptionLanguage, "tr_TR"))

        ### Connexions du menu Help (au clic ou au coche)
        self.ui.option_debug.toggled.connect(partial(self.OptionsValue, "DebugMode"))
        self.ui.help_mkvextractorqt5.triggered.connect(self.HelpMKVExtractorQt5)
        self.ui.they_talk_about.triggered.connect(self.TheyTalkAbout)
        self.ui.about.triggered.connect(self.AboutMKVExtractorQt5)
        self.ui.about_qt.triggered.connect(lambda: QMessageBox.aboutQt(MKVExtractorQt5Class))
        self.ui.mkvtoolnix.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://mkvtoolnix.download/downloads.html")))
        self.ui.whatsup.triggered.connect(lambda: WhatsUp('/usr/share/doc/mkv-extractor-qt5/changelog.Debian.gz', 'mkv-extractor-qt5', self.Trad["WhatsUpTitle"], self))

        ### Connexion du dockwidget
        self.ui.feedback_widget.visibilityChanged.connect(self.FeedbackWidget)

        ### Connexions des widgets de configuration (au clic ou changement de contenu)
        self.ui.configuration_table.itemChanged.connect(self.ConfigurationEdit)
        self.ui.configuration_close.clicked.connect(lambda: (self.ui.stackedMiddle.setCurrentIndex(0)))
        self.ui.configuration_reset.clicked.connect(self.ConfigurationReset)

        ### Connexions des widgets des locations de logiciels
        self.ui.locations_close.clicked.connect(lambda: (self.ui.stackedMiddle.setCurrentIndex(0)))
        self.ui.locations_reset.clicked.connect(partial(self.SoftwareFinding, True))
        self.ui.button_avconv.clicked.connect(partial(self.SoftwareSelector, "Location/AvConv", self.ui.location_avconv))
        self.ui.button_bdsup2sub.clicked.connect(partial(self.SoftwareSelector, "Location/BDSup2Sub", self.ui.location_bdsup2sub))
        self.ui.button_ffmpeg.clicked.connect(partial(self.SoftwareSelector, "Location/FFMpeg", self.ui.location_ffmpeg))
        self.ui.button_mkclean.clicked.connect(partial(self.SoftwareSelector, "Location/MKClean", self.ui.location_mkclean))
        self.ui.button_mkvextract.clicked.connect(partial(self.SoftwareSelector, "Location/MKVExtract", self.ui.location_mkvextract))
        self.ui.button_mkvinfo.clicked.connect(partial(self.SoftwareSelector, "Location/MKVInfo", self.ui.location_mkvinfo))
        self.ui.button_mkvmerge.clicked.connect(partial(self.SoftwareSelector, "Location/MKVMerge", self.ui.location_mkvmerge))
        self.ui.button_mkvtoolnix.clicked.connect(partial(self.SoftwareSelector, "Location/MKVToolNix", self.ui.location_mkvtoolnix))
        self.ui.button_mkvalidator.clicked.connect(partial(self.SoftwareSelector, "Location/MKValidator", self.ui.location_mkvalidator))
        self.ui.button_qtesseract5.clicked.connect(partial(self.SoftwareSelector, "Location/Qtesseract5", self.ui.location_qtesseract5))

        self.ui.location_avconv.textChanged.connect(partial(self.SoftwareChanged, "Location/AvConv"))
        self.ui.location_bdsup2sub.textChanged.connect(partial(self.SoftwareChanged, "Location/BDSup2Sub"))
        self.ui.location_ffmpeg.textChanged.connect(partial(self.SoftwareChanged, "Location/FFMpeg"))
        self.ui.location_mkvextract.textChanged.connect(partial(self.SoftwareChanged, "Location/MKVExtract"))
        self.ui.location_mkclean.textChanged.connect(partial(self.SoftwareChanged, "Location/MKClean"))
        self.ui.location_mkvinfo.textChanged.connect(partial(self.SoftwareChanged, "Location/MKVInfo"))
        self.ui.location_mkvmerge.textChanged.connect(partial(self.SoftwareChanged, "Location/MKVMerge"))
        self.ui.location_mkvtoolnix.textChanged.connect(partial(self.SoftwareChanged, "Location/MKVToolNix"))
        self.ui.location_mkvalidator.textChanged.connect(partial(self.SoftwareChanged, "Location/MKValidator"))
        self.ui.location_qtesseract5.textChanged.connect(partial(self.SoftwareChanged, "Location/Qtesseract5"))

        ### Connexions du tableau listant les pistes du fichier mkv
        self.ui.mkv_tracks.itemChanged.connect(self.TrackModif) # Au changement du contenu d'un item
        self.ui.mkv_tracks.itemSelectionChanged.connect(self.TrackModif) # Au changement de sélection
        self.ui.mkv_tracks.horizontalHeader().sectionPressed.connect(self.TrackSelectAll) # Au clic sur le header horizontal

        ### Connexions des options sur les pistes du fichier mkv (au clic)
        self.ui.option_reencapsulate.toggled.connect(partial(self.OptionsValue, "Reencapsulate"))
        self.ui.option_subtitles.toggled.connect(partial(self.OptionsValue, "SubtitlesConvert"))
        self.ui.option_audio.toggled.connect(partial(self.OptionsValue, "AudioConvert"))
        self.ui.option_systray.toggled.connect(partial(self.OptionsValue, "SysTray"))
        self.ui.option_minimise_systray.toggled.connect(partial(self.OptionsValue, "SysTrayMinimise"))
        self.option_stereo.toggled.connect(partial(self.OptionsValue, "AudioStereo"))
        self.option_to_ac3.toggled.connect(partial(self.OptionsValue, "AudioToAc3"))
        self.option_subtitles_open.toggled.connect(partial(self.OptionsValue, "SubtitlesOpen"))
        self.option_ffmpeg.toggled.connect(partial(self.OptionsValue, "FFMpeg"))

        Sub2Srt[1].triggered.connect(partial(self.OptionsValue, "Sub2Srt", 1))
        Sub2Srt[2].triggered.connect(partial(self.OptionsValue, "Sub2Srt", 2))
        Sup2Sub[1].triggered.connect(partial(self.OptionsValue, "Sup2Sub", 1))
        Sup2Sub[2].triggered.connect(partial(self.OptionsValue, "Sup2Sub", 2))
        Sup2Sub[3].triggered.connect(partial(self.OptionsValue, "Sup2Sub", 3))

        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
            QualityList[nb].triggered.connect(partial(self.OptionsValue, "AudioQuality", nb))

        for nb in [2, 3, 4, 5]:
            PowerList[nb].triggered.connect(partial(self.OptionsValue, "AudioBoost", nb))

        ### Connexions en lien avec le system tray
        self.SysTrayIcon.activated.connect(self.SysTrayClick)

        ### Connexions des boutons du bas (au clic)
        self.ui.mkv_stop.clicked.connect(partial(self.WorkStop, "Stop"))
        self.ui.mkv_pause.clicked.connect(self.WorkPause)
        self.ui.mkv_execute.clicked.connect(self.CommandCreate)
        self.ui.soft_quit.__class__ = QuitButton # Utilisation de la classe QuitButton pour la prise en charge du clic droit

        ### Connexions du QProcess
        self.process.readyReadStandardOutput.connect(self.WorkReply) # Retours du travail
        self.process.finished.connect(self.WorkFinished) # Fin du travail

        ### Boutons de fermeture de l'application'
        self.SysTrayQuit.triggered.connect(self.CloseButton)
        self.ui.soft_quit_2.triggered.connect(self.CloseButton)
        self.ui.soft_quit.clicked.connect(self.CloseButton)
        self.ui.soft_quit.signalReboot.connect(self.RebootButton)


    #========================================================================
    def StyleChange(self, Value):
        """Fonction modifiant le style utilisé par Qt."""
        ### Enregistrement de la valeur
        Configs.setValue("QtStyle", Value)

        ### Grise le style actuellement utilisé
        for Style in QtStyleList.keys():
            if Value == Style :
                QtStyleList[Style].setEnabled(False)

            else:
                QtStyleList[Style].setEnabled(True)

        ### Applique le style graphique
        QApplication.setStyle(QStyleFactory.create(Value))



    #========================================================================
    def SoftwareFinding(self, Reset=False):
        """Fonction vérifiant les adresses des exécutables et les affichant dans la page des exécutables."""
        ### Si demande de réinitialisation
        if Reset:
            for Location in self.WidgetsLocation.keys():
                Configs.setValue(Location, "")

        ### Traitement de tous les exécutables
        for Location, Executable, Widget in (("Location/AvConv", "avconv", self.ui.location_avconv),
                                             ("Location/BDSup2Sub", "bdsup2sub", self.ui.location_bdsup2sub),
                                             ("Location/FFMpeg", "ffmpeg", self.ui.location_ffmpeg),
                                             ("Location/MKClean", "mkclean", self.ui.location_mkclean),
                                             ("Location/MKVExtract", "mkvextract", self.ui.location_mkvextract),
                                             ("Location/MKVInfo", "mkvinfo-gui", self.ui.location_mkvinfo),
                                             ("Location/MKVMerge", "mkvmerge", self.ui.location_mkvmerge),
                                             ("Location/MKVToolNix", "mkvtoolnix-gui", self.ui.location_mkvtoolnix),
                                             ("Location/MKValidator", "mkvalidator", self.ui.location_mkvalidator),
                                             ("Location/Qtesseract5", "qtesseract5", self.ui.location_qtesseract5)):

            ## Sauvegarde de la valeur initiale
            InitialValue = Configs.value(Location)

            ## Si la variable est vide, on recherche le logiciel
            if not Configs.value(Location):
                # Recherche le fichier dans le PATH
                if QStandardPaths.findExecutable(Executable):
                    Configs.setValue(Location, QStandardPaths.findExecutable(Executable))

                # Recherche le fichier à la base du logiciel
                elif QStandardPaths.findExecutable(Executable, [QFileInfo(Executable).absoluteFilePath()]):
                    Configs.setValue(Location, QStandardPaths.findExecutable(Executable, [QFileInfo(Executable).absoluteFilePath()]))

                # Cas spécifique à BDSup2Sub
                elif Location == "Location/BDSup2Sub":
                    if QStandardPaths.findExecutable("BDSup2Sub.jar"):
                        Configs.setValue("Location/BDSup2Sub", QStandardPaths.findExecutable("BDSup2Sub.jar"))

                    elif QStandardPaths.findExecutable("bdsup2sub.jar"):
                        Configs.setValue("Location/BDSup2Sub", QStandardPaths.findExecutable("bdsup2sub.jar"))

                    elif QStandardPaths.findExecutable("bdsup2sub", [QFileInfo("BDSup2Sub.jar").absoluteFilePath()]):
                        Configs.setValue("Location/BDSup2Sub", QStandardPaths.findExecutable("bdsup2sub", [QFileInfo("BDSup2Sub.jar").absoluteFilePath()]))

                    elif QStandardPaths.findExecutable("bdsup2sub", [QFileInfo("bdsup2sub.jar").absoluteFilePath()]):
                        Configs.setValue("Location/BDSup2Sub", QStandardPaths.findExecutable("bdsup2sub", [QFileInfo("bdsup2sub.jar").absoluteFilePath()]))

                # Cas spécifique à MKVToolNix
                elif Location == "Location/MKVToolNix":
                    if QStandardPaths.findExecutable("mmg"):
                        Configs.setValue("Location/MKVToolNix", QStandardPaths.findExecutable("mmg"))

                    elif QStandardPaths.findExecutable("mmg", [QFileInfo("mmg").absoluteFilePath()]):
                        Configs.setValue("Location/MKVToolNix", "{} --info".format(QStandardPaths.findExecutable("mmg", [QFileInfo("mmg").absoluteFilePath()])))

                    elif QStandardPaths.findExecutable("mkvtoolnix-gui"):
                        Configs.setValue("Location/MKVToolNix", QStandardPaths.findExecutable("mkvtoolnix-gui"))

                    elif QStandardPaths.findExecutable("mkvtoolnix-gui", [QFileInfo("mkvtoolnix-gui").absoluteFilePath()]):
                        Configs.setValue("Location/MKVToolNix", "{} --info".format(QStandardPaths.findExecutable("mkvtoolnix-gui", [QFileInfo("mkvtoolnix-gui").absoluteFilePath()])))

                # Cas spécifique à MKVInfo
                elif Location == "Location/MKVInfo":
                    if QStandardPaths.findExecutable("mkvtoolnix-gui"):
                        Configs.setValue("Location/MKVInfo", "{} --info".format(QStandardPaths.findExecutable("mkvtoolnix-gui")))

                    elif QStandardPaths.findExecutable("mkvtoolnix-gui", [QFileInfo("mkvtoolnix-gui").absoluteFilePath()]):
                        Configs.setValue("Location/MKVInfo", "{} --info".format(QStandardPaths.findExecutable("mkvtoolnix-gui", [QFileInfo("mkvtoolnix-gui").absoluteFilePath()])))

                    elif QStandardPaths.findExecutable("mkvinfo"):
                        Configs.setValue("Location/MKVInfo", "{} -g".format(QStandardPaths.findExecutable("mkvinfo")))

                    elif QStandardPaths.findExecutable("mkvinfo", [QFileInfo("mkvinfo").absoluteFilePath()]):
                        Configs.setValue("Location/MKVInfo", "{} --info".format(QStandardPaths.findExecutable("mkvinfo", [QFileInfo("mkvinfo").absoluteFilePath()])))


            ## Si la valeur n'a pas évoluée, au démarrage, le setText ne sera pas "fonctionnel", on l'appelle manuellement
            if InitialValue == Configs.value(Location):
                self.SoftwareChanged(Location, InitialValue, Widget)

            ## Envoie de l'adresse dans le line edit
            Widget.setText(Configs.value(Location))


    #========================================================================
    def SoftwareSelector(self, Location, Widget):
        """Fonction de sélection des exécutables."""
        ### Affichage de la fenêtre avec le bon dossier par défaut
        FileDialog = QFileDialog.getOpenFileName(self, self.Trad["LocationTitle"], MultiVar(Configs.value(Location), QDir.homePath()))

        ### En cas d'annulation, on arrête là
        if not FileDialog[0]:
            return

        ### Mise à jour du widget
        Widget.setText(FileDialog[0])


    #========================================================================
    def SoftIsExec(self, Name):
        """Mini fonction pour simplifier les tests d'executabilité (et du coup son existence) des commandes."""
        ### Si utilisation de | pour tester plusieurs commandes
        # not self.SoftIsExec("FFMpeg|AvConv") : Si on veut que tous les tests soient négatifs
        # self.SoftIsExec("BDSup2Sub|FFMpeg") : Si on veut au moins 1 résultat positif
        if "|" in Name:
            ## Boucles sur tous les noms
            for SubName in Name.split("|"):
                # Ajout de Location/
                SubName = "Location/" + SubName.replace("Location/", "")

                # Si le fichier est exécutable (et du coup existant)
                if QFileInfo(Configs.value(SubName).split(" -")[0]).isExecutable():
                    return True

            ## Si tous les tests ont échoués
            return False

        ### Mode simple
        else:
            ## Ajout de Location/
            Name = "Location/" + Name.replace("Location/", "")

            ## Renvoi de l'état de la commande
            Retour = QFileInfo(Configs.value(Name).split(" -")[0]).isExecutable()

            ## Cas spécifique à MKVExtract et MKVMerge
            if not Retour and Name in ("Location/MKVExtract", "Location/MKVMerge"):
                QMessageBox.critical(self, self.Trad["WorkTestTitle"].format(Name.replace("Location/", "")), self.Trad["WorkTestText"].format(Name.replace("Location/", "")))

                self.SetInfo(self.Trad["WorkTestTitle"].format(Name.replace("Location/", "")) + " : " + self.Trad["WorkTestText"].format(Name.replace("Location/", "")), "FF0000", True) # Erreur pendant le travail

                self.WorkStop("Error")

            ## Renvoi de la valeur
            return Retour


    #========================================================================
    def SoftwareChanged(self, Location, NewText, Widget = None):
        """Fonction vérifiant que l'adresse de l'exécutable est valide."""
        ### Mise à jour de la variable
        Configs.setValue(Location, NewText)

        ### Fait sauter les arguments afin de pouvoir tester uniquement l'exécutable
        NewText = NewText.split(" -")[0]

        ### Nom du widget appelant la fonction
        if not Widget:
            Widget = self.sender()

        ### Variable servant au (dé)grisement des options
        OptionActive = False

        ### Suppression des actions (icônes) du widget
        for Action in Widget.actions():
            Widget.removeAction(Action)

        ### Teste l'adresse et attribut une icône
        # Si l'adresse est vide, envoi d'une icône question dans le line edit
        if not NewText:
            Action = QAction(QIcon.fromTheme("emblem-question", QIcon(":/img/emblem-question.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationNo"])

        # Si l'adresse est introuvable, envoi d'une icône d'erreur dans le line edit
        elif not QFileInfo(NewText.split(" -")[0]).exists():
            Action = QAction(QIcon.fromTheme("emblem-error", QIcon(":/img/emblem-error.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationKO"])

        # Si l'adresse n'est pas exécutable, envoi d'une icône de point d'exclamation dans le line edit
        elif not QFileInfo(NewText.split(" -")[0]).isExecutable():
            Action = QAction(QIcon.fromTheme("emblem-important", QIcon(":/img/emblem-important.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationOKO"])

        # Sinon, icône OK
        else:
            Action = QAction(QIcon.fromTheme("emblem-succed", QIcon(":/img/emblem-succed.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationOK"])
            OptionActive = True


        ### Envoi de l'icône dans le line edit
        Widget.addAction(Action, QLineEdit.LeadingPosition)

        ### Récupération du widget de l'option
        # Avconv n'a pas de widget
        try:
            OptionWidget = self.WidgetsLocation[Location]

        except:
            OptionWidget = None


        ### Si un widget a été donné
        if OptionWidget:
            ## Fait disparaître si besoin l'option
            if Configs.value("HideOptions") and not OptionActive:
                OptionWidget.setVisible(False)

            ## Fait apparaître l'option
            else:
                OptionWidget.setVisible(True)

            ## Activation du widget si un fichier est chargé ne concernant pas Qtesseract et BDSup2Sub
            if TempValues.value("MKVLoaded") and Location not in ("Location/Qtesseract5", "Location/FFMpeg", "Location/BDSup2Sub"):
                if self.SoftIsExec(Location) and OptionActive:
                    OptionWidget.setEnabled(True)

                else:
                    OptionWidget.setEnabled(False)

            ## Pour Qtesseract / BDSup2Sub / FFMpeg
            if Location in ("Location/Qtesseract5", "Location/FFMpeg", "Location/BDSup2Sub"):
                self.SubtitlesSoftwareUpdate()


        ### Recherche ffmpeg et avconv qui font la même chose
        if Location in ("Location/FFMpeg", "Location/AvConv"):
            # Décoche le bouton de conversion audio
            self.ui.option_audio.setChecked(False)

            # Décoche les sous options
            self.option_stereo.setChecked(False)
            self.option_to_ac3.setChecked(False)

            for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
                QualityList[nb].setChecked(False)

            for nb in [2, 3, 4, 5]:
                PowerList[nb].setChecked(False)

            # S'il n'y a ni FFMpeg ni AvConv
            if not self.SoftIsExec("FFMpeg|AvConv"):
                # On désactive les options et le bouton de conversion audio
                TempValues.setValue("FFMpeg", False)
                self.option_ffmpeg.setEnabled(False)
                self.option_ffmpeg.setChecked(False)
                self.ui.option_audio.setEnabled(False)

                # Si besoin, on cache aussi le bouton de conversion audio
                if Configs.value("HideOptions"):
                    self.ui.option_audio.setVisible(False)

            else:
                # Affichage du bouton de conversion audio
                self.ui.option_audio.setVisible(True)

                # Activation du bouton de conversion audio s'il y a de l'audio coché
                for valeurs in MKVDicoSelect.values():
                    if valeurs[2] == "audio-x-generic":
                        self.ui.option_audio.setEnabled(True)

                # Si FFMPEG existe, c'est toujours lui qu'on utilise par défaut
                if self.SoftIsExec("FFMpeg"):
                    TempValues.setValue("FFMpeg", True)

                # Sinon utilisation de AvConv
                elif self.SoftIsExec("AvConv"):
                    TempValues.setValue("FFMpeg", False)

                # S'il y a FFMPEG et AvConv, activation de l'option
                if self.SoftIsExec("FFMpeg") and self.SoftIsExec("AvConv"):
                    self.option_ffmpeg.setEnabled(True)
                    self.option_ffmpeg.setChecked(True)

                # Sinon, on désactive l'option
                else:
                    self.option_ffmpeg.setChecked(False)
                    self.option_ffmpeg.setEnabled(False)


    #========================================================================
    def SubtitlesSoftwareUpdate(self):
        """Gestion spécifique des actions de conversion des sous-titres."""
        # Bouton d'activation des conversions de sous titres
        option_subtitlesEnabled = False
        option_subtitlesChecked = False

        # Décoche et désactive les actions de Qtesseract
        Qtesseract5ConvertChecked = False
        Qtesseract5ConvertEnabled = False
        Qtesseract5OpenChecked = False
        Qtesseract5OpenEnabled = False

        # Décoche et désactive les actions de BDSup2Sub
        BDSup2SubConvertChecked = False
        BDSup2SubConvertEnabled = False
        BDSup2SubOpenEnabled = False
        BDSup2SubOpenChecked = False

        # Décoche et désactive les actions de FFMpeg
        FFMpegConvertChecked = False
        FFMpegConvertEnabled = False

        # Dans le cas où il faut cacher les actions indisponibles
        if Configs.value("HideOptions"):
            Qtesseract5ConvertVisible = False
            Qtesseract5OpenVisible = False
            BDSup2SubOpenVisible = False
            BDSup2SubConvertVisible = False
            FFMpegConvertVisible = False

        else:
            Qtesseract5ConvertVisible = True
            Qtesseract5OpenVisible = True
            BDSup2SubOpenVisible = True
            BDSup2SubConvertVisible = True
            FFMpegConvertVisible = True


        # Si BDSup2Sub/FFMpeg et Qtesseract sont fonctionnels
        if self.SoftIsExec("BDSup2Sub|FFMpeg") and self.SoftIsExec("Qtesseract5"):
            if MKVDicoSelect:
                # Bouton de conversion des sous-titres
                option_subtitlesEnabled = True

            # Affichage des actions
            if self.SoftIsExec("BDSup2Sub"):
                BDSup2SubOpenVisible = True
                BDSup2SubConvertVisible = True

            if self.SoftIsExec("FFMpeg"):
                FFMpegConvertVisible = True

            Qtesseract5ConvertVisible = True
            Qtesseract5OpenVisible = True

            # Recherche une piste cochée de type sub/sup/pgs
            for valeurs in MKVDicoSelect.values():
                if valeurs[-1] in ("sup", "pgs", "sub"):
                    # Bouton de conversion des sous-titres
                    option_subtitlesChecked = self.ui.option_subtitles.isChecked()

                    if valeurs[-1] in ("sup", "pgs"):
                        # Activation de BDSup2Sub
                        if self.SoftIsExec("BDSup2Sub"):
                            BDSup2SubConvertEnabled = True
                            BDSup2SubOpenEnabled = True

                            # Conserve l'état des coches
                            BDSup2SubConvertChecked = Sup2Sub[2].isChecked()
                            BDSup2SubOpenChecked = Sup2Sub[3].isChecked()

                        # Activation de FFMpeg
                        if self.SoftIsExec("FFMpeg"):
                            FFMpegConvertEnabled = True

                            # Conserve l'état des coches
                            FFMpegConvertChecked = Sup2Sub[1].isChecked()


                        # Si BDSup2Sub ou FFMpeg sont actuellement utilisés
                        if BDSup2SubConvertChecked or FFMpegConvertChecked:
                            # Activation de Qtesseract
                            Qtesseract5ConvertEnabled = True
                            Qtesseract5OpenEnabled = True

                            # Conserve l'état des coches
                            Qtesseract5ConvertChecked = Sub2Srt[1].isChecked()
                            Qtesseract5OpenChecked = Sub2Srt[2].isChecked()

                            # On a déjà tout activé, on peut arrêter
                            break

                    else:
                        # Activation de Qtesseract
                        Qtesseract5ConvertEnabled = True
                        Qtesseract5OpenEnabled = True

                        # Conserve l'état des coches
                        Qtesseract5ConvertChecked = Sub2Srt[1].isChecked()
                        BDSup2SubOpenChecked = Sub2Srt[2].isChecked()

        # Si Qtesseract est fonctionnel
        elif self.SoftIsExec("Qtesseract5"):
            if MKVDicoSelect:
                # Bouton de conversion des sous-titres
                option_subtitlesEnabled = True

            # Affichage des actions
            Qtesseract5ConvertVisible = True
            Qtesseract5OpenVisible = True

            # S'il y a des pistes
            if MKVDicoSelect:
                # Recherche une piste cochée de type sub
                for valeurs in MKVDicoSelect.values():
                    if valeurs[-1] == "sub":
                        # Bouton de conversion des sous-titres
                        option_subtitlesChecked = self.ui.option_subtitles.isChecked()

                        # Activation de Qtesseract
                        Qtesseract5ConvertEnabled = True
                        Qtesseract5OpenEnabled = True

                        # Conserve l'état des coches
                        Qtesseract5ConvertChecked = Sub2Srt[1].isChecked()
                        BDSup2SubOpenChecked = Sub2Srt[2].isChecked()

                        break

        # Si BDSup2Sub/FFMpeg sont fonctionnels
        elif self.SoftIsExec("BDSup2Sub|FFMpeg"):
            if MKVDicoSelect:
                # Bouton de conversion des sous-titres
                option_subtitlesEnabled = True

            # Affichage des actions
            if self.SoftIsExec("BDSup2Sub"):
                BDSup2SubOpenVisible = True
                BDSup2SubConvertVisible = True

            if self.SoftIsExec("FFMpeg"):
                FFMpegConvertVisible = True

            # S'il y a des pistes
            if MKVDicoSelect:
                # Recherche une piste cochée de type sup ou pgs
                for valeurs in MKVDicoSelect.values():
                    if valeurs[-1] in ("sup", "pgs"):
                        # Bouton de conversion des sous-titres
                        option_subtitlesChecked = self.ui.option_subtitles.isChecked()

                        # Activation de BDSup2Sub
                        if self.SoftIsExec("BDSup2Sub"):
                            BDSup2SubConvertEnabled = True
                            BDSup2SubOpenEnabled = True

                            # Conserve l'état des coches
                            BDSup2SubConvertChecked = Sup2Sub[2].isChecked()
                            BDSup2SubOpenChecked = Sup2Sub[3].isChecked()

                        # Activation de FFMpeg
                        if self.SoftIsExec("FFMpeg"):
                            FFMpegConvertEnabled = True

                            # Conserve l'état des coches
                            FFMpegConvertChecked = Sup2Sub[1].isChecked()

                        break


        # Mise à jour du bouton de conversion des sous titres
        self.ui.option_subtitles.setEnabled(option_subtitlesEnabled)
        self.ui.option_subtitles.setChecked(option_subtitlesChecked)

        # Mise à jour des info-bulles
        self.SubtitlesTranslation(False)

        # Mise à jour des actions de Qtesseract
        Sub2Srt[1].setChecked(Qtesseract5ConvertChecked)
        Sub2Srt[1].setEnabled(Qtesseract5ConvertEnabled)
        Sub2Srt[1].setVisible(Qtesseract5ConvertVisible)
        Sub2Srt[2].setChecked(Qtesseract5OpenChecked)
        Sub2Srt[2].setEnabled(Qtesseract5OpenEnabled)
        Sub2Srt[2].setVisible(Qtesseract5OpenVisible)

        # Mise à jour des actions de BDSup2Sub
        Sup2Sub[2].setChecked(BDSup2SubConvertChecked)
        Sup2Sub[2].setEnabled(BDSup2SubConvertEnabled)
        Sup2Sub[2].setVisible(BDSup2SubConvertVisible)
        Sup2Sub[3].setChecked(BDSup2SubOpenChecked)
        Sup2Sub[3].setEnabled(BDSup2SubOpenEnabled)
        Sup2Sub[3].setVisible(BDSup2SubOpenVisible)

        # Mise à jour des actions de FFMpeg
        Sup2Sub[1].setChecked(FFMpegConvertChecked)
        Sup2Sub[1].setEnabled(FFMpegConvertEnabled)
        Sup2Sub[1].setVisible(FFMpegConvertVisible)


    #========================================================================
    def OptionsValue(self, Option, Value):
        """Fonction de mise à jour des options."""
        if Option in ("AudioBoost", "AudioQuality", "Sup2Sub", "Sub2Srt"):
            if Configs.value(Option) == Value:
                if Option == "AudioBoost":
                    PowerList[Value].setChecked(False)

                elif Option == "AudioQuality":
                    QualityList[Value].setChecked(False)

                elif Option == "Sup2Sub":
                    Sup2Sub[Value].setChecked(False)

                    # Décoche si besoin l'utilisation de Qtesseract
                    if self.SoftIsExec("Qtesseract5"):
                        State = False

                        # Boucle sur la liste des pistes cochées à la recherche de fichier sub
                        if MKVDicoSelect:
                            for valeurs in MKVDicoSelect.values():
                                if valeurs[-1] == "sub":
                                    # Ne désactive pas Qtesseract s'il y a un sub
                                    State = True
                                    break

                        if not State:
                            Sub2Srt[1].setEnabled(False)
                            Sub2Srt[1].setChecked(False)
                            Sub2Srt[2].setEnabled(False)
                            Sub2Srt[2].setChecked(False)

                elif Option == "Sub2Srt":
                    Sub2Srt[Value].setChecked(False)

                Configs.setValue(Option, 0)

                return


        ### Mise à jour de la variable et envoie de l'info
        Configs.setValue(Option, Value)

        if Configs.value("DebugMode"):
            self.SetInfo(self.Trad["OptionUpdate"].format(Option, Value), newline=True)

        ### Dans le cas de certaines options, il faut faire plus
        # Si l'option OutputSameFolder est activée et qu'un fichier d'entrée est déjà connu
        if Option == "OutputSameFolder" and Value and Configs.contains("InputFile"):
            # Recherche de l'option OutputSameFolder
            x = self.ui.configuration_table.findItems("OutputSameFolder", Qt.MatchExactly)[0].row()

            ## Il faut bloquer le signal pour éviter un cercle vicieux et modifier la valeur visuelle en directe
            self.ui.configuration_table.blockSignals(True)
            self.ui.configuration_table.item(x, 1).setText(Configs.value("InputFolder"))

            # Envoie de la nouvelle variable à la fonction de gestion des dossiers qui mettra à jour la variable
            self.OutputFolder(Configs.value("InputFolder"))

            # Déblocage des signaux
            self.ui.configuration_table.blockSignals(False)

        # En cas de modification du dossier de sorti
        elif Option == "OutputFolder":
            Configs.setValue(Option, QFileInfo(Value))

            # Recherche de l'option OutputFolder
            x = self.ui.configuration_table.findItems("OutputSameFolder", Qt.MatchExactly)[0].row()

            # Il faut bloquer le signal pour éviter un cercle vicieux et modifier la valeur visuelle en directe
            self.ui.configuration_table.blockSignals(True)
            self.ui.configuration_table.item(x, 1).setText("False")

            # Mise à jour de la variable
            Configs.setValue("OutputSameFolder", False)

            # Envoie de la nouvelle variable à la fonction de gestion des dossiers
            self.OutputFolder(Configs.value("OutputFolder"))

            # Déblocage des signaux
            self.ui.configuration_table.blockSignals(False)

        # Pour cacher ou afficher la box de retour d'informations
        elif Option == "Feedback":
            if Value:
                self.ui.feedback_widget.show()

            else:
                self.ui.feedback_widget.hide()

        # Pour bloquer ou débloquer la box de retour d'informations
        elif Option == "FeedbackBlock":
            if Value:
                self.ui.feedback_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)

            else:
                self.ui.feedback_widget.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        # Pour cacher ou afficher l'icône du systray
        elif Option == "SysTray":
            ## Affichage de l'icône
            if Value:
                self.SysTrayIcon.show()

            ## Cache l'icône après avoir affiché la fenêtre principale
            else:
                self.show()
                self.activateWindow()
                self.SysTrayIcon.hide()

                # Décoche SysTrayMinimise
                if self.ui.option_minimise_systray.isChecked():
                    self.ui.option_minimise_systray.setChecked(False)

        # Pour cocher l'option systray
        elif Option == "SysTrayMinimise" and Value:
            if not self.ui.option_systray.isChecked():
                self.ui.option_systray.setChecked(True)

        # Activation des boutons Qtesseract si conversion Sup => Sub
        if Option == "Sup2Sub" and self.SoftIsExec("Qtesseract5") and Value:
            # Si la conversion SUP => SUB est coché, on active les actions Qtesseract pour les fichiers SUP/PGS
            if Value:
                Sub2Srt[1].setEnabled(True)
                Sub2Srt[2].setEnabled(True)

            # Si la conversion SUP => SUB est décochée
            else:
                State = False

                # Boucle sur la liste des pistes cochées à la recherche de fichier sub
                if MKVDicoSelect:
                    for valeurs in MKVDicoSelect.values():
                        if valeurs[-1] == "sub":
                            # Ne désactive pas Qtesseract s'il y a un sub
                            State = True
                            break

                Sub2Srt[1].setEnabled(State)
                Sub2Srt[1].setChecked(Sub2Srt[1].isChecked())
                Sub2Srt[2].setEnabled(State)
                Sub2Srt[2].setChecked(Sub2Srt[2].isChecked())

        ## Pour cacher ou afficher les commandes indisponibles
        elif Option == "HideOptions":
            for Location, Widget in self.WidgetsLocation.items():
                # S'il faut les afficher
                if not Value:
                    Widget.setVisible(True)

                # S'il faut les cacher
                else:
                    if not self.SoftIsExec(Location):
                        Widget.setVisible(False)


    #========================================================================
    def SubtitlesTranslation(self, All=False):
        """Fonction de traduction des actions de conversion des sous-titres."""
        ### Retraduction complète
        if All:
            Sub2Srt[1].setText(self.Trad["QtesseractConvertText"])
            Sub2Srt[1].setStatusTip(self.Trad["QtesseractConvertStatusTip"])
            Sup2Sub[1].setText(self.Trad["FFMpegConvertText"])
            Sup2Sub[1].setStatusTip(self.Trad["FFMpegConvertStatusTip"])
            Sup2Sub[2].setText(self.Trad["BDSup2SubConvertText"])
            Sup2Sub[2].setStatusTip(self.Trad["BDSup2SubConvertStatusTip"])
            Sub2Srt[2].setText(self.Trad["QtesseractOpenText"])
            Sub2Srt[2].setStatusTip(self.Trad["QtesseractOpenStatusTip"])
            Sup2Sub[3].setText(self.Trad["BDSup2SubOpenText"])
            Sup2Sub[3].setStatusTip(self.Trad["BDSup2SubOpenStatusTip"])

        ### Gestion des bonnes info bulles
        if not QFileInfo(Configs.value("Location/Qtesseract5").split(" -")[0]).exists():
            Sub2Srt[1].setToolTip(self.Trad["QtesseractConvertToolTip1"])
            Sub2Srt[2].setToolTip(self.Trad["QtesseractOpenToolTip1"])

        elif not self.SoftIsExec("Qtesseract5"):
            Sub2Srt[1].setToolTip(self.Trad["QtesseractConvertToolTip2"])
            Sub2Srt[2].setToolTip(self.Trad["QtesseractOpenToolTip2"])

        else:
            Sub2Srt[1].setToolTip(self.Trad["QtesseractConvertToolTip3"])
            Sub2Srt[2].setToolTip(self.Trad["QtesseractOpenToolTip3"])


        if not QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).exists():
            Sup2Sub[1].setToolTip(self.Trad["FFMpegConvertToolTip1"])

        elif not self.SoftIsExec("FFMpeg"):
            Sup2Sub[1].setToolTip(self.Trad["FFMpegConvertToolTip2"])

        else:
            Sup2Sub[1].setToolTip(self.Trad["FFMpegConvertToolTip3"])


        if not QFileInfo(Configs.value("Location/BDSup2Sub").split(" -")[0]).exists():
            Sup2Sub[2].setToolTip(self.Trad["BDSup2SubConvertToolTip1"])
            Sup2Sub[3].setToolTip(self.Trad["BDSup2SubOpenToolTip1"])

        elif not self.SoftIsExec("BDSup2Sub"):
            Sup2Sub[2].setToolTip(self.Trad["BDSup2SubConvertToolTip2"])
            Sup2Sub[3].setToolTip(self.Trad["BDSup2SubOpenToolTip2"])

        else:
            Sup2Sub[2].setToolTip(self.Trad["BDSup2SubConvertToolTip3"])
            Sup2Sub[3].setToolTip(self.Trad["BDSup2SubOpenToolTip3"])



    #========================================================================
    def OptionLanguage(self, value):
        """Fonction modifiant en temps réel la traduction."""
        ### Mise à jour de la variable de la langue
        Configs.setValue("Language", value)

        ### Chargement du fichier QM de traduction (anglais utile pour les textes singulier/pluriel)
        appTranslator = QTranslator() # Création d'un QTranslator

        ### Dans le cas d'une langue autre que anglais et qui existe
        if Configs.value("Language") in ("fr_FR", "cs_CZ", "es_ES", "tr_TR"):
            find = appTranslator.load("Languages/MKVExtractorQt5_{}".format(Configs.value("Language")), AppFolder)

            # Si le fichier n'a pas été trouvé, affiche une erreur et utilise la version anglaise
            if not find:
                Texts = {
                    "fr_FR": ["Erreur de traduction", "Aucun fichier de traduction <b>française</b> trouvé.<br/>Utilisation de la langue <b>anglaise</b>."],
                    "cs_CZ": ["Chyba překladu", "No translation file <b>Czech</b> found. Use <b>English</b> language. Soubor s překladem do <b>češtiny</b> nenalezen. Použít <b>anglický</b> jazyk."],
                    "es_ES": ["Error de traducción", "No se han encontrado archivos de traducción al <b>español</b>.<br>El idioma <b>inglés</b> utilizado."],
                    "tr_TR": ["Çeviri hatası", "<b>Türkçe</b> çeviri dosyası bulunamadı.<br><b>İngilizce dilini</b> kullanma."]
                    }

                QMessageBox(QMessageBox.Critical, Texts[Configs.value("Language")][0], Texts[Configs.value("Language")][1], QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()
                self.ui.lang_en.setChecked(True)
                Configs.setValue("Language", "en_US")

            # Sinon, chargement de la traduction
            else:
                app.installTranslator(appTranslator)


        ### Mise à jour du fichier langage de Qt
        translator_qt = QTranslator() # Création d'un QTranslator
        if translator_qt.load("qt_" + Configs.value("Language"), QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator_qt)


        ### Mise à jour du dictionnaire des textes
        # 008000 : vert                 0000c0 : bleu                           800080 : violet
        effet = """<span style=" color:#000000;">@=====@</span>"""
        self.Trad = {"AboutTitle": QCoreApplication.translate("About", "About MKV Extractor Gui"),
                     "AboutText": QCoreApplication.translate("About", """<html><head/><body><p align="center"><span style=" font-size:12pt; font-weight:600;">MKV Extractor Qt v{}</span></p><p><span style=" font-size:10pt;">GUI to extract/edit/remux the tracks of a matroska (MKV) file.</span></p><p><span style=" font-size:10pt;">This program follows several others that were coded in Bash and it codec in python3 + QT5.</span></p><p><span style=" font-size:8pt;">This software is licensed under </span><span style=" font-size:8pt; font-weight:600;"><a href="{}">GNU GPL v3</a></span><span style=" font-size:8pt;">.</span></p><p>Software's page on <a href="https://github.com/Hizoka76/MKV-Extractor-Qt5"><span style=" text-decoration: underline; color:#0057ae;">github</span></a>.</p><p>ppa's page on <a href="https://launchpad.net/~hizo/+archive/ubuntu/mkv-extractor-gui"><span style=" text-decoration: underline; color:#0057ae;">launchpad</span></a>.</p><p align="right">Created by <span style=" font-weight:600;">Belleguic Terence</span> (Hizoka), November 2013</p></body></html>"""),

                     "TheyTalkAboutTitle": QCoreApplication.translate("TheyTalkAbout", "They talk about MKV Extractor Gui"),
                     "TheyTalkAboutText": QCoreApplication.translate("TheyTalkAbout", """<html><head/><body><p><a href="http://sysads.co.uk/2014/09/install-mkv-extractor-qt-5-1-4-ubuntu-14-04/"><span style=" text-decoration: underline; color:#0057ae;">sysads.co.uk</span></a> (English)</p><p><a href="http://www.softpedia.com/reviews/linux/mkv-extractor-qt-review-496919.shtml"><span style=" text-decoration: underline; color:#0057ae;">softpedia.com</span></a> (English)</p><p><a href="http://linux.softpedia.com/get/Multimedia/Video/MKV-Extractor-Qt-103555.shtml"><span style=" text-decoration: underline; color:#0057ae;">linux.softpedia.com</span></a> (English)</p><p><a href="http://zenway.ru/page/mkv-extractor-qt"><span style=" text-decoration: underline; color:#0057ae;">zenway.ru</span></a> (Russian)</p><p><a href="http://linuxg.net/how-to-install-mkv-extractor-qt-5-1-4-on-ubuntu-14-04-linux-mint-17-elementary-os-0-3-deepin-2014-and-other-ubuntu-14-04-derivatives/"><span style=" text-decoration: underline; color:#2980b9;">linuxg.net</span></a> (English)</p><p><a href="http://la-vache-libre.org/mkv-extractor-gui-virer-les-sous-titres-inutiles-de-vos-fichiers-mkv-et-plus-encore/"><span style=" text-decoration: underline; color:#2980b9;">la-vache-libre.org</span></a> (French)</p><p><a href="http://passionexubuntu.altervista.org/index.php/it/kubuntu/1152-mkv-extractor-qt-vs-5-1-3-kde.html"><span style=" text-decoration: underline; color:#2980b9;">passionexubuntu.altervista.org</span></a> (Italian)</p><p><a href="https://github.com/darealshinji/mkv-extractor-qt5"><span style=" text-decoration: underline; color:#2980b9;">an unofficial github </span></a>(English)</p><p><a href="https://gamblisfx.com/mkv-extractor-qt-5-2-1-extract-audio-and-video-from-mkv-files/"><span style=" text-decoration: underline; color:#2980b9;">gamblisfx.com</span></a><a href="https://github.com/darealshinji/mkv-extractor-qt5"><span style=" text-decoration: underline; color:#2980b9;"/></a>(English)</p><p><a href="https://aur.archlinux.org/packages/mkv-extractor-qt/"><span style=" text-decoration: underline; color:#2980b9;">An unofficial aur package</span></a></p><p><br/></p><p><br/></p><p><br/></p></body></html>"""),

                     "SysTrayQuit": QCoreApplication.translate("SysTray", "Quit"),
                     "SysTrayFinishTitle": QCoreApplication.translate("SysTray", "The command(s) have finished"),
                     "SysTrayFinishText": QCoreApplication.translate("SysTray", "The <b>{}</b> command have finished its work."),
                     "SysTrayTotalFinishText": QCoreApplication.translate("SysTray", "All commands have finished their work."),

                     "WhatsUpTitle": QCoreApplication.translate("WhatsUp", "MKV Extractor Qt5's changelog"),

                     "QTextEditStatusTip": QCoreApplication.translate("Main", "Use the right click for view options."),

                     "LocationOK": QCoreApplication.translate("Main", "This location is valid."),
                     "LocationKO": QCoreApplication.translate("Main", "This location is not valid."),
                     "LocationNo": QCoreApplication.translate("Main", "No location for this command."),
                     "LocationOKO": QCoreApplication.translate("Main", "This location is valid but not executable."),
                     "LocationTitle": QCoreApplication.translate("Main", "Please select the executable file"),

                     "AllFiles": QCoreApplication.translate("Main", "All compatible Files"),
                     "MatroskaFiles": QCoreApplication.translate("Main", "Matroska Files"),
                     "OtherFiles": QCoreApplication.translate("Main", "Other files that need to be converted to mkv"),

                     "Convert0": QCoreApplication.translate("Main", "Do not ask again"),
                     "Convert1": QCoreApplication.translate("Main", "File needs to be converted"),
                     "Convert2": QCoreApplication.translate("Main", "This file is not supported by MKVExtract.\nDo you want convert this file in mkv ?"),
                     "Convert3": QCoreApplication.translate("Main", "MKVMerge Warning"),
                     "Convert4": QCoreApplication.translate("Main", "A warning has occurred during the convertion of the file, read the feedback informations."),
                     "Convert5": QCoreApplication.translate("Main", "Do not warn me"),
                     "Convert6": QCoreApplication.translate("Main", "Choose the out folder of the new mkv file"),

                     "FileExistsTitle": QCoreApplication.translate("Main", "Already existing file"),
                     "FileExistsText": QCoreApplication.translate("Main", "The <b>{}</b> is already existing, overwrite it?"),

                     "ErrorLastFileTitle": QCoreApplication.translate("Errors", "The last file doesn't exist"),
                     "ErrorLastFileText": QCoreApplication.translate("Errors", "You have checked the option who reload the last file to the launch of MKV Extractor Qt, but this last file doesn't exist anymore."),
                     "ErrorArgTitle": QCoreApplication.translate("Errors", "Wrong arguments"),
                     "ErrorArgExist": QCoreApplication.translate("Errors", "The <b>{}</b> file given as argument does not exist."),
                     "ErrorArgNb": QCoreApplication.translate("Errors", "<b>Too many arguments given:</b><br/> - {} "),
                     "ErrorConfigTitle": QCoreApplication.translate("Errors", "Wrong value"),
                     "ErrorConfigText": QCoreApplication.translate("Errors", "Wrong value for the <b>{}</b> option, MKV Extractor Qt will use the default value."),
                     "ErrorConfigPath": QCoreApplication.translate("Errors", "Wrong path for the <b>{}</b> option, MKV Extractor Qt will use the default path."),
                     "ErrorQuoteTitle": QCoreApplication.translate("Errors", "No way to open this file"),
                     "ErrorQuoteText": QCoreApplication.translate("Errors", "The file to open contains quotes (\") in its name. It's impossible to open a file with this carac. Please rename it."),
                     "ErrorSizeTitle": QCoreApplication.translate("Errors", "Space available"),
                     "ErrorSize": QCoreApplication.translate("Errors", "Not enough space available in the <b>{}</b> folder.<br/>It is advisable to have at least twice the size of free space on the disk file.<br>Free disk space: <b>{}</b>.<br>File size: <b>{}</b>."),
                     "ErrorSizeAttachement": QCoreApplication.translate("Errors", "Not enough space available in <b>{}</b> folder.<br/>Free space in the disk: <b>{}</b><br/>File size: <b>{}</b>."),
                     "ErrorSizeButton1": QCoreApplication.translate("Errors", "Change the directory"),
                     "ErrorSizeButton2": QCoreApplication.translate("Errors", "I don't care"),
                     "ErrorSizeButton3": QCoreApplication.translate("Errors", "I want stop this"),

                     "WaitWinTitle": QCoreApplication.translate("WaitWindow", "Waiting for rework before re-encapsulation"),
                     "WaitWinText": QCoreApplication.translate("WaitWindow", "The subtitle files are normally open.\nYou can make any changes you want to them.\nWhen finished, click on Continue.\n\nTo cancel the work and delete the created files, click on Stop."),
                     "WaitWinButton1": QCoreApplication.translate("WaitWindow", "Continue"),
                     "WaitWinButton2": QCoreApplication.translate("WaitWindow", "Stop"),

                     "HelpTitle": QCoreApplication.translate("Help", "Help me!"),
                     "HelpText": QCoreApplication.translate("Help", """<html><head/><body><p align="center"><span style=" font-weight:600;">Are you lost? Do you need help? </span></p><p><span style=" font-weight:600;">Normally all necessary information is present: </span></p><p>- Read the informations in the status bar when moving the mouse on widgets </p><p>- Read the informations in some tooltips, wait 2-3 secondes on actions or buttons.</p><p><span style=" font-weight:600;">Though, if you need more information: </span></p><p>- Software's page on <a href="https://github.com/Hizoka76/MKV-Extractor-Qt5"><span style=" text-decoration: underline; color:#0057ae;">github</span></a>.</p><p> - ppa's page on <a href="https://launchpad.net/~hizo/+archive/ubuntu/mkv-extractor-gui"><span style=" text-decoration: underline; color:#0057ae;">launchpad</span></a>.</p><p>- Forum Ubuntu-fr.org: <a href="https://forum.ubuntu-fr.org/viewtopic.php?id=1508741"><span style=" text-decoration: underline; color:#0057ae;">topic</span></a></p><p>- My email address: <a href="mailto:hizo@free.fr"><span style=" text-decoration: underline; color:#0057ae;">hizo@free.fr </span></a></p><p><span style=" font-weight:600;">Thank you for your interest in this program.</span></p></body></html>"""),

                     "MKVMergeErrors": QCoreApplication.translate("MKVMerge", "MKVMerge returns errors during the read of the MKV file."),
                     "MKVMergeWarning":QCoreApplication.translate("MKVMerge", "MKVMerge returns warning during the read of the MKV file."),

                     "AlreadyExistsTest": QCoreApplication.translate("Main", "Skip the existing file test."),
                     "AudioQuality": QCoreApplication.translate("Main", "Quality of the ac3 file converted."),
                     "AudioBoost": QCoreApplication.translate("Main", "Power of the ac3 file converted."),
                     "CheckSizeCheckbox": QCoreApplication.translate("Main", "Skip the free space disk test."),
                     "DelTempFiles": QCoreApplication.translate("Main", "Delete temporary files."),
                     "DebugMode": QCoreApplication.translate("Main", "View more informations in feedback box."),
                     "ConfirmErrorLastFile": QCoreApplication.translate("Main", "Remove the error message if the last file doesn't exist."),
                     "Feedback": QCoreApplication.translate("Main", "Show or hide the information feedback box."),
                     "FeedbackBlock": QCoreApplication.translate("Main", "Anchor or loose information feedback box."),
                     "FolderParentTemp": QCoreApplication.translate("Main", "The folder to use for extract temporaly the attachements file to view them."),
                     "FFMpeg": QCoreApplication.translate("Main", "Use FFMpeg for the conversion."),
                     "LastFile": QCoreApplication.translate("Main", "Keep in memory the last file opened for open it at the next launch of MKV Extractor Qt."),
                     "HideOptions": QCoreApplication.translate("Main", "Hide the disabled options."),
                     "MMGorMEQ": QCoreApplication.translate("Main", "Software to use for just encapsulate."),
                     "MMGorMEQCheckbox": QCoreApplication.translate("Main", "Skip the proposal to software to use."),
                     "ConfirmConvert": QCoreApplication.translate("Main", "Skip the confirmation of the conversion."),
                     "ConfirmWarning": QCoreApplication.translate("Main", "Hide the information of the conversion warning."),
                     "InputFolder": QCoreApplication.translate("Main", "Folder of the MKV files."),
                     "OutputFolder": QCoreApplication.translate("Main", "Output folder for the new MKV files."),
                     "Language": QCoreApplication.translate("Main", "Software language to use."),
                     "RecentInfos": QCoreApplication.translate("Main", "Remove the Qt file who keeps the list of the recent files for the window selection."),
                     "OutputSameFolder": QCoreApplication.translate("Main", "Use the same input and output folder."),
                     "RemuxRename": QCoreApplication.translate("Main", "Automatically rename the output file name in MEG_FileName."),
                     "AudioStereo": QCoreApplication.translate("Main", "Switch to stereo during conversion."),
                     "SubtitlesOpen": QCoreApplication.translate("Main", "Opening subtitles before encapsulation."),
                     "SysTray": QCoreApplication.translate("Main", "Display or hide the system tray icon."),
                     "SysTrayMinimise": QCoreApplication.translate("Main", "Minimize the window when it closed with the X and when the systray is enabled."),
                     "WindowAspect": QCoreApplication.translate("Main", "Keep in memory the aspect and the position of the window for the next opened."),
                     "QtStyle": QCoreApplication.translate("Main", "Qt decoration."),

                     "OptionsDTStoAC31": QCoreApplication.translate("Options", "Convert in AC3"),
                     "OptionsDTStoAC32": QCoreApplication.translate("Options", "Convert audio tracks automatically to AC3."),
                     "OptionsFFMpeg": QCoreApplication.translate("Options", "Use FFMpeg for the conversion."),
                     "OptionsFFMpegStatusTip": QCoreApplication.translate("Options", "If FFMpeg and AvConv are installed, use FFMpeg."),
                     "OptionsPowerList": QCoreApplication.translate("Options", "Increase the sound power"),
                     "OptionsPowerX": QCoreApplication.translate("Options", "Multiplying audio power by {}. A click on item checked uncheck all."),
                     "OptionsPowerY": QCoreApplication.translate("Options", "Power x {}"),
                     "OptionsQuality": QCoreApplication.translate("Options", "List of available flow rates of conversion"),
                     "OptionsQualityX": QCoreApplication.translate("Options", "Convert the audio quality in {} kbits/s. A click on item checked uncheck all."),
                     "OptionsQualityY": QCoreApplication.translate("Options", "{} kbits/s"),
                     "OptionsStereo1": QCoreApplication.translate("Options", "Switch to stereo during conversion"),
                     "OptionsStereo2": QCoreApplication.translate("Options", "The audio will not use the same number of channels, the audio will be stereo (2 channels)."),
                     "OptionsSub1": QCoreApplication.translate("Options", "Opening subtitles before encapsulation"),
                     "OptionsSub2": QCoreApplication.translate("Options", "Auto opening of subtitle srt files for correction. The software will be paused."),
                     "OptionUpdate": QCoreApplication.translate("Options", 'New value for <span style=" color:#0000c0;">{}</span> option: <span style=" color:#0000c0;">{}</span>'),
                     "OptionsStyles": QCoreApplication.translate("Options", "Use the {} style."),

                     "MKVInfoText": QCoreApplication.translate("Actions", "&View MKV information"),
                     "MKVInfoToolTip": QCoreApplication.translate("Actions", "<html><head/><body><p><span style=\" font-weight:600;\">Why I can\'t use it?</span><br/>1) mkvtoolnix-gui needs to be install.<br/>2) Open a mkv file before execute command.</p></body></html>"),
                     "MKVInfoStatusTip": QCoreApplication.translate("Actions", "Display information about the MKV file with mkvinfo."),

                     "MKVMergeText": QCoreApplication.translate("Actions", "&Edit MKV file"),
                     "MKVMergeToolTip": QCoreApplication.translate("Actions", "<html><head/><body><p><span style=\" font-weight:600;\">Why I can\'t use it?</span><br/>1) mkvtoolnix-gui needs to be install.<br/>2) Open a mkv file before execute command.</p></body></html>"),
                     "MKVMergeStatusTip": QCoreApplication.translate("Actions", "Open the MKV file with mkvmerge GUI for more modifications."),

                     "MKValidatorText": QCoreApplication.translate("Actions", "&Check MKV file"),
                     "MKValidatorToolTip": QCoreApplication.translate("Actions", "<html><head/><body><p><span style=\" font-weight:600;\">Why I can\'t use it?</span><br/>1) mkvalidator needs to be install.<br/>2) Open a mkv file before execute command.</p></body></html>"),
                     "MKValidatorStatusTip": QCoreApplication.translate("Actions", "Verify Matroska files for specification conformance with MKValidator."),

                     "MKCleanText": QCoreApplication.translate("Actions", "&Optimize MKV file"),
                     "MKCleanToolTip": QCoreApplication.translate("Actions", "<html><head/><body><p><span style=\" font-weight:600;\">Why I can\'t use it?</span><br/>1) mkclean needs to be install.<br/>2) Open a mkv file before execute command.</p></body></html>"),
                     "MKCleanStatusTip": QCoreApplication.translate("Actions", "Clean/Optimize Matroska files with MKClean."),

                     "MKViewText": QCoreApplication.translate("Actions", "&Play MKV file"),
                     "MKViewToolTip": QCoreApplication.translate("Actions", "<html><head/><body><p><span style=\" font-weight:600;\">Why I can\'t use it?</span><br/>1) Open a mkv file before execute command.</p></body></html>"),
                     "MKViewStatusTip": QCoreApplication.translate("Actions", "Open the MKV file with the default application."),

                     "MKVExecute2Text": QCoreApplication.translate("Actions", "&Start job queue"),
                     "MKVExecute2ToolTip": QCoreApplication.translate("Actions", "<html><head/><body><p><span style=\" font-weight:600;\">Why I can\'t use it?</span><br/>1) Open a mkv file.<br/>2) Tick tracks before execute command.</p></body></html>"),
                     "MKVExecute2StatusTip": QCoreApplication.translate("Actions", "Launch extract/convert/mux tracks."),

                     "PauseText": QCoreApplication.translate("Actions", "Pause"),
                     "PauseStatusTip": QCoreApplication.translate("Actions", "Press button to pause the jobs."),
                     "PauseErrorStatusTip": QCoreApplication.translate("Actions", "The pause button needs python3 psutil2 module."),
                     "ResumeText": QCoreApplication.translate("Actions", "Resume"),
                     "ResumeStatusTip": QCoreApplication.translate("Actions", "Press button to resume the jobs."),

                     "SelectedFile": QCoreApplication.translate("Select", "Selected file: {}."),
                     "SelectedFolder1": QCoreApplication.translate("Select", "Selected folder: {}."),
                     "SelectedFolder2": QCoreApplication.translate("Select", 'Always use the same output folder as the input MKV file (automatically updated)'),

                     "SelectFileInCheckbox": QCoreApplication.translate("Select", "Keep in memory the last file opened for open it at the next launch of MKV Extractor Qt (to use for tests)"),
                     "SelectFileIn": QCoreApplication.translate("Select", "Select the input MKV File"),
                     "SelectFileOut": QCoreApplication.translate("Select", "Select the output MKV file"),
                     "SelectFolder": QCoreApplication.translate("Select", "Select the output folder"),

                     "UseMMGTitle": QCoreApplication.translate("UseMMG", "MKV Merge Gui or MKV Extractor Qt ?"),
                     "UseMMGText": QCoreApplication.translate("UseMMG", "You want extract and reencapsulate the tracks without use other options.\n\nIf you just need to make this, you should use MKVToolNix-Gui (previously mmg) who is more adapted for this job.\n\nWhat software do you want use ?\n"),

                     "RemuxRenameCheckBox": QCoreApplication.translate("RemuxRename", "Always use the default file rename (MEG_FileName)"),
                     "RemuxRenameTitle": QCoreApplication.translate("RemuxRename", "Choose the output file name"),

                     "Audio": QCoreApplication.translate("Track", "audio"),
                     "Subtitles": QCoreApplication.translate("Track", "subtitles"),
                     "Video": QCoreApplication.translate("Track", "video"),

                     "TrackAac": QCoreApplication.translate("Track", "If the remuxed file has reading problems, change this value."),
                     "TrackAudio": QCoreApplication.translate("Track", "Change the language if it's not right. 'und' means 'Undetermined'."),
                     "TrackAttachment": QCoreApplication.translate("Track", "This track can be renamed and must contain an extension to avoid reading errors by clicking on the icon."),
                     "TrackChapters": QCoreApplication.translate("Track", "chapters"),
                     "TrackID1": QCoreApplication.translate("Track", "Work with track number {}."), # Pour les pistes normales
                     "TrackID2": QCoreApplication.translate("Track", "Work with attachment number {}."), # Pour les fichiers joints
                     "TrackID3": QCoreApplication.translate("Track", "Work with {}."), # Pour les chapitres et les tags
                     "TrackRename": QCoreApplication.translate("Track", "This track can be renamed by doubleclicking."),
                     "TrackTags": QCoreApplication.translate("Track", "tags"),
                     "TrackType": QCoreApplication.translate("Track", "This track is a {} type and cannot be previewed."),
                     "TrackType2": QCoreApplication.translate("Track", "This track is a {} type and can be previewed."),
                     "TrackTypeAttachment": QCoreApplication.translate("Track", "This attachment file is a {} type, it can be extracted (speedy) and viewed by clicking."),
                     "TrackVideo": QCoreApplication.translate("Track", "Change the fps value if needed. Useful in case of audio lag. Normal : 23.976, 25.000 and 30.000."),

                     "QtesseractConvertText": QCoreApplication.translate("Qtesseract5", "Convert SUB files to SRT files"),
                     "QtesseractConvertStatusTip": QCoreApplication.translate("Qtesseract5", "Convert the SUB files to SRT with Qtesseract5. A click on checked item uncheck it."),
                     "QtesseractConvertToolTip1": QCoreApplication.translate("Qtesseract5", "Qtesseract5 isn't installed, impossible to convert the SUB files."),
                     "QtesseractConvertToolTip2": QCoreApplication.translate("Qtesseract5", "Qtesseract5 isn't executable, impossible to convert the SUB files."),
                     "QtesseractConvertToolTip3": QCoreApplication.translate("Qtesseract5", "Convert the SUB files to SRT with Qtesseract5.\n A click on checked item uncheck it."),

                     "QtesseractOpenText": QCoreApplication.translate("Qtesseract5", "Open the SUB files in Qtesseract5"),
                     "QtesseractOpenStatusTip": QCoreApplication.translate("Qtesseract5", "Open the SUB files in Qtesseract5. A click on checked item uncheck it."),
                     "QtesseractOpenToolTip1": QCoreApplication.translate("Qtesseract5", "Qtesseract5 isn't installed, impossible to open the SUB files with it."),
                     "QtesseractOpenToolTip2": QCoreApplication.translate("Qtesseract5", "Qtesseract5 isn't executable, impossible to open the SUB files with it."),
                     "QtesseractOpenToolTip3": QCoreApplication.translate("Qtesseract5", "Open the SUB files in Qtesseract5 gui for better configuration.\n A click on checked item uncheck it."),

                     "QtesseractTitle": QCoreApplication.translate("Qtesseract5", "Expected location of the SRT file"),
                     "QtesseractInfoText": QCoreApplication.translate("Qtesseract5", "Since the SRT file is reused later, it must be saved under the address: {}"),

                     "FFMpegConvertText": QCoreApplication.translate("FFMpeg", "Convert SUP/PGS files to SUB files"),
                     "FFMpegConvertStatusTip": QCoreApplication.translate("FFMpeg", "Convert the SUP/PGS files to SUB files with FFMpeg. A click on checked item uncheck it."),
                     "FFMpegConvertToolTip1": QCoreApplication.translate("FFMpeg", "FFMpeg isn't installed, impossible to convert the SUP/PGS files with it."),
                     "FFMpegConvertToolTip2": QCoreApplication.translate("FFMpeg", "FFMpeg isn't executable, impossible to convert the SUP/PGS files with it."),
                     "FFMpegConvertToolTip3": QCoreApplication.translate("FFMpeg", "Convert the SUP/PGS files to SUB files with FFMpeg.\nA click on checked item uncheck it."),

                     "BDSup2SubConvertText": QCoreApplication.translate("BDSup2Sub", "Convert SUP/PGS files to SUB files"),
                     "BDSup2SubConvertStatusTip": QCoreApplication.translate("BDSup2Sub", "Convert the SUP/PGS files to SUB files with BDSup2Sub. A click on checked item uncheck it."),
                     "BDSup2SubConvertToolTip1": QCoreApplication.translate("BDSup2Sub", "BDSup2Sub isn't installed, impossible to convert the SUP/PGS files with it."),
                     "BDSup2SubConvertToolTip2": QCoreApplication.translate("BDSup2Sub", "BDSup2Sub isn't executable, impossible to convert the SUP/PGS files with it."),
                     "BDSup2SubConvertToolTip3": QCoreApplication.translate("BDSup2Sub", "Convert the SUP/PGS files to SUB files with BDSup2Sub.\nA click on checked item uncheck it."),

                     "BDSup2SubOpenText": QCoreApplication.translate("BDSup2Sub", "Open the SUP/PGS files in BDSup2Sub"),
                     "BDSup2SubOpenStatusTip": QCoreApplication.translate("BDSup2Sub", "Open SUP/PGS files in BDSup2Sub. A click on checked item uncheck it."),
                     "BDSup2SubOpenToolTip1": QCoreApplication.translate("BDSup2Sub", "BDSup2Sub isn't installed, impossible to open SUP/PGS files to SUB files."),
                     "BDSup2SubOpenToolTip2": QCoreApplication.translate("BDSup2Sub", "BDSup2Sub isn't executable, impossible to open SUP/PGS files to SUB files."),
                     "BDSup2SubOpenToolTip3": QCoreApplication.translate("BDSup2Sub", "Open the SUP/PGS files in BDSup2Sub gui for better configuration.\nA click on checked item uncheck it."),

                     "BDSup2SubTitle": QCoreApplication.translate("BDSup2Sub", "Expected location of the IDX file"),
                     "BDSup2SubInfoText": QCoreApplication.translate("BDSup2Sub", "Since the IDX file is reused later, it must be saved under the address: {}"),

                     "Header1": QCoreApplication.translate("Tracks", "Click here to (un)select all tracks."),
                     "Header2": QCoreApplication.translate("Tracks", "Icon of the tracks, the attachments icons are clickable to view them."),
                     "Header3": QCoreApplication.translate("Tracks", "Name or information of the tracks. It's possible to edit them by double click."),
                     "Header4": QCoreApplication.translate("Tracks", "Audio and subtitles language or fps of the videos can be modified. Size of the attached files."),
                     "Header5": QCoreApplication.translate("Tracks", "Codec or extension of the tracks. Only codec AAC can be modified."),

                     "WorkFileCheckTitle" : QCoreApplication.translate("Work", "Files missing !"),
                     "WorkFileCheckText" : QCoreApplication.translate("Work", "The following files are missing for the proper execution of the command:\n - {}"),
                     "WorkTestTitle" : QCoreApplication.translate("Work", "{} problem !"),
                     "WorkTestText" : QCoreApplication.translate("Work", "<b>{}</b> is the base of this software,<br>this command is <b>mandatory</b> !<br><br>To configure the command,<br>go to <b>Options > Softwares locations</b>."),
                     "WorkCanceled" : effet + QCoreApplication.translate("Work", " All commands were canceled ") + effet,
                     "WorkCmd": QCoreApplication.translate("Work", """Command execution: <span style=" color:#0000c0;">{}</span>"""),
                     "WorkError" : effet + QCoreApplication.translate("Work", " The last command returned an error ") + effet,
                     "WorkFinished" : effet + QCoreApplication.translate("Work", " {} execution is finished ") + effet,
                     "WorkMerge" : effet + QCoreApplication.translate("Work", " Load of MKV File Tracks ") + effet,
                     "WorkProgress" : effet + QCoreApplication.translate("Work", " {} execution in progress ") + effet,
                    }


        ### Recharge les textes de l'application graphique du fichier ui.py
        self.ui.retranslateUi(self)

        ### Mise au propre du widget de retour d'info et envoie de langue
        if not TempValues.value("FirstRun"): # Variable évitant l'envoie inutile d'info au démarrage
            self.ui.reply_info.clear()

            if Configs.value("DebugMode"):
                self.SetInfo(self.Trad["OptionUpdate"].format("Language", value), newline=True)

        else:
            TempValues.setValue("FirstRun", False)


        ### Recharge le SysTrayQuit
        self.SysTrayQuit.setText(self.Trad["SysTrayQuit"])

        ### Message spécifique si le bouton pause n'est pas utilisable
        if not 'psutil' in globals():
            self.ui.mkv_pause.setStatusTip(self.Trad["PauseErrorStatusTip"])

        ### Recharge les actions
        self.mkv_info.setText(self.Trad["MKVInfoText"])
        self.mkv_info.setToolTip(self.Trad["MKVInfoToolTip"])
        self.mkv_info.setStatusTip(self.Trad["MKVInfoStatusTip"])

        self.mkv_mkvtoolnix.setText(self.Trad["MKVMergeText"])
        self.mkv_mkvtoolnix.setToolTip(self.Trad["MKVMergeToolTip"])
        self.mkv_mkvtoolnix.setStatusTip(self.Trad["MKVMergeStatusTip"])

        self.mk_validator.setText(self.Trad["MKValidatorText"])
        self.mk_validator.setToolTip(self.Trad["MKValidatorToolTip"])
        self.mk_validator.setStatusTip(self.Trad["MKValidatorStatusTip"])

        self.mk_clean.setText(self.Trad["MKCleanText"])
        self.mk_clean.setToolTip(self.Trad["MKCleanToolTip"])
        self.mk_clean.setStatusTip(self.Trad["MKCleanStatusTip"])

        self.mkv_view.setText(self.Trad["MKViewText"])
        self.mkv_view.setToolTip(self.Trad["MKViewToolTip"])
        self.mkv_view.setStatusTip(self.Trad["MKViewStatusTip"])

        self.mkv_execute_2.setText(self.Trad["MKVExecute2Text"])
        self.mkv_execute_2.setToolTip(self.Trad["MKVExecute2ToolTip"])
        self.mkv_execute_2.setStatusTip(self.Trad["MKVExecute2StatusTip"])

        ### Recharger les statustip des headers
        self.ui.mkv_tracks.horizontalHeaderItem(1).setStatusTip(self.Trad["Header1"])
        self.ui.mkv_tracks.horizontalHeaderItem(2).setStatusTip(self.Trad["Header2"])
        self.ui.mkv_tracks.horizontalHeaderItem(3).setStatusTip(self.Trad["Header3"])
        self.ui.mkv_tracks.horizontalHeaderItem(4).setStatusTip(self.Trad["Header4"])
        self.ui.mkv_tracks.horizontalHeaderItem(5).setStatusTip(self.Trad["Header5"])

        ### Recharge les textes des toolbutton
        self.option_ffmpeg.setText(self.Trad["OptionsFFMpeg"])
        self.option_ffmpeg.setStatusTip(self.Trad["OptionsFFMpegStatusTip"])
        self.option_ffmpeg.setToolTip(self.Trad["OptionsFFMpegStatusTip"])
        self.option_to_ac3.setText(self.Trad["OptionsDTStoAC31"])
        self.option_to_ac3.setStatusTip(self.Trad["OptionsDTStoAC32"])
        self.option_stereo.setText(self.Trad["OptionsStereo1"])
        self.PowerMenu.setTitle(self.Trad["OptionsPowerList"])
        self.RatesMenu.setTitle(self.Trad["OptionsQuality"])
        self.option_subtitles_open.setText(self.Trad["OptionsSub1"])
        self.option_subtitles_open.setStatusTip(self.Trad["OptionsSub2"])
        self.option_stereo.setStatusTip(self.Trad["OptionsStereo2"])
        self.ui.reply_info.setStatusTip(self.Trad["QTextEditStatusTip"])

        for nb in [2, 3, 4, 5]:
            PowerList[nb].setText(self.Trad["OptionsPowerY"].format(nb))
            PowerList[nb].setStatusTip(self.Trad["OptionsPowerX"].format(nb))

        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
            QualityList[nb].setStatusTip(self.Trad["OptionsQualityX"].format(nb))
            QualityList[nb].setText(self.Trad["OptionsQualityY"].format(nb))

        for Style in QtStyleList.keys():
            QtStyleList[Style].setStatusTip(self.Trad["OptionsStyles"].format(Style))

        ### Traduction des actions de conversion des sous titres
        self.SubtitlesTranslation(True)

        ### Recharge les emplacements des exécutables
        self.SoftwareFinding()

        ### Si un dossier de sortie a déjà été sélectionné, mise à jour du statustip et affiche l'info
        if Configs.value("OutputFolder"):
            self.ui.output_folder.setStatusTip(self.Trad["SelectedFolder1"].format(Configs.value("OutputFolder")))
            self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + Configs.value("OutputFolder") + '</span>'), newline=True)

        ### Si un fichier mkv à déjà été chargé, relance le chargement du fichier pour tout traduire et remet en place les cases et boutons cochés
        if TempValues.value("MKVLoaded"):
            ## Crée la liste des boutons cochés
            WidgetsList = []
            for Widget in [self.ui.option_reencapsulate, self.ui.option_subtitles, self.ui.option_audio]:
                if Widget.isChecked():
                    WidgetsList.append(Widget)

            ## Relance le chargement du fichier mkv pour tout traduire
            self.InputFile(Configs.value("InputFile"))

            ## Recoche les pistes qui l'étaient, crée une liste car MKVDicoSelect sera modifié pendant la boucle
            for x in list(MKVDicoSelect.keys()):
                self.ui.mkv_tracks.item(x, 1).setCheckState(2)

            ## Recoche les boutons
            for Widget in WidgetsList:
                Widget.setChecked(True)


    #========================================================================
    def SetInfo(self, text, color="000000", center=False, newline=False):
        """Fonction mettant en page les infos à afficher dans le widget d'information."""
        ### Saut de ligne à la demande si le widget n'est pas vide
        if newline and self.ui.reply_info.toPlainText() != "":
            self.ui.reply_info.append('')

        ### Envoie du nouveau texte avec mise en page
        if center:
            self.ui.reply_info.append("""<center><table><tr><td><span style=" color:#{};">{}</span></td></tr></table></center>""".format(color, text))

        else:
            self.ui.reply_info.append("""<span style=" color:#{};">{}</span>""".format(color, text))

        ### Force l'affichage de la dernière ligne
        self.ui.reply_info.moveCursor(QTextCursor.End)


    #========================================================================
    def Configuration(self):
        """Fonction affichant les options et leur valeurs."""
        ### Bloque la connexion pour éviter les messages d'erreur
        self.ui.configuration_table.blockSignals(True)

        ### Nécessaire à l'affichage des statustip
        self.ui.configuration_table.setMouseTracking(True)

        ### Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 1:
            self.ui.stackedMiddle.setCurrentIndex(1)

        while self.ui.configuration_table.rowCount() != 0:
            self.ui.configuration_table.removeRow(0)

        ### Remplissage du tableau, chaque ligne renvoie (num_de_ligne, (Key, Value))
        for x, (Key, Value) in enumerate(DefaultValues.items()):
            # Création de la ligne
            self.ui.configuration_table.insertRow(x)

            # Remplissage de la ligne (nom, valeur, valeur par défaut)
            self.ui.configuration_table.setItem(x, 0, QTableWidgetItem(Key))

            # Valeur actuelle
            Item = QTableWidgetItem(str(Configs.value(Key)))

            # Mise en gras si la valeur actuelle diffère de celle par défaut
            if str(Value) != str(Configs.value(Key)):
                Font = QFont()
                Font.setBold(True)
                Item.setFont(Font)

            self.ui.configuration_table.setItem(x, 1, QTableWidgetItem(Item))
            self.ui.configuration_table.setItem(x, 2, QTableWidgetItem(str(Value)))

            # Blocage de la modification
            self.ui.configuration_table.item(x, 0).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.configuration_table.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            # Si c'est la variable d'un exécutable, on cache la ligne
            if Key[0:8] == 'Location':
                self.ui.configuration_table.setRowHidden(x, True)

            # Sinon on envoie du statustip
            else:
                self.ui.configuration_table.item(x, 0).setStatusTip(self.Trad[Key])
                self.ui.configuration_table.item(x, 1).setStatusTip(self.Trad[Key])
                self.ui.configuration_table.item(x, 2).setStatusTip(self.Trad[Key])


        ### Visuel du tableau
        self.ui.configuration_table.sortItems(0) # Rangement par ordre de nom d'option
        largeur = int((self.ui.configuration_table.size().width() - 185) / 2) # Calcul de la largeur
        self.ui.configuration_table.setColumnWidth(0, 160) # Définition de la largeur de la colonne
        self.ui.configuration_table.setColumnWidth(1, largeur) # Définition de la largeur de la colonne
        self.ui.configuration_table.setColumnWidth(2, largeur) # Définition de la largeur de la colonne
        self.ui.configuration_table.setSortingEnabled(False) # Blocage du rangement

        ### Débloque la connexion
        self.ui.configuration_table.blockSignals(False)


    #========================================================================
    def ConfigurationEdit(self, Item):
        """Fonction de mise à jour de la configuration."""
        ### Récupération de la cellule modifiée et des valeurs
        x = self.ui.configuration_table.row(Item)
        Option = self.ui.configuration_table.item(x, 0).text()
        Value = self.ui.configuration_table.item(x, 1).text()

        ### Si la valeur est vide, on utilise celle par défaut
        if not Value:
            Value = self.ui.configuration_table.item(x, 2).text()
            self.ui.configuration_table.setItem(x, 1, QTableWidgetItem(Value))


        ### Vérifie la classe et corrige si besoin de la valeur
        ## En cas de type bool
        if isinstance(DefaultValues[Option], bool):
            # Pour gérer les vrai
            if Value.lower() == "true":
                self.OptionsValue(Option, True)

            # Pour gérer les faux
            elif Value.lower() == "false":
                self.OptionsValue(Option, False)

            # Si mauvaise valeur, on indique l'erreur et utilise la valeur par défaut
            else:
                # Message d'erreur
                QMessageBox(QMessageBox.Critical, self.Trad["ErrorConfigTitle"], self.Trad["ErrorConfigText"].format(Option), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

                # Modification du texte et donc de la valeur (ça relance cette fonction)
                self.ui.configuration_table.item(x, 1).setText(str(DefaultValues[Option]))

        ## En cas de type int
        elif isinstance(DefaultValues[Option], int):
            # Essaie de convertir en int
            try:
                self.OptionsValue(Option, int(Value))

            # Si ça foire,  on indique l'erreur et utilise la valeur par défaut
            except:
                # Message d'erreur
                QMessageBox(QMessageBox.Critical, self.Trad["ErrorConfigTitle"], self.Trad["ErrorConfigText"].format(Option), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

                # Modification du texte et donc de la valeur (ça relance cette fonction)
                self.ui.configuration_table.item(x, 1).setText(str(DefaultValues[Option]))

        ## En cas de type str
        else:
            # Si la valeur est une adresse existante, on converti en QFileInfo
            if QFileInfo(Value).exists():
                self.OptionsValue(Option, QFileInfo(Value))

                # En cas de modification du dossier temporaire
                if Option == "FolderParentTemp":
                    self.OptionsValue(Option, Value)
                    self.FolderTempCreate()


            # Sinon, c'est que c'est juste du texte
            else:
                # Si l'adresse est erronée
                if Option in ["OutputFolder", "InputFolder", "MKVConvertThisFolder"]:
                    # Message d'erreur
                    QMessageBox(QMessageBox.Critical, self.Trad["ErrorConfigTitle"], self.Trad["ErrorConfigPath"].format(Option), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

                    # Modification du texte et donc de la valeur (ça relance cette fonction)
                    self.ui.configuration_table.item(x, 1).setText(DefaultValues[Option])

                else:
                    self.OptionsValue(Option, str(Value))


    #========================================================================
    def ConfigurationReset(self):
        """Fonction de réinitialisation des configs."""
        ### Utilisation de toutes les valeurs par défauts
        for Key, Value in DefaultValues.items():
            self.OptionsValue(Key, Value)

        ### Rechargement de la liste d'infos
        self.Configuration()


    #========================================================================
    def FeedbackWidget(self, value):
        """Fonction appelée lors de l'ouverture et la fermeture du dockwidget."""
        ### Mise à jour de la variable
        Configs.setValue("Feedback", value)

        ### Mise à jour de la case à cocher
        self.ui.option_feedback.setChecked(value)


    #========================================================================
    def HumanSize(self, Value):
        """Fonction rendant plus lisible les tailles."""
        ### Valeur finale
        HumanValue = ""

        ### Conversion dans une catégorie supérieure
        for count in ['Bytes', 'KB', 'MB', 'GB']:
            if Value > -1024.0 and Value < 1024.0:
                HumanValue = "%3.1f%s" % (Value, count)

            Value /= 1024.0

        if not HumanValue:
            HumanValue = "%3.1f%s" % (Value, 'TB')

        ### Renvoie la valeur finale
        return HumanValue


    #========================================================================
    def CheckSize(self, Folder, InputSize, OutputSize, Text):
        """Fonction vérifiant qu'il y a assez de place pour travailler."""
        ### Pas de test si valeur le demandant
        if Configs.value("CheckSizeCheckbox", False):
            return False

        ### Affiche un message s'il n'y a pas la double de la place
        if (InputSize * 2) > OutputSize:
            HumanInputSize = self.HumanSize(int(InputSize))
            HumanOutputSize = self.HumanSize(int(OutputSize))

            ## Création de la fenêtre d'information
            ChoiceBox = QMessageBox(QMessageBox.Warning, self.Trad["ErrorSizeTitle"], Text.format(TempValues.value(Folder), HumanOutputSize, HumanInputSize), QMessageBox.NoButton, self, Qt.WindowSystemMenuHint)
            CheckBox = QCheckBox(self.Trad["Convert0"], ChoiceBox)
            Button1 = QPushButton(QIcon.fromTheme("folder-open", QIcon(":/img/folder-open.png")), self.Trad["ErrorSizeButton1"], ChoiceBox)
            Button2 = QPushButton(QIcon.fromTheme("dialog-ok", QIcon(":/img/dialog-ok.png")), self.Trad["ErrorSizeButton2"], ChoiceBox)
            Button3 = QPushButton(QIcon.fromTheme("process-stop", QIcon(":/img/process-stop.png")), self.Trad["ErrorSizeButton3"], ChoiceBox)
            ChoiceBox.setCheckBox(CheckBox) # Envoie de la checkbox
            ChoiceBox.addButton(Button3, QMessageBox.NoRole) # Ajout du bouton
            ChoiceBox.addButton(Button2, QMessageBox.YesRole) # Ajout du bouton
            ChoiceBox.addButton(Button1, QMessageBox.ApplyRole) # Ajout du bouton
            Choice = ChoiceBox.exec()

            Configs.setValue("CheckSizeCheckbox", CheckBox.isChecked())

            ## Si on veut changer de répertoire
            if Choice == 2:
                # Affichage de la fenêtre
                FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFolder"], TempValues.value(Folder))
                OutputFolder = QFileInfo(FileDialogCustom.createWindow("Folder", "Open", None, Qt.Tool, Language=Configs.value("Language"))[0])

                # Si un dossier a bien été indiqué
                if not OutputFolder.isDir():
                    return True

                else:
                    TempValues.setValue(Folder, OutputFolder.absoluteFilePath())


            ## Si on continue
            elif Choice == 1:
                return False

            ## Si on stoppe
            elif Choice == 0:
                return True


    #========================================================================
    def FolderTempCreate(self):
        """Fonction créant le dossier temporaire."""
        ### Boucle permettant d'être sûr d'avoir un dossier de créé
        while True:
            # Création du dossier temporaire
            self.FolderTempWidget = QTemporaryDir(Configs.value("FolderParentTemp") + "/mkv-extractor-qt5-")

            # Suppression de l'auto suppression du dossier non adapté
            self.FolderTempWidget.setAutoRemove(False)

            # Si le dossier est valide, on l'enregistre et arrête la boucle
            if self.FolderTempWidget.isValid():
                TempValues.setValue("FolderTemp", self.FolderTempWidget.path()) # Dossier temporaire
                break


    #========================================================================
    def AboutMKVExtractorQt5(self):
        """Fenêtre à propos de MKVExtractorQt5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["AboutTitle"], self.Trad["AboutText"].format(app.applicationVersion(), "http://www.gnu.org/copyleft/gpl.html"), QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def HelpMKVExtractorQt5(self):
        """Fenêtre d'aide de MKVExtractorQt5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["HelpTitle"], self.Trad["HelpText"], QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def TheyTalkAbout(self):
        """Fenêtre "Ils en parlent" de MKVExtractorQt5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["TheyTalkAboutTitle"], self.Trad["TheyTalkAboutText"], QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def MKVInfoGui(self):
        """Fonction ouvrant le fichier MKV avec le logiciel MKVInfo en mode détaché."""
        self.process.startDetached('{} "{}"'.format(Configs.value("Location/MKVInfo"), Configs.value("InputFile")))


    #========================================================================
    def MKVMergeGui(self):
        """Fonction ouvrant le fichier MKV avec le logiciel MKVToolNix-Gui (avec le bon nom de commande) en mode détaché."""
        self.process.startDetached('{} "{}"'.format(Configs.value("Location/MKVToolNix"), Configs.value("InputFile")))


    #========================================================================
    def MKVView(self):
        """Fonction ouvrant le fichier MKV avec le logiciel de lecture par défaut."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(Configs.value("InputFile")))


   #========================================================================
    def MKClean(self):
        """Fonction lançant MKClean sur le fichier MKV."""
        InputFileName = QFileInfo(Configs.value("InputFile")).fileName()

        ### On crée automatiquement l'adresse de sortie
        if Configs.value("MKCleanRename") and (Configs.value("MKCleanSameFolder") or Configs.value("MKCleanThisFolder")):
            ## Utilisation du même dossier en entré et sorti ou du dossier choisi
            MKCleanTemp = "{}/Clean_{}".format(Configs.value("OutputFolder", Configs.value("MKCleanThisFolder")), InputFileName)

        ### Fenêtre de sélection de sortie du fichier MKV
        else:
            ## Création de la fenêtre
            FileDialogCustom = QFileDialogCustom(self,
                                                 self.Trad["SelectFileOut"],
                                                 Configs.value("OutputFolder"),
                                                 "Matroska file (*.mkv *.mks *.mka *.mk3d *.webm *.webmv *.webma)")

            MKCleanTemp = FileDialogCustom.createWindow("File",
                                                        "Save",
                                                        None,
                                                        Qt.Tool,
                                                        FileName="Clean_{}".format(InputFileName),
                                                        AlreadyExistsTest=Configs.value("AlreadyExistsTest", False),
                                                        Language=Configs.value("Language"))


        ### Arrêt de la fonction s'il n'y a pas de fichier de choisi
        if not QFileInfo(MKCleanTemp).absoluteFilePath():
            return

        ### Ajout du fichier de sortie dans le listing des fichiers
        TempFiles = [MKCleanTemp]

        ### Commande finale
        TempValues.setValue("Command", ["MKClean", Configs.value("Location/MKClean"), ["--optimize", Configs.value("InputFile"), MKCleanTemp], [Configs.value("InputFile")]])

        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True)
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1] + ' ' + ' '.join(TempValues.value("Command")[2])))

        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.WorkStart()


    #========================================================================
    def MKValidator(self):
        """Fonction lançant MKValidator sur le fichier MKV."""
        ### Code à exécuter
        TempValues.setValue("Command", ["MKValidator", Configs.value("Location/MKValidator"), [Configs.value("InputFile")], [Configs.value("InputFile")]])

        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1] + ' ' + ' '.join(TempValues.value("Command")[2]))) # Envoie d'informations

        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.ui.progressBar.setMaximum(0) # Mode pulsation de la barre de progression
        self.WorkStart()


    #========================================================================
    def MKVConvert(self, File):
        """Fonction de conversion d'une vidéo en fichier MKV."""
        # File : URL du fichier au format QFileInfo

        ### Proposition de conversion de la vidéo
        if not Configs.value("ConfirmConvert"):
            ## Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
            dialog = QMessageBox(QMessageBox.Warning, self.Trad["Convert1"], self.Trad["Convert2"], QMessageBox.NoButton, self)
            CheckBox = QCheckBox(self.Trad["Convert0"])
            dialog.setCheckBox(CheckBox)
            dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            dialog.setDefaultButton(QMessageBox.Ok)
            dialog.setIconPixmap(QPixmap(QIcon().fromTheme("dialog-warning", QIcon(":/img/dialog-warning.png")).pixmap(64)))
            Confirmation = dialog.exec_()

            ## Mise en mémoire de la case à cocher
            Configs.setValue("ConfirmConvert", CheckBox.isChecked())

            ## Arrêt de la fonction en cas de refus
            if Confirmation != 1024:
                return


        ### Choix du dossier de sortie
        FileDialogCustom = QFileDialogCustom(self, self.Trad["Convert6"], File.absolutePath())
        OutputFile = FileDialogCustom.createWindow("File",
                                                   "Save",
                                                   None,
                                                   Qt.Tool,
                                                   FileName="{}.mkv".format(File.completeBaseName()),
                                                   AlreadyExistsTest=Configs.value("AlreadyExistsTest", False),
                                                   Language=Configs.value("Language"))

        ### En cas d'annulation
        if not OutputFile:
            return

        ### Nettoyage graphique ici aussi afin de tout nettoyer avant la conversion pour un visuel plus joli
        ## Désactivation des différentes options qui pourraient être activées
        for widget in [self.ui.option_reencapsulate, self.ui.option_subtitles, self.ui.option_audio]:
            widget.setChecked(False)
            widget.setEnabled(False)

        ## Désactivation des widgets
        for Widget in [self.mkv_info, self.mkv_mkvtoolnix, self.mk_validator, self.mk_clean, self.mkv_view, self.mkv_execute_2]:
            Widget.setEnabled(False)

        ## Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 0:
            self.ui.stackedMiddle.setCurrentIndex(0)

        while self.ui.mkv_tracks.rowCount() != 0:
            self.ui.mkv_tracks.removeRow(0)

        ## Suppression du titre
        self.ui.mkv_title.setText("")

        ### Mise à jour des variables
        WarningReply.clear() # Réinitialisation des retours de warning de mkvmerge
        AllTempFiles.clear()
        AllTempFiles.append(OutputFile) # Ajout du fichier dans la liste en cas d'arrêt
        TempValues.setValue("Command", ["FileToMKV", "mkvmerge", ["-o", OutputFile, File.absoluteFilePath()], [File.absoluteFilePath()]]) # Commande de conversion

        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1] + ' ' + ' '.join(TempValues.value("Command")[2]))) # Envoie d'informations

        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.WorkStart()


    #========================================================================
    def RemoveTempFiles(self):
        """Fonction supprimant les fichiers contenu dans la liste des fichiers temporaires."""
        ### Boucle supprimant les fichiers temporaires s'ils existent
        for Item in TempFiles:
            if QFileInfo(Item).exists() and QFileInfo(Item).isFile():
                QFile(Item).remove()

        ### Nettoyage de la liste des fichiers temporaires
        TempFiles.clear()


    #========================================================================
    def RemoveAllTempFiles(self):
        """Fonction supprimant les fichiers contenu dans la liste des fichiers temporaires."""
        ### Boucle supprimant les fichiers temporaires s'ils existent
        for Item in AllTempFiles:
            if QFileInfo(Item).exists() and QFileInfo(Item).isFile():
                QFile(Item).remove()

        ### Nettoyage de la liste des fichiers temporaires
        AllTempFiles.clear()


    #========================================================================
    def OutputFolder(self, OutputFolderTemp=None):
        """Fonction de sélection du dossier de sortie, est appelée via un clic ou via un glisser/déposer de dossier."""
        # OutputFolderTemp : Url au format texte

        if OutputFolderTemp == Configs.value("OutputFolder"):
            return

        ### En cas de lancement via l'interface graphique
        if not OutputFolderTemp:
            ## Création et coche si besoin de la checkbox
            CheckBox = QCheckBox(self.Trad["SelectedFolder2"])
            CheckBox.setChecked(Configs.value("OutputSameFolder"))

            ## Affichage de la fenêtre
            FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFolder"], Configs.value("OutputFolder"))
            OutputFolderTemp = FileDialogCustom.createWindow("Folder", "Open", CheckBox, Qt.Tool, Language=Configs.value("Language"))

            ## Mise à jour de l'option
            Configs.setValue("OutputSameFolder", CheckBox.isChecked())

        ### Arrêt de la fonction si aucun fichier n'est sélectionné et qu'on n'utilise pas le même dossier de sorti
        if not QFileInfo(OutputFolderTemp).isDir() and not Configs.value("OutputSameFolder"):
            return

        ### Suite de la fonction
        # URL absolue au format texte
        OutputFolderTemp = QFileInfo(OutputFolderTemp).absoluteFilePath()

        # Mise à jour de la variable du dossier de sorti
        Configs.setValue("OutputFolder", OutputFolderTemp)

        # Mis à jour du statustip de l'item de changement de dossier
        self.ui.output_folder.setStatusTip(self.Trad["SelectedFolder1"].format(OutputFolderTemp))

        # Envoie d'information en mode debug
        if Configs.value("DebugMode"):
            self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + OutputFolderTemp + '</span>'), newline=True)

        ### Modifications graphiques
        # Cela n'a lieu que si un dossier et un fichier mkv sont choisis
        if TempValues.value("MKVLoaded") and MKVDicoSelect:
            self.ui.option_reencapsulate.setEnabled(True) # Déblocage de widget
            self.ui.mkv_execute.setEnabled(True) # Déblocage de widget
            self.mkv_execute_2.setEnabled(True) # Déblocage de widget

            option_audio = False # Blocage de widget
            option_subtitles = False # Blocage de widget

            for valeurs in MKVDicoSelect.values(): # Boucle sur la liste des lignes
                # Recherche la valeur audio dans les sous listes
                if valeurs[2] == "audio-x-generic" and self.SoftIsExec("FFMpeg"):
                    option_audio = True # Déblocage de widget

                # Recherche la valeur vobsub dans les sous listes
                elif valeurs[-1] == "sub" and self.SoftIsExec("Qtesseract5"):
                    option_subtitles = True # Déblocage de widget

                elif valeurs[-1] in ("sup", "pgs") and self.SoftIsExec("BDSup2Sub|FFMpeg"):
                    option_subtitles = True # Déblocage de widget

                # Arrêt de la boucle si on les 2 valeurs
                if option_audio and option_subtitles:
                    break

            # Mise à jour de l'état des widgets
            self.ui.option_audio.setEnabled(option_audio)
            self.ui.option_subtitles.setEnabled(option_subtitles)


    #========================================================================
    def InputFile(self, MKVLinkTemp=None):
        """Fonction de sélection du fichier d'entrée."""
        # MKVLinkTemp : URL au format str

        ### Si aucun fichier n'est donné en argument
        if not MKVLinkTemp:
            ## Création du widget à ajouter à la boite
            BigWidget = QWidget()
            BigLayout = QVBoxLayout()
            CheckBox1 = QCheckBox(self.Trad["SelectFileInCheckbox"], BigWidget)
            CheckBox1.setChecked(Configs.value("LastFile"))
            BigLayout.addWidget(CheckBox1)
            BigWidget.setLayout(BigLayout)

            ## Affichage de la fenêtre
            FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFileIn"], Configs.value("InputFolder"), '{}(*.mk3d *.mka *.mks *.mkv *.webm *.webma *.webmv);; {}(*.avi *.m4a *.mp4 *.nut *.ogg *.ogm *.ogv);; {}(*.avi *.m4a *.mk3d *.mka *.mks *.mkv *.mp4 *.nut *.ogg *.ogm *.ogv *.webm *.webma *.webmv)'.format(self.Trad["MatroskaFiles"], self.Trad["OtherFiles"], self.Trad["AllFiles"]))
            MKVLinkTemp = FileDialogCustom.createWindow("File", "Open", BigWidget, Qt.Tool, Language=Configs.value("Language"))

            ## Mise à jour de l'option
            Configs.setValue("LastFile", CheckBox1.isChecked())

        ### Transformation du type de la variable
        MKVLinkTemp = QFileInfo(MKVLinkTemp)

        ### Arrêt de la fonction si le fichier n'existe pas
        if not MKVLinkTemp.isFile():
            return

        ### Si le fichier nécessite une conversion en MKV
        if MKVLinkTemp.suffix().lower() in ("avi", "mp4", "m4a", "nut", "ogg", "ogm", "ogv"):
            self.MKVConvert(MKVLinkTemp) # Lancement de la conversion et la fonction sera relancée par WorkFinished

        ### Continuation de la fonction si un fichier est bien sélectionné
        else:
            # Mise à jour de variables
            Configs.setValue("InputFile", MKVLinkTemp.absoluteFilePath())
            Configs.setValue("InputFolder", MKVLinkTemp.absolutePath())

            # Envoie d'information quelque soit le mode de debug
            self.SetInfo(self.Trad["SelectedFile"].format('<span style=" color:#0000c0;">' + Configs.value("InputFile") + '</span>'))

            # Mise à jour du statustip du menu d'ouverture d'un fichier MKV
            self.ui.input_file.setStatusTip(self.Trad["SelectedFile"].format(Configs.value("InputFile")))

            # Dans le cas de l'utilisation de l'option SameFolder qui permet d'utiliser le même dossier en sorti qu'en entré
            if Configs.value("OutputSameFolder"):
                self.OutputFolder(Configs.value("InputFolder"))

            # Envoie d'information en mode debug de l'adresse du dossier de sortie s'il existe
            elif Configs.value("OutputFolder") and Configs.value("DebugMode"):
                self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + Configs.value("OutputFolder") + '</span>'))

            # Chargement du contenu du fichier MKV
            self.TracksLoad()


    #========================================================================
    def ComboModif(self, x, value):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'utilisation des combobox du tableau."""
        ### Si x est une chaîne, c'est que ça traite un fichier AAC
        if isinstance(x, str):
            ## Récupération de la ligne
            x = int(x.split("-")[0])

            ## Mise à jour de variables
            if value != MKVDico[x][6]:
                MKVDico[x][6] = value
                if self.ui.mkv_tracks.item(x, 1).checkState():
                    MKVDicoSelect[x][6] = value


        ### Pour les autres combobox
        elif value != MKVDico[x][5]:
            ## Mise à jour de variables
            MKVDico[x][5] = value
            if self.ui.mkv_tracks.item(x, 1).checkState():
                MKVDicoSelect[x][5] = value


    #========================================================================
    def TracksLoad(self):
        """Fonction de listage et d'affichage des pistes contenues dans le fichier MKV."""
        ### Curseur de chargement
        self.setCursor(Qt.WaitCursor)

        ### Mise à jour des variables
        TempValues.setValue("MKVLoaded", True) # Fichier MKV chargé
        TempValues.setValue("AllTracks", False) # Mode sélection all
        TempValues.setValue("SuperBlockTemp", True) # Sert à bloquer les signaux du tableau (impossible d'utiliser blocksignals)
        x = 0 # Sert à indiquer les numéros de lignes
        self.ComboBoxes = {} # Dictionnaire listant les combobox
        MKVDico.clear() # Mise au propre du dictionnaire

        ### Désactivation des différentes options qui pourraient être activés
        self.ui.mkv_execute.setEnabled(False)

        # Décoche et désactive les boutons
        for widget in [self.ui.option_reencapsulate, self.ui.option_subtitles, self.ui.option_audio]:
            widget.setChecked(False)
            widget.setEnabled(False)

        # Décoche les sous actions des boutons
        for widget in [Sup2Sub[1], Sup2Sub[2], Sup2Sub[3], Sub2Srt[1], Sub2Srt[2], self.option_ffmpeg, self.option_to_ac3, self.option_stereo, self.option_subtitles_open]:
            widget.setChecked(False)

        # Réinitialise les valeurs des conversions audio
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
            QualityList[nb].setChecked(False)

        for nb in [2, 3, 4, 5]:
            PowerList[nb].setChecked(False)

        ### Activation des widgets qui attendaient un fichier MKV valide
        self.mkv_view.setEnabled(True)

        # Activation des actions si disponibles et cache les infos bulles d'aide
        for Location, Widget in (("Location/MKClean", self.mk_clean),
                                 ("Location/MKVInfo", self.mkv_info),
                                 ("Location/MKVToolNix", self.mkv_mkvtoolnix),
                                 ("Location/MKValidator", self.mk_validator)):

            if self.SoftIsExec(Location):
                Widget.setEnabled(True)

        ### Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 0:
            self.ui.stackedMiddle.setCurrentIndex(0)

        while self.ui.mkv_tracks.rowCount() != 0:
            self.ui.mkv_tracks.removeRow(0)

        ### Retours d'information
        self.SetInfo(self.Trad["WorkMerge"], "800080", True, True)


        ### Récupération du retour de MKVMerge
        # Vérification de la présence de mkvmerge
        if not self.SoftIsExec("MKVMerge"):
            return

        JsonMKV = ""

        # Exécution de la commande
        for line in self.LittleProcess(Configs.value("Location/MKVMerge"), ["-J", Configs.value("InputFile")]):
            JsonMKV += line

        # Conversion du json en un dictionnaire
        JsonMKV = json.loads(JsonMKV)

        ### Vérification des erreurs
        if JsonMKV["warnings"]:
            self.SetInfo(self.Trad["MKVMergeWarning"], "800080", True, True)
            self.SetInfo("\n".join(JsonMKV["warnings"]))

        if JsonMKV["errors"]:
            self.SetInfo(self.Trad["MKVMergeErrors"], "800080", True, True)
            self.SetInfo("\n".join(JsonMKV["errors"]))

            self.setCursor(Qt.ArrowCursor)
            return

        ### Traitement des données de Json
        # Titre du fichier MKV
        if "title" in JsonMKV["container"]["properties"]:
            # Si le titre existe
            TempValues.setValue("TitleFile", JsonMKV["container"]["properties"]["title"])

        else:
            # Sinon on utilise le nom du fichier
            TempValues.setValue("TitleFile", QFileInfo(Configs.value("InputFile")).completeBaseName())

        # Envoie de la valeur titre
        self.ui.mkv_title.setText(TempValues.value("TitleFile"))

        # Récupération de la durée du fichier MKV
        if "duration" in JsonMKV["container"]["properties"]:
            # Passage de nanosecondes à secondes 10 puissance 9 => il se plante d'un 0 ?!...
            TempValues.setValue("DurationFile", int(JsonMKV["container"]["properties"]["duration"]/10E8))

        ### Boucle traitant les pistes du fichier MKV
        # Renvoie un truc du genre : 0 {"codec": "RealVideo", "id": 0, "properties": {... }}...
        for Track in JsonMKV["tracks"]:
            ID = Track["id"] # Récupération de l'ID de la piste

            ## Récupération du codec de la piste
            if "codec_id" in Track["properties"]:
                codec = Track["properties"]["codec_id"]

                if codec in CodecList:
                     codecInfo = CodecList[codec][1]
                     codec = CodecList[codec][0]

                elif "codec" in Track:
                    codecInfo = codec
                    codec = Track["codec"]

                else:
                    codecInfo = ""
                    code = codec

            elif "codec" in Track:
                codecInfo = ""
                codec = Track["codec"]

            else:
                codecInfo = ""
                codec = "Unknow"


            ## Traitement des videos
            if Track["type"] == "video":
                # Mise à jour des variables
                TrackTypeName = self.Trad["Video"]
                icone = 'video-x-generic'

                # Récupération de l'info1
                if "track_name" in Track["properties"]:
                    info1 = Track["properties"]["track_name"]

                elif "display_dimensions" in Track["properties"]:
                    info1 = Track["properties"]["display_dimensions"]

                elif "pixel_dimensions" in Track["properties"]:
                    info1 = Track["properties"]["pixel_dimensions"]

                else:
                    info1 = ""

                # Liste normale des fps
                ComboItems = ["23.976fps", "25.000fps", "30.000fps"]

                # Récupération du fps de la piste
                if "default_duration" in Track["properties"]:
                    infoTemp = Track["properties"]["default_duration"]

                    if infoTemp in [40000000, 40001000]:
                        info2 = "25.000fps"

                    elif infoTemp == 41708000:
                        info2 = "23.976fps"

                    elif infoTemp == 33333000:
                        info2 = "30.000fps"

                    else:
                        cal = "%.3f" % float(1000000000 / infoTemp)
                        info2 = "{}fps".format(cal)
                        ComboItems.append(str(info2)) # Ajout de la valeur inconnue
                        ComboItems.sort()

                # Cas spécifique où l'info est manquante
                else:
                    info2 = ""

                # Texte à afficher
                Text = self.Trad["TrackVideo"]


            ## Traitement des audios et sous-titres
            elif Track["type"] in ["audio", "subtitles"]:
                # Variables spécifiques à l'audio
                if Track["type"] == "audio":
                    TrackTypeName = self.Trad["Audio"]
                    icone = 'audio-x-generic'

                    # Récupération de l'info1
                    if "track_name" in Track["properties"]:
                        info1 = Track["properties"]["track_name"]

                    elif "audio_sampling_frequency" in Track["properties"]:
                        info1 = Track["properties"]["audio_sampling_frequency"]

                    else:
                        info1 = ""

                # Variables spécifiques aux sous titres
                else:
                    # Mise à jour des variables
                    TrackTypeName = self.Trad["Subtitles"]
                    icone = 'text-x-generic'

                    # Récupération de l'info1
                    if "track_name" in Track["properties"]:
                        info1 = Track["properties"]["track_name"]

                    else:
                        info1 = ""

                # Variables communes
                # Récupération de la langue
                if "language" in Track["properties"]:
                    info2 = Track["properties"]["language"]

                else:
                    info2 = "und"

                # Item servant à remplir la combobox
                ComboItems = MKVLanguages

                # Texte à afficher
                Text = self.Trad["TrackAudio"]


            ## Création, remplissage et connexion d'une combobox qui est envoyée dans une nouvelle ligne du tableau
            self.ui.mkv_tracks.insertRow(x)
            self.ComboBoxes[x] = QComboBox()
            self.ui.mkv_tracks.setCellWidget(x, 4, self.ComboBoxes[x])
            self.ComboBoxes[x].addItems(ComboItems)
            self.ComboBoxes[x].currentIndexChanged['QString'].connect(partial(self.ComboModif, x))
            self.ComboBoxes[x].setStatusTip(Text)

            ## Ajout de la piste au dico
            MKVDico[x] = [ID, "Track", icone, "unknown", info1, info2, codec]

            ## Envoie des informations dans le tableaux
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem(ID)) # Envoie de l'ID
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem("")) # Texte bidon permettant d'envoyer la checkbox
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
            self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID1"].format(ID)) # StatusTip
            self.ui.mkv_tracks.setItem(x, 2, QTableWidgetItem(QIcon.fromTheme(icone, QIcon(":/img/{}.png".format(icone))), "")) # Envoie de l'icône
            self.ui.mkv_tracks.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
            self.ui.mkv_tracks.item(x, 2).setStatusTip(self.Trad["TrackType"].format(TrackTypeName)) # StatusTip
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1)) # Envoie de l'information
            self.ui.mkv_tracks.item(x, 3).setStatusTip(self.Trad["TrackRename"]) # StatusTip

            ## Sélection de la valeur de la combobox
            self.ComboBoxes[x].setCurrentIndex(self.ComboBoxes[x].findText(str(info2)))

            ## Dans le cas de codec AAC
            if "aac" == codec:
                # Création d'une combobox, remplissage, mise à jour du statustip, connexion, sélection de la valeur et envoie de la combobox dans le tableau
                name = "{}-aac".format(x)
                self.ComboBoxes[name] = QComboBox()
                self.ui.mkv_tracks.setCellWidget(x, 5, self.ComboBoxes[name])
                self.ComboBoxes[name].addItems(['aac', 'aac sbr'])
                self.ComboBoxes[name].setStatusTip(self.Trad["TrackAac"])
                self.ComboBoxes[name].currentIndexChanged['QString'].connect(partial(self.ComboModif, name))
                self.ComboBoxes[name].setCurrentIndex(self.ComboBoxes[name].findText(codec))

            ## Pour les autres audios
            else:
                self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem(codec))
                self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.item(x, 5).setStatusTip(codecInfo)

            # Incrémentation du numéro de ligne
            x += 1


        ### Boucle traitant les chapitrages
        # Renvoie un truc du genre : 0 "num_entries": 15
        for Chapter in JsonMKV["chapters"]:
            ## Mise à jour des variables
            info1 = self.Trad["TrackChapters"]
            info2 = "{} {}".format(Chapter["num_entries"], info1)

            ## Mise à jour du dictionnaire des pistes du fichier MKV
            MKVDico[x] = ["NoID", "Chapters", "x-office-address-book", "document-preview", info1, info2, "Chapters"]

            ## Création du bouton de visualisation
            Button = QPushButton(QIcon.fromTheme("x-office-address-book", QIcon(":/img/x-office-address-book.png")), "")
            Button.setFlat(True)
            Button.clicked.connect(partial(self.TrackView, x))
            Button.setStatusTip(self.Trad["TrackType2"].format(info1))

            ## Envoi des informations dans le tableaux
            self.ui.mkv_tracks.insertRow(x) # Création de ligne
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem("chapters")) # Remplissage des cellules
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem(""))
            self.ui.mkv_tracks.setCellWidget(x, 2, Button) # Envoie du bouton
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1))
            self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2))
            self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem("text"))
            self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID3"].format(info1)) # Envoie des StatusTip
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
            self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            # Incrémentation du numéro de ligne
            x += 1


        ### Boucle traitant les tags
        # Renvoie un truc du genre : 0 "num_entries": 15
        for GlobalTag in JsonMKV["global_tags"]:
            ## Mise à jour des variables
            info1 = self.Trad["TrackTags"]
            info2 = "{} {}".format(GlobalTag["num_entries"], info1)

            ## Mise à jour du dictionnaire des pistes du fichier MKV
            MKVDico[x] = ["NoID", "Global tags", "text-html", "document-preview", info1, info2, "Tags"]

            ## Création du bouton de visualisation
            Button = QPushButton(QIcon.fromTheme("text-html", QIcon(":/img/text-html.png")), "")
            Button.setFlat(True)
            Button.clicked.connect(partial(self.TrackView, x))
            Button.setStatusTip(self.Trad["TrackType2"].format(info1))

            ## Envoi des informations dans le tableaux
            self.ui.mkv_tracks.insertRow(x) # Création de ligne
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem("tags")) # Remplissage des cellules
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem(""))
            self.ui.mkv_tracks.setCellWidget(x, 2, Button) # Envoie du bouton
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1))
            self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2))
            self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem("xml"))
            self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID3"].format(info1)) # Envoie des StatusTip
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
            self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            # Incrémentation du numéro de ligne
            x += 1


        ### Boucle traitant les fichiers joints du fichier MKV
        # Renvoie un truc du genre : 0 "content_type": "text/html", "description": "", "file_name": "index.php"...
        for Attachment in JsonMKV["attachments"]:
            ## Mise à jour des variables
            ID = Attachment["id"]
            Item1 = ID
            info2 = "{} octets".format(Attachment["size"])
            typecodec = Attachment["content_type"]
            typetrack = typecodec.split("/")[0]

            ## Récupération de l'information 1
            if "description" in Attachment and Attachment["description"]:
                info1 = Attachment["description"]

            elif "file_name" in Attachment:
                info1 = Attachment["file_name"]

            else:
                info1 = "No info"

            ## Traitement des codecs
            if "/" in typecodec:
                typetrack = typecodec.split("/")[0]
                codec = typecodec.split("/")[1]

            else:
                typetrack = typecodec
                codec = typecodec

            ## Mise à jour du codec pour plus de lisibilité
            Codecs = {
                "x-truetype-font": "font",
                "vnd.ms-opentype": "font OpenType",
                "x-msdos-program": "application msdos",
                "plain": "text",
                "ogg": "audio", # Il est reconnu en tant qu'application
                "ogm": "audio", # Il est reconnu en tant qu'application
                "x-flac": "flac",
                "x-flv": "flv",
                "x-ms-bmp": "bmp"
                }

            codec = Codecs.get(codec, codec)

            ## Traitement des statustip
            StatusTip1 = self.Trad["TrackID2"].format(ID)
            StatusTip2 = self.Trad["TrackTypeAttachment"].format(typetrack)
            StatusTip3 = self.Trad["TrackAttachment"]

            ## Icône du type de piste
            machin = QMimeDatabase().mimeTypeForName(typecodec)
            icone = QIcon().fromTheme(QMimeType(machin).iconName(), QIcon().fromTheme(QMimeType(machin).genericIconName())).name()

            ## Dans le cas où l'icône n'a pas été déterminée
            if not icone:
                Icones = {
                    "application": "system-run",
                    "image": "image-x-generic",
                    "text": "accessories-text-editor",
                    "media": "applications-multimedia",
                    "video": "applications-multimedia",
                    "audio": "applications-multimedia",
                    "web": "applications-internet"
                    }

                icone = Icones.get(typetrack, "unknown")

            ## Mise à jour du dictionnaire des pistes du fichier MKV
            MKVDico[x] = [ID, "Attachment", icone, "document-preview", info1, info2, codec]

            ## Création du bouton de visualisation
            Button = QPushButton(QIcon.fromTheme(icone, QIcon(":/img/{}.png".format(icone))), "")
            Button.setFlat(True)
            Button.clicked.connect(partial(self.TrackView, x))
            Button.setStatusTip(StatusTip2)

            ## Envoi des informations dans le tableau
            self.ui.mkv_tracks.insertRow(x) # Création de ligne
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem(Item1)) # Remplissage des cellules
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem(""))
            self.ui.mkv_tracks.setCellWidget(x, 2, Button) # Envoi du bouton
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1))
            self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2))
            self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem(codec))
            self.ui.mkv_tracks.item(x, 1).setStatusTip(StatusTip1) # Envoi des StatusTip
            self.ui.mkv_tracks.item(x, 3).setStatusTip(StatusTip3)
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoi de la checkbox
            self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            ## Incrémentation du numéro de ligne
            x += 1

        ### Retours d'information, déblocage, curseur normal
        if Configs.value("DebugMode"):
            self.SetInfo(self.Trad["WorkMerge"], "800080", True, True)

        TempValues.setValue("SuperBlockTemp", False) # Variable servant à bloquer les signaux du tableau (impossible autrement)
        self.setCursor(Qt.ArrowCursor)


    #========================================================================
    def TrackView(self, x):
        """Fonction d'affichage des fichiers joints."""
        ### Vérification de la présence de mkvmerge
        if not self.SoftIsExec("MKVExtract"):
            return

        ### Dans le cas d'un fichier de chapitrage
        if MKVDico[x][1] == "Chapters":
            ## Fichier de sortie
            ChaptersFileStr = TempValues.value("FolderTemp") + "/chapters.txt"
            TempValues.setValue("ChaptersFile", ChaptersFileStr)

            ## str => QFile
            ChaptersFile = QFile(ChaptersFileStr)

            ## Écriture du fichier
            ChaptersFile.open(QFile.WriteOnly)

            for line in self.LittleProcess(Configs.value("Location/MKVExtract"), ['chapters', Configs.value("InputFile"), '-s']):
                ChaptersFile.write((line + '\n').encode())

            ChaptersFile.close()

            ## Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(ChaptersFileStr))


        ### Dans le cas de global tags
        elif MKVDico[x][1] == "Global tags":
            ## Fichier de sortie
            TagsFileStr = TempValues.value("TagsFile") + "/tags.xml"
            TempValues.setValue("TagsFile", TagsFileStr)

            ## str => QFile
            TagsFile = QFile(TagsFileStr)

            ## Écriture du fichier
            TagsFile.open(QFile.WriteOnly)

            for line in self.LittleProcess(Configs.value("Location/MKVExtract"), ['tags', Configs.value("InputFile")]):
                TagsFile.write((line + '\n').encode())

            TagsFile.close()

            ## Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(TagsFileStr))


        ### Dans le cas de fichier joint
        elif MKVDico[x][1] == "Attachment":
            ## Test de la place disponible avant d'extraire
            FileSize = int(MKVDico[x][5].split(" ")[0])
            FreeSpaceDisk = QStorageInfo(TempValues.value("FolderTemp")).bytesAvailable()

            ## Test de la place restante
            if self.CheckSize("FolderTemp", FileSize, FreeSpaceDisk, self.Trad["ErrorSizeAttachement"]):
                return

            ## Fichier de sortie
            Fichier = TempValues.value("FolderTemp") + '/attachement_{0[0]}_{0[4]}'.format(MKVDico[x])

            ## Extraction du fichier
            reply = self.LittleProcess(Configs.value("Location/MKVExtract"), ['attachments', Configs.value("InputFile"), "{}:{}".format(MKVDico[x][0], Fichier)])

            ## Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(Fichier))


    #========================================================================
    def TrackModif(self, info):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'édition des textes."""
        ### Blocage de la fonction pendant le chargement des pistes
        if TempValues.value("SuperBlockTemp"):
            return

        ### Récupération de la cellule modifiée
        x = self.ui.mkv_tracks.row(info)
        y = self.ui.mkv_tracks.column(info)

        ### Dans le cas de la modification d'une checkbox
        if y == 1:
            ## Mise au propre du tableau
            MKVDicoSelect.clear() # Mise au propre du dictionnaire

            for x in range(self.ui.mkv_tracks.rowCount()): # Boucle traitant toutes les lignes du tableau
                if self.ui.mkv_tracks.item(x, 1).checkState(): # Teste si la ligne est cochée
                    MKVDicoSelect[x] = MKVDico[x] # mise à jour de la liste des pistes cochées

            ## Liste des widgets à possiblement (dé)bloquer
            Widgets = {
                self.ui.mkv_execute: False,
                self.mkv_execute_2: False,
                self.ui.option_audio: False,
                self.ui.option_subtitles: False,
                self.ui.option_reencapsulate: False,
                Sup2Sub[1]: False,
                Sup2Sub[2]: False,
                Sup2Sub[3]: False,
                Sub2Srt[1]: False,
                Sub2Srt[2]: False
                }

            # Déblocage des options si besoin
            if MKVDicoSelect and Configs.value("OutputFolder"):
                # Déblocages des boutons
                Widgets[self.ui.mkv_execute] = True
                Widgets[self.mkv_execute_2] = True
                Widgets[self.ui.option_reencapsulate] = True

                # Boucle sur la liste des lignes
                for valeurs in MKVDicoSelect.values():
                    # Recherche la valeur audio dans les sous listes
                    if valeurs[2] == "audio-x-generic" and self.SoftIsExec("FFMpeg"):
                        Widgets[self.ui.option_audio] = True

                    # Recherche la valeur vobsub dans les sous listes
                    elif valeurs[-1] == "sub" and self.SoftIsExec("Qtesseract5"):
                        Widgets[self.ui.option_subtitles] = True
                        Widgets[Sub2Srt[1]] = True
                        Widgets[Sub2Srt[2]] = True

                    # Recherche la valeur sup/pgs dans les sous listes
                    elif valeurs[-1] in ("sup", "pgs") and self.SoftIsExec("BDSup2Sub|FFMpeg"):
                        Widgets[self.ui.option_subtitles] = True

                        if self.SoftIsExec("BDSup2Sub"):
                            Widgets[Sup2Sub[2]] = True
                            Widgets[Sup2Sub[3]] = True

                        if self.SoftIsExec("FFMpeg"):
                            Widgets[Sup2Sub[1]] = True

                        # Active la conversion Qtesseract si disponible
                        if (Sup2Sub[2].isChecked() or Sup2Sub[1].isChecked()) and self.SoftIsExec("Qtesseract5"):
                            Widgets[Sub2Srt[1]] = True
                            Widgets[Sub2Srt[2]] = True

                    # Arrêt de la boucle si tout est activé
                    if Widgets[self.ui.option_subtitles] and Widgets[Sub2Srt[1]] and (Widgets[Sup2Sub[1]] or Widgets[Sup2Sub[2]]):
                        break

            # (Dé)blocage des widgets
            for Widget, State in Widgets.items():
                Widget.setEnabled(State)

                # Décoche les boutons s'ils sont grisés
                if Widget not in [self.ui.mkv_execute, self.mkv_execute_2] and not State:
                    Widget.setChecked(False)


        ### Dans le cas d'une modification de texte
        else:
            ## Mise à jour du texte dans le dico des pistes
            MKVDico[x][y] = self.ui.mkv_tracks.item(x, y).text()

            ## Mise à jour du texte dans le dico des pistes sélectionnées si la ligne est sélectionnée
            if self.ui.mkv_tracks.item(x, 1).checkState():
                MKVDicoSelect[x][y] = MKVDico[x][y]


    #========================================================================
    def TrackSelectAll(self, Value):
        """Fonction (dé)cochant toutes les pistes avec un clic sur le header."""
        ### Ne traite que la colonne des coches soit la colonne num 1
        if Value == 1:
            ## Dans le cas où il faut tout cocher
            if not TempValues.value("AllTracks"):
                TempValues.setValue("AllTracks", True)

                # Boucle traitant toutes les lignes du tableau
                for x in range(self.ui.mkv_tracks.rowCount()):
                    self.ui.mkv_tracks.item(x, 1).setCheckState(2)

            ## Dans le cas où il faut tout décocher
            else:
                TempValues.setValue("AllTracks", False)

                # Boucle traitant toutes les lignes du tableau
                for x in range(self.ui.mkv_tracks.rowCount()):
                    self.ui.mkv_tracks.item(x, 1).setCheckState(0)


    #========================================================================
    def CommandCreate(self):
        """Fonction créant toutes les commandes : mkvextractor, ffmpeg, mkvmerge..."""
        ### Test de la place restante
        FileSize = QFileInfo(Configs.value("InputFile")).size()
        FreeSpaceDisk = QStorageInfo(Configs.value("OutputFolder")).bytesAvailable()

        if self.CheckSize("OutputFolder", FileSize, FreeSpaceDisk, self.Trad["ErrorSize"]):
            return

        ### Mise au propre et initialisation de variables
        TempFiles.clear() # Fichiers temporaires à effacer
        AllTempFiles.clear() # Fichiers à effacer en cas d'arrêt
        SubConvert = [] # Conversion des sub en srt
        SupConvert = [] # Conversion des sup/pgs en sub
        mkvextract_track = [] # Commande d'extraction des pistes normales
        mkvextract_joint = [] # Commande d'extraction des fichiers joints
        dts_ffmpeg = [] # Commande de conversion DTS vers AC3
        mkvmerge = [] # Commande de réencapsulage
        mkvmerge_files = [Configs.value("InputFile")] # Liste des fichiers nécessaires à mkvmerge
        SubToRemove = [] # Liste pour ne pas ouvrir les idx convertis

        CommandList.clear() # Liste des commandes à exécuter à la suite
            # str : Nom de la commande
            # str : Commande
            # list : Arguments de la commande
            # list : Fichiers dont il faut vérifier l'existence avant le lancement de la commande

        ### Si on veut uniquement ré-encapsuler sans rien d'autre, on affiche un message conseillant d'utiliser MKVToolNix-Gui
        if TempValues.value("Reencapsulate") and not TempValues.value("AudioConvert") and not TempValues.value("SubtitlesConvert") and not TempValues.value("SubtitlesOpen"):
            if not Configs.value("MMGorMEQCheckbox"):
                ## Création de la fenêtre
                UseMMG = QMessageBox(QMessageBox.Question, self.Trad["UseMMGTitle"], self.Trad["UseMMGText"], QMessageBox.Cancel, self, Qt.WindowSystemMenuHint)
                UseMMG.setWindowFlags(Qt.WindowTitleHint | Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.CustomizeWindowHint) # Enlève le bouton de fermeture de la fenêtre

                # Création des widgets à y mettre
                CheckBox = QCheckBox(self.Trad["Convert0"], UseMMG) # Création de la checkbox
                MMG = QPushButton(QIcon.fromTheme("mkvmerge", QIcon(":/img/mkvmerge.png")), "MKVToolNix-Gui", UseMMG) # Création du bouton MKVToolNix-Gui
                MEQ = QPushButton(QIcon.fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")), "MKV Extracor Qt 5", UseMMG) # Création du bouton MKV Extracor Qt

                # Remplissage de la fenêtre
                UseMMG.setCheckBox(CheckBox) # Envoie de la checkbox
                UseMMG.addButton(MMG, QMessageBox.YesRole) # Ajout du bouton
                UseMMG.addButton(MEQ, QMessageBox.NoRole) # Ajout du bouton
                UseMMG.setDefaultButton(MEQ) # Bouton par défaut : MKV Extracor Qt

                # Lancement de la fenêtre
                UseMMG.exec() # Message d'information

                # Mise à jour de la variable
                Configs.setValue("MMGorMEQCheckbox", CheckBox.isChecked())

                # Mise à jour de la variable du logiciel à utiliser
                if UseMMG.buttonRole(UseMMG.clickedButton()) == 5:
                    Configs.setValue("MMGorMEQ", "MMG")

                elif UseMMG.buttonRole(UseMMG.clickedButton()) == 6:
                    Configs.setValue("MMGorMEQ", "MEQ")

                else:
                    return

            # Si on veut utiliser MMG, on arrête là
            if Configs.value("MMGorMEQ") == "MMG":
                self.MKVMergeGui()
                return


        ### Boucle traitant les pistes une à une
        for Select in MKVDicoSelect.values():
            # Select[0] : ID
            # Select[1] : Type de piste : Track, Attachment, Chapters, Global
            # Select[2] : Icône
            # Select[3] : Icône de visualisation
            # Select[4] : Nom de la piste
            # Select[5] : Info : fps, langue...
            # Select[6] : Info : codec

            ## Traitement des pistes vidéos, mise à jour de commandes
            if Select[2] == "video-x-generic":
                # Ajout du fichier à la liste
                File = "{0}/{1[0]}_video_{1[4]}.mkv".format(Configs.value("OutputFolder"), Select)
                AllTempFiles.append(File)
                mkvmerge_files.append(File)

                # Code d'extraction des pistes
                mkvextract_track.append('{0[0]}:{1}'.format(Select, File))

                # Code d'encapsulage
                mkvmerge.extend(["--track-name", "0:{0[4]}".format(Select), "--default-duration", "0:{0[5]}".format(Select), "--compression", "0:none", File])


            ## Traitement des pistes audios
            elif Select[2] == "audio-x-generic":
                # Ajout du fichier à la liste
                File = "{0}/{1[0]}_audio_{1[4]}.{2}".format(Configs.value("OutputFolder"), Select, Select[6])
                AllTempFiles.append(File)

                # En cas de modification audio
                if TempValues.value("AudioConvert") and (
                    TempValues.value("AudioBoost") or
                    TempValues.value("AudioStereo") or
                    TempValues.value("AudioQuality") or
                    Configs.value("AudioToAc3")):

                    # Indique la piste audio
                    dts_ffmpeg.extend(['-vn', '-map', '0:{}'.format(Select[0])])

                    # En cas de boost
                    if TempValues.value("AudioBoost"):
                        dts_ffmpeg.extend(['-af', 'volume={}'.format(TempValues.value("AudioBoost"))])

                    # En cas de passage en stéréo
                    if TempValues.value("AudioStereo"):
                        dts_ffmpeg.extend(['-ac', '2'])

                    # En cas de modification de qualité
                    if TempValues.value("AudioQuality"):
                        dts_ffmpeg.extend(['-ab', '{0}k'.format(TempValues.value("AudioQuality", 128))])

                    # En cas de passage en ac3
                    if Configs.value("AudioToAc3"):
                        File = "{0}/{1[0]}_audio_{1[4]}.ac3".format(Configs.value("OutputFolder"), Select)
                        dts_ffmpeg.extend(['-f', 'ac3'])

                    # Fichier de sortie
                    dts_ffmpeg.append(File)

                    # Ajout du fichier de sortie dans la liste
                    AllTempFiles.append(File)
                    mkvmerge_files.append(File)

                # Si pas de modification audio
                else:
                    # Code d'extraction des pistes
                    mkvmerge_files.append(File)
                    mkvextract_track.append('{0[0]}:{1}'.format(Select, File))


                # Code d'encapsulage
                Temp = ["--track-name", "0:{0[4]}".format(Select), "--language", "0:{0[5]}".format(Select), "--compression", "0:none"]

                # Dans le cas où il faut ré-encapsuler des fichiers AAC, il faut préciser si sbr ou non
                if "aac" in Select[6]:
                    aac_is_sbr = "0:1"

                    if Select[6] == "aac sbr":
                        aac_is_sbr = "0:0"

                    Temp.extend(["--aac-is-sbr", aac_is_sbr])

                Temp.append(File)
                mkvmerge.extend(Temp)


            ## Traitement des pistes sous titres
            elif Select[2] == "text-x-generic":
                # Dans le cas de sous titres de fichiers sub
                if Select[6] == "sub":
                    # Ajout des fichiers à la liste
                    SUB = "{0}/{1[0]}_subtitles_{1[4]}.sub".format(Configs.value("OutputFolder"), Select)
                    IDX = "{0}/{1[0]}_subtitles_{1[4]}.idx".format(Configs.value("OutputFolder"), Select)

                    AllTempFiles.append(SUB)
                    AllTempFiles.append(IDX)

                    # Code d'extraction des pistes
                    mkvextract_track.append('{0[0]}:{1}'.format(Select, IDX))

                    # Dans le cas d'un conversion de sous titres sub => srt
                    if TempValues.value("SubtitlesConvert") and TempValues.value("Sub2Srt"):
                        # Ajout du fichier à la liste
                        SRT = "{0}/{1[0]}_subtitles_{1[4]}.srt".format(Configs.value("OutputFolder"), Select)
                        #TempFiles.append(SRT)
                        AllTempFiles.append(SRT)

                        TempFiles.append(SUB)
                        TempFiles.append(IDX)

                        # Code d'encapsulage
                        mkvmerge_files.append(SRT)
                        mkvmerge.extend(["--track-name", "0:{0[4]}".format(Select), "--language", "0:{0[5]}".format(Select), "--compression", "0:none", SRT])

                        # Différence de nom entre la langue de tesseract et celle de mkvalidator
                        SubConvert.append([Select[0], Select[4], Select[5].replace("fre", "fra")])


                    # Dans le cas ou il n'y a pas de conversion, maj de commande
                    else:
                        # Code d'encapsulage
                        mkvmerge_files.append(SUB)
                        mkvmerge_files.append(IDX)
                        File = "{1}/{0[0]}_subtitles_{0[4]}.idx".format(Select, Configs.value("OutputFolder"))
                        mkvmerge.extend(["--track-name", "0:{0[4]}".format(Select), "--language", "0:{0[5]}".format(Select), "--compression", "0:none", "{1}".format(Select, File)])


                # Dans le cas de sous titres de fichiers sup ou pgs
                elif Select[6] in ("sup", "pgs"):
                    # Ajout du fichier à la liste
                    SUP = "{1}/{0[0]}_subtitles_{0[4]}.{0[6]}".format(Select, Configs.value("OutputFolder"))
                    AllTempFiles.append(SUP)

                    # Code d'extraction des pistes
                    mkvextract_track.append('{0[0]}:{1}'.format(Select, SUP))

                    # Si conversion du sous titre
                    if TempValues.value("SubtitlesConvert") and TempValues.value("Sup2Sub"):
                        TempFiles.append(SUP)

                        # Fichiers de conversion sup => sub
                        SUB = "{0}/{1[0]}_subtitles_{1[4]}.sub".format(Configs.value("OutputFolder"), Select)
                        IDX = "{0}/{1[0]}_subtitles_{1[4]}.idx".format(Configs.value("OutputFolder"), Select)
                        AllTempFiles.append(SUB)
                        AllTempFiles.append(IDX)

                        # Fichier de conversion sub => srt
                        if TempValues.value("Sub2Srt"):
                            SRT = "{0}/{1[0]}_subtitles_{1[4]}.srt".format(Configs.value("OutputFolder"), Select)
                            AllTempFiles.append(SRT)

                            TempFiles.append(SUB)
                            TempFiles.append(IDX)

                            # Code d'encapsulage du srt
                            mkvmerge.extend(["--track-name", "0:{0[4]}".format(Select), "--language", "0:{0[5]}".format(Select), "--compression", "0:none", SRT])
                            mkvmerge_files.append(SRT)

                            # Différence de nom entre la langue de tesseract et celle de mkvalidator
                            SubConvert.append([Select[0], Select[4], Select[5].replace("fre", "fra")])

                        # Si pas de conversion srt
                        else:
                            mkvmerge_files.append(SUB)
                            mkvmerge_files.append(IDX)

                            # Code d'encapsulage
                            mkvmerge.extend(["--track-name", "0:{0[4]}".format(Select), "--language", "0:{0[5]}".format(Select), "--compression", "0:none", IDX])

                        # Liste des sous titres à convertir
                        SupConvert.append([Select[0], Select[4], "{1}/{0[0]}_subtitles_{0[4]}.{0[6]}".format(Select, Configs.value("OutputFolder"))])


                    # Dans le cas ou il n'y a pas de conversion, maj de commande
                    else:
                        # Code d'encapsulage
                        mkvmerge_files.append(SUP)
                        mkvmerge.extend(["--track-name", "0:{0[4]}".format(Select), "--language", "0:{0[5]}".format(Select), "--compression", "0:none", SUP])


                # Dans le cas de sous titres autre que de type sub, maj de commandes
                else:
                    # Ajout du fichier à la liste
                    File = "{1}/{0[0]}_subtitles_{0[4]}.{0[6]}".format(Select, Configs.value("OutputFolder"))
                    AllTempFiles.append(File)

                    # Code d'extraction des pistes
                    mkvmerge_files.append(File)
                    mkvextract_track.append('{0[0]}:{1}'.format(Select, File))

                    # Code d'encapsulage
                    mkvmerge.extend(["--track-name", "0:{0[4]}".format(Select), "--language", "0:{0[5]}".format(Select), "--compression", "0:none", File])


            ## Traitement des pistes chapitrage, maj de commandes
            elif Select[1] == 'Chapters':
                # Ajout du fichier à la liste
                File = "{0}/chapters.txt".format(Configs.value("OutputFolder"))
                AllTempFiles.append(File)
                mkvmerge_files.append(File)

                # Code d'encapsulage
                mkvmerge.extend(["--chapters", File])

                # Variable temporaire
                TempValues.setValue("ChaptersFile", File)

                # Suppression du fichier s'il existe déjà
                if QFileInfo(TempValues.value("ChaptersFile")).exists():
                    QFile(TempValues.value("ChaptersFile")).remove()

                # Ajout de la commande d'extraction du chapitrage
                CommandList.append(["MKVExtract Chapters", Configs.value("Location/MKVExtract"), ["chapters", Configs.value("InputFile"), "-s"], [Configs.value("InputFile")]])


            ## Traitement des pistes de tags, maj de commandes
            elif Select[1] == 'Global tags':
                # Ajout du fichier à la liste
                File = "{0}/tags.xml".format(Configs.value("OutputFolder"))
                AllTempFiles.append(File)
                mkvmerge_files.append(File)

                # Code d'encapsulage
                mkvmerge.extend(["--global-tags", File])

                # Variable temporaire
                TempValues.setValue("TagsFile", File)

                # Suppression du fichier s'il existe déjà
                if QFileInfo(TempValues.value("TagsFile")).exists():
                    QFile(TempValues.value("TagsFile")).remove()

                # Ajout de la commande d'extraction des tags
                CommandList.append(["MKVExtract Tags", Configs.value("Location/MKVExtract"), ["tags", Configs.value("InputFile")], [Configs.value("InputFile")]])


            ## Traitement des pistes jointes, maj de commandes
            else:
                # Ajout du fichier à la liste
                File = "{0}/{1[0]}_{1[4]}".format(Configs.value("OutputFolder"), Select)
                AllTempFiles.append(File)
                mkvmerge_files.append(File)

                # Code d'extraction des fichiers joints
                mkvextract_joint.append('{0[0]}:{1}'.format(Select, File))

                # Code d'encapsulage
                mkvmerge.extend(["--attachment-name", Select[4], "--attach-file", File])


        ### Ajout de la commande mkvextract_track à la liste des commandes à exécuter
        if mkvextract_track:
            # Finalisation de la commande d'extraction des pistes
            mkvextract_track.insert(0, Configs.value("InputFile"))
            mkvextract_track.insert(0, "tracks")

            # Ajout de la commande d'extraction des pistes à la liste des commandes
            CommandList.append(["MKVExtract Tracks", Configs.value("Location/MKVExtract"), mkvextract_track, [Configs.value("InputFile")]])


        ### Ajout de la commande mkvextract_joint à la liste des commandes à exécuter
        if mkvextract_joint:
            # Finalisation de la commande d'extraction des fichiers joints
            mkvextract_joint.insert(0, Configs.value("InputFile"))
            mkvextract_joint.insert(0, "attachments")

            # Ajout de la commande d'extraction des fichiers joints à la liste des commandes
            CommandList.append(["MKVExtract Attachments", Configs.value("Location/MKVExtract"), mkvextract_joint, [Configs.value("InputFile")]])


        ### Ajout de la commande dts_ffmpeg à la liste des commandes à exécuter
        if dts_ffmpeg:
            # Finalisation de la commande de conversion audio
            if TempValues.value("FFMpeg"):
                ffconv = Configs.value("Location/FFMpeg")
                ffconvName = "FFMpeg"

            else:
                ffconv = Configs.value("Location/AvConv")
                ffconvName = "AvConv"

            dts_ffmpeg.insert(0, '-y')
            dts_ffmpeg.insert(0, Configs.value("InputFile"))
            dts_ffmpeg.insert(0, '-i')

            # Ajout de la commande de conversion audio à la liste des commandes
            CommandList.append([ffconvName, ffconv, dts_ffmpeg, [Configs.value("InputFile")]])


        ### Ajout des commandes de conversion des vobsub en srt
        if TempValues.value("SubtitlesConvert"):

            ## Pour chaque pgs/sup à convertir en sub
            for SupInfo in SupConvert:
                # Liste des fichiers sous titres
                IDX = '{}/{}_subtitles_{}.idx'.format(Configs.value("OutputFolder"), SupInfo[0], SupInfo[1])

                # Ajout de la commande de conversion des sous titres sup en sub à la liste des commandes
                if TempValues.value("Sup2Sub") == 3:
                    CommandList.append(["Message", "Information", [self.Trad["BDSup2SubTitle"], self.Trad["BDSup2SubInfoText"].format(IDX), IDX], []])
                    CommandList.append(["BDSup2Sub", "java", ["-jar", Configs.value("Location/BDSup2Sub"), SupInfo[2]], [SupInfo[2]]])

                elif TempValues.value("Sup2Sub") == 2:
                    CommandList.append(["BDSup2Sub", "java", ["-jar", Configs.value("Location/BDSup2Sub"), "-o", IDX, SupInfo[2]], [SupInfo[2]]])

                elif TempValues.value("Sup2Sub") == 1:
                    # Fichiers temporaires
                    MKS = '{}/{}_subtitles_{}.mks'.format(Configs.value("OutputFolder"), SupInfo[0], SupInfo[1])
                    SUB = '{}/{}_subtitles_{}.sub'.format(Configs.value("OutputFolder"), SupInfo[0], SupInfo[1])

                    AllTempFiles.append(MKS)
                    AllTempFiles.append(SUB)
                    TempFiles.append(MKS)

                    # Commande FFMpeg pour ne conserver que le sub dans un mks
                    CommandList.append(["FFMpeg", Configs.value("Location/FFMpeg"), ["-i", SupInfo[2], "-map", "0:s:0", "-c:s", "dvdsub", "-f", "matroska", MKS], [SupInfo[2]]])

                    # Commande mkvextract pour extraire le sub du mks
                    CommandList.append(["MKVExtract", Configs.value("Location/MKVExtract"), [MKS, "tracks", "0:{}".format(SUB)], [MKS]])


            ## Pour chaque sub à convertir en srt
            for SubInfo in SubConvert:
                # Liste des fichiers sous titres
                IDX = '{}/{}_subtitles_{}.idx'.format(Configs.value("OutputFolder"), SubInfo[0], SubInfo[1])
                SRT = '{}/{}_subtitles_{}.srt'.format(Configs.value("OutputFolder"), SubInfo[0], SubInfo[1])
                SubToRemove.append(IDX)

                # Finalisation de la commande Qtesseract5
                g = 1

                if TempValues.value("Sub2Srt") == 2:
                    CommandList.append(["Message", "Information", [self.Trad["QtesseractTitle"], self.Trad["QtesseractInfoText"].format(SRT), SRT], []])
                    g = 2

                # Ajout de la commande de conversion de conversion des sous titres sub en srt à la liste des commandes
                CommandList.append(["Qtesseract5", Configs.value("Location/Qtesseract5"), ["-g {}".format(g), "-v 1", "-r", "-c 0", "-w", "-r", "-t {}".format(QThread.idealThreadCount()), "-l", SubInfo[2], IDX, SRT], [IDX]])


        ### Ajout de la commande mkvmerge à la liste des commandes à exécuter
        if TempValues.value("Reencapsulate"):
            InputFileName = QFileInfo(Configs.value("InputFile")).fileName()

            ## Si l'option de renommage automatique n'est pas utilisée
            if not Configs.value("RemuxRename"):
                # Fenêtre de sélection de sortie du fichier mkv
                CheckBox = QCheckBox(self.Trad["RemuxRenameCheckBox"])

                FileDialogCustom = QFileDialogCustom(self,
                                                     self.Trad["RemuxRenameTitle"],
                                                     Configs.value("OutputFolder"),
                                                     "{}(*.mka *.mks *.mkv *.mk3d *.webm *.webmv *.webma)".format(self.Trad["MatroskaFiles"]))

                # Choix du fichier de destination
                FileTemp = FileDialogCustom.createWindow("File",
                                                         "Save",
                                                         CheckBox,
                                                         Qt.Tool,
                                                         "MEG_{}".format(InputFileName),
                                                         AlreadyExistsTest=Configs.value("AlreadyExistsTest", False),
                                                         Language=Configs.value("Language"),
                                                         App=app)

                # Si c'est vide, on utilise .
                if not FileTemp:
                    FileTemp = "."

                TempValues.setValue("OutputFile", FileTemp)
                Configs.setValue("RemuxRename", CheckBox.isChecked())

                # Mise à jour de la variable
                Configs.setValue("RemuxRename", CheckBox.isChecked())

                # Arrêt de la fonction si aucun fichier n'est choisi
                if TempValues.value("OutputFile") == ".":
                    return

            else:
                File = "{0}/MEG_{1}".format(Configs.value("OutputFolder"), InputFileName)
                TempValues.setValue("OutputFile", File)

            ## Ajout des fichiers temporaires à la liste
            for Item in mkvmerge_files:
                if Item != Configs.value("InputFile"):
                    TempFiles.append(Item)

            ## Ajout du fichier mkv à la liste des fichiers
            AllTempFiles.append(TempValues.value("OutputFile"))

            ## Dans le cas où il faut ouvrir les fichiers srt avant leur encapsulage
            if TempValues.value("SubtitlesOpen"):
                SubtitlesFiles.clear()

                # Ajout des fichiers sous titres
                for Item in mkvmerge_files:
                    if QFileInfo(Item).suffix().lower() in ("srt", "ssa", "ass", "idx"):
                        SubtitlesFiles.append(Item)

                # Suppression des fichiers idx qui ont été convertis
                if SubToRemove:
                    for Item in SubToRemove:
                        SubtitlesFiles.remove(Item)

                # Echo bidon pour être sûr que la commande se termine bien
                if SubtitlesFiles:
                    CommandList.append(["Open Subtitles", "echo", [], []])

            ## Récupération du titre du fichier dans le cas où il faut réencapsuler,
            TempValues.setValue("TitleFile", self.ui.mkv_title.text())

            ## Si le titre est vide, il plante l'encapsulage
            if TempValues.value("TitleFile"):
                mkvmerge.insert(0, TempValues.value("TitleFile"))
                mkvmerge.insert(0, "--title")

            # Finalisation de la commande d'encapsulage
            mkvmerge.insert(0, TempValues.value("OutputFile"))
            mkvmerge.insert(0, "-o")

            # Ajout de la commande d'encapsulage à la liste des commandes
            CommandList.append(["MKVMerge", Configs.value("Location/MKVMerge"), mkvmerge, mkvmerge_files])


        ### Modifications graphiques
        self.WorkInProgress(True) # Blocage des widgets

        ### Code à exécuter
        TempValues.setValue("Command", CommandList.pop(0)) # Récupération de la 1ere commande

        ### Envoie de textes
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1] + ' ' + ' '.join(TempValues.value("Command")[2]))) # Envoie d'informations

        ### Lancement de la commande
        self.WorkStart()


    #========================================================================
    def WorkStart(self):
        """Fonction vérifiant la présence des fichiers nécessaires au bon lancement de la commande."""
        ### Si des fichiers sont nécessaires
        if TempValues.value("Command")[2]:
            FilesMissing = []

            # Teste chaque fichier
            for File in TempValues.value("Command")[3]:
                if not QFile(File).exists():
                    FilesMissing.append(File)

            # S'il manque des fichiers
            if FilesMissing:
                QMessageBox.critical(self, self.Trad["WorkFileCheckTitle"], self.Trad["WorkFileCheckText"].format("\n - ".join(FilesMissing)))

                self.SetInfo(self.Trad["WorkFileCheckTitle"] + "\n" + self.Trad["WorkFileCheckText"].format("\n - ".join(FilesMissing)), "FF0000", True) # Erreur pendant le travail

                self.WorkStop("Error")
                return

        ### Vérification de la présence de mkvmerge et mkvextract
        if not self.SoftIsExec("MKVMerge") or not self.SoftIsExec("MKVExtract"):
            return

        ### Si tout est OK, on lance la commande
        self.process.start(TempValues.value("Command")[1], TempValues.value("Command")[2])


    #========================================================================
    def WorkInProgress(self, value):
        """Fonction de modifications graphiques en fonction d'un travail en cours ou non."""
        ### Dans le cas d'un lancement de travail
        if value:
            ## Modifications graphiques
            self.setCursor(Qt.WaitCursor) # Curseur de chargement
            self.ui.mkv_execute.hide() # Cache le bouton exécuter
            self.mkv_execute_2.setEnabled(False) # Grise le bouton exécuter
            self.ui.mkv_stop.show() # Affiche le bouton arrêter

            # Affiche le bouton pause si l'option de cache auto est inactive ou si elle est active mais que psutil est présent
            if not Configs.value("HideOptions") or (Configs.value("HideOptions") and 'psutil' in globals()):
                self.ui.mkv_pause.show()

            for widget in (self.ui.menubar, self.ui.tracks_bloc):
                widget.setEnabled(False)  # Blocage de widget


        ### Dans le cas où le travail vient de se terminer (bien ou mal)
        else:
            ## Modifications graphiques
            self.ui.mkv_execute.show() # Affiche le bouton exécuter
            self.ui.mkv_stop.hide() # Cache le bouton arrêter
            self.ui.mkv_pause.hide() # Cache le bouton pause

            if TempValues.value("MKVLoaded") and MKVDicoSelect:
                self.mkv_execute_2.setEnabled(True) # Dégrise le bouton exécuter

            if self.ui.progressBar.format() != "%p %":
                self.ui.progressBar.setFormat("%p %") # Réinitialisation du bon formatage de la barre de progression

            if self.ui.progressBar.maximum() != 100:
                self.ui.progressBar.setMaximum(100) # Réinitialisation de la valeur maximale de la barre de progression

            if self.ui.stackedMiddle.currentIndex() != 0:
                self.ui.stackedMiddle.setCurrentIndex(0) # Ré-affiche le tableau des pistes si ce n'est plus lui qui est affiché

            for widget in (self.ui.menubar, self.ui.tracks_bloc):
                widget.setEnabled(True) # Blocage de widget

            self.setCursor(Qt.ArrowCursor) # Curseur normal


    #========================================================================
    def WorkReply(self):
        """Fonction recevant tous les retours du travail en cours."""
        ### Récupération du retour (les 2 sorties sont sur la standard)
        data = self.process.readAllStandardOutput()

        ### Converti les data en textes et les traite
        for line in bytes(data).decode('utf-8').splitlines():
            #TempValues
            #TempValues.value("Command")[0]
            print("TempValues : ", TempValues.value("Command"))

            progression = 0
            debugLine = ""

            ## Passe la boucle si le retour est vide
            if line == "":
                continue



            ## Dans le cas d'un encapsulation
            elif TempValues.value("Command")[0] == "MKVMerge":
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%":
                    progression = int(line.split(": ")[1].strip()[0:-1])
                    debugLine = line

            ## Dans le cas d'une conversion
            elif TempValues.value("Command")[0] == "FileToMKV":
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%":
                    progression = int(line.split(": ")[1].strip()[0:-1])
                    debugLine = line

            elif TempValues.value("Command")[0] == "MKVExtract Tags":
                TagsFile = QFile(TempValues.value("TagsFile"))
                TagsFile.open(QFile.Append)
                TagsFile.write((line + '\n').encode())
                TagsFile.close()

                line = ""

            elif TempValues.value("Command")[0] == "MKVExtract Chapters":
                ChaptersFile = QFile(TempValues.value("ChaptersFile"))
                ChaptersFile.open(QFile.Append)
                ChaptersFile.write((line + '\n').encode())
                ChaptersFile.close()

                line = ""

            ## MKVExtract renvoie une progression. Les fichiers joints ne renvoient rien.
            elif "MKVExtract" in TempValues.value("Command")[0]:
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%":
                    progression = int(line.split(": ")[1].strip()[0:-1])
                    debugLine = line

            ## MKValidator ne renvoie pas de pourcentage mais des infos ou des points, on vire les . qui indiquent un travail en cours
            elif TempValues.value("Command")[0] == "MKValidator":
                line = line.strip().replace('.', '')

            ## MKClean renvoie une progression et des infos, on ne traite que les pourcentages
            elif TempValues.value("Command")[0] == "MKClean":
                if line[-1] == "%":
                    progression = int(line.split(": ")[1].strip()[0:-1])
                    debugLine = line

            ## FFMpeg ne renvoie pas de pourcentage mais la durée de vidéo encodée en autre
            elif TempValues.value("Command")[0].lower() in ["ffmpeg", "avconv"]:
                if "time=" in line and TempValues.contains("DurationFile"):
                    # Pour les versions renvoyant : 00:00:00
                    try:
                        value = line.split("=")[2].strip().split(".")[0].split(":")
                        value2 = timedelta(hours=int(value[0]), minutes=int(value[1]), seconds=int(value[2])).seconds

                    # Pour les versions renvoyant : 00000 secondes
                    except:
                        value = "caca"
                        value2 = line.split("=")[2].strip().split(".")[0]

                    # Pourcentage maison se basant sur la durée du fichier
                    progression = int((value2 * 100) / TempValues.value("DurationFile"))
                    debugLine = line

            ## Qtesseract5
            elif TempValues.value("Command")[0] == "Qtesseract5":
                if "Temporary folder:" in line:
                    TempValues.setValue("Qtesseract5Folder", line.split(": ")[1])

                try:
                    progression = int((int(line.split("/")[0]) / int(line.split("/")[1])) * 100)
                    debugLine = line

                except:
                    pass

            ## BDSup2Sub
            elif TempValues.value("Command")[0] == "BDSup2Sub":
                # Progression
                if "Decoding frame" in line:
                    try:
                        values = line.split(" ")[2].split("/")
                        progression = int((int(values[0]) / int(values[1])) * 100)
                        debugLine = line

                    except:
                        pass

                # Cache ces infos
                elif "#>" in line:
                    debugLine = line
                    line = ""


            ## Affichage du texte ou de la progression si c'est une nouvelle valeur
            if line and line != TempValues.value("WorkOldLine"): # Comparaison anti doublon
                TempValues.setValue("WorkOldLine", line) # Mise à jour de la variable anti doublon

                # Mode debug
                if Configs.value("DebugMode") and debugLine:
                    self.SetInfo(debugLine)

                # Envoie du pourcentage à la barre de progression si c'est un nombre
                if isinstance(progression, int):
                    self.ui.progressBar.setValue(progression)

                # Envoie de l'info à la boite de texte si c'est du texte
                else:
                    # On ajoute le texte dans une variable en cas de conversion (utile pour le ressortir dans une fenêtre)
                    if TempValues.value("Command")[0] == "FileToMKV":
                        WarningReply.append(line)

                    self.SetInfo(line)


    #========================================================================
    def WorkFinished(self):
        """Fonction appelée à la fin du travail, que ce soit une fin normale ou une annulation."""
        # TempValues.value("Command")[0] : Nom de la commande
        # TempValues.value("Command")[1] : Commande à exécuter
        # TempValues.value("Command")[2] : Arguments de la commande

        ### Si le travail est annulé (via le bouton stop ou via la fermeture du logiciel) ou a renvoyée une erreur, mkvmerge renvoie 1 s'il y a des warnings
        if (TempValues.value("Command")[0] == "FileToMKV" and self.process.exitCode() == 2) or (self.process.exitCode() != 0 and TempValues.value("Command")[0] != "FileToMKV"):
            ## Arrêt du travail
            if TempValues.value("Command")[0] == "Qtesseract5":
                self.WorkStop("SrtError")

            else:
                self.WorkStop("Error")

            return


        ### Traitement différent en fonction de la commande, rien de particulier pour MKValidator, MKClean, FFMpeg
        if TempValues.value("Command")[0] == "Open Subtitles":
            # Boucle ouvrant tous les fichiers srt d'un coup
            for Item in SubtitlesFiles:
                QDesktopServices.openUrl(QUrl.fromLocalFile(Item))


        ### Indication de fin de pack de commande
        else:
            # Travail terminé
            self.SetInfo(self.Trad["WorkFinished"].format(TempValues.value("Command")[0]), "800080", True)

            # Mise à 100% de la barre de progression pour signaler la fin ok
            self.ui.progressBar.setValue(100)

            if Configs.value("SysTray"):
                self.SysTrayIcon.showMessage(self.Trad["SysTrayFinishTitle"], self.Trad["SysTrayFinishText"].format(TempValues.value("Command")[0], QSystemTrayIcon.Information, 3000))


        ### Lancement de l'ouverture du fichier MKV, ici pour un soucis esthétique du texte affiché
        # Dans le cas d'une conversion
        if TempValues.value("Command")[0] == "FileToMKV":
            ## Si mkvmerge a renvoyé un warning, on l'indique
            if self.process.exitCode() == 1 and not Configs.value("ConfirmWarning"):
                # Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, self.Trad["Convert3"], self.Trad["Convert4"], QMessageBox.NoButton, self)
                CheckBox = QCheckBox(self.Trad["Convert5"])
                dialog.setCheckBox(CheckBox)
                dialog.setStandardButtons(QMessageBox.Ok)
                dialog.setDefaultButton(QMessageBox.Ok)
                dialog.setDetailedText("\n".join(WarningReply))
                dialog.exec()

                # Mise en mémoire de la case à cocher
                Configs.setValue("ConfirmWarning", CheckBox.isChecked())

            ## Lancement de la fonction d'ouverture du fichier MKV créé dans le soft
            self.InputFile(AllTempFiles[-1])


        ### Lors de l'ouverture des sous-titres avant réencapsulation, on bloque ici
        if TempValues.value("Command")[0] == "Open Subtitles":
            # Création d'une fenêtre de confirmation de reprise
            ChoiceBox = QMessageBox(QMessageBox.NoIcon, self.Trad["WaitWinTitle"], self.Trad["WaitWinText"], QMessageBox.NoButton, self, Qt.WindowSystemMenuHint)
            Button1 = QPushButton(QIcon.fromTheme("dialog-ok", QIcon(":/img/dialog-ok.png")), self.Trad["WaitWinButton1"], ChoiceBox)
            Button2 = QPushButton(QIcon.fromTheme("process-stop", QIcon(":/img/process-stop.png")), self.Trad["WaitWinButton2"], ChoiceBox)
            ChoiceBox.addButton(Button1, QMessageBox.AcceptRole)
            ChoiceBox.addButton(Button2, QMessageBox.RejectRole)
            ChoiceBox.setDefaultButton(QMessageBox.Ok)
            ChoiceBox.setIconPixmap(QPixmap(QIcon().fromTheme("media-playback-pause", QIcon(":/img/media-playback-pause.png")).pixmap(64)))
            Choice = ChoiceBox.exec()

            # Arrêt du travail
            if Choice == 1:
                self.WorkStop("Stop")
                return


        ### S'il reste des commandes, exécution de la commande suivante
        if CommandList:
            ## Récupération de la commande suivante à exécuter
            TempValues.setValue("Command", CommandList.pop(0))

            ## Traitement des boites de messages
            Message = ""

            # N'affiche les messages que si le fichier test est réutilisé par la suite
            if TempValues.value("Command")[0] == "Message":
                # Le try permet de sortir de toutes les boucles en une fois
                class Found(Exception): pass

                try:
                    for Command in CommandList:
                        for File in Command[3]:
                            # Le fichier est retrouvé dans un paramètre de commande par la suite
                            if TempValues.value("Command")[2][2] == File:
                                # Message d'information
                                if TempValues.value("Command")[1] == "Information":
                                    Message = TempValues.value("Command")[2][0] + " : " + TempValues.value("Command")[2][1]
                                    QMessageBox.information(self, TempValues.value("Command")[2][0], TempValues.value("Command")[2][1])

                                raise Found

                except Found:
                    pass

                # Si c'était la dernière commande
                if not CommandList:
                    self.WorkFinishedCompletly()
                    return

                # Récupération de la commande suivante à exécuter
                TempValues.setValue("Command", CommandList.pop(0))


            ## Mise à 0% de la barre de progression pour signaler le début du travail
            self.ui.progressBar.setValue(0)

            ## Messages d'info
            if TempValues.value("Command")[0] != "Open Subtitles":
                self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True)

            if TempValues.value("Command")[1] != "echo":
                self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1] + ' ' + ' '.join(TempValues.value("Command")[2])))

            if Message:
                self.SetInfo(Message)

            ## Commande suivante
            self.WorkStart()


        ### Si c'était la dernière commande
        else:
            self.WorkFinishedCompletly()


    #========================================================================
    def WorkFinishedCompletly(self):
        """Appelée lorsqu'il n'y a plus aucune commande à exécuter."""
        ### Si l'option de suppression des fichiers temporaire est activée
        if Configs.value("DelTempFiles"):
            ## Suppression des fichiers temporaires
            self.RemoveTempFiles()

        ### Remise en état des widgets
        self.WorkInProgress(False)

        ### Envoi de l'information au systray
        if Configs.value("SysTray"):
            self.SysTrayIcon.showMessage(self.Trad["SysTrayFinishTitle"], self.Trad["SysTrayTotalFinishText"], QSystemTrayIcon.Information, 3000)


    #========================================================================
    def WorkPause(self):
        """Fonction de mise en pause du travail en cours."""
        ### PID du processus en cours
        PID = self.process.processId()

        ### Si aucun PID, c'est qu'il n'y a pas de processus
        if PID <= 0:
            return

        ### Chargement du PID
        try:
            Process = psutil.Process(PID)
        except:
            return

        ### Si le processus est en pause
        if Process.status() == 'stopped':
            ## Reprise
            Process.resume()

            ## Bouton pose
            Icon = QIcon.fromTheme("media-playback-pause", QIcon(":/img/media-playback-pause.png"))
            self.ui.mkv_pause.setIcon(Icon)
            self.ui.mkv_pause.setText(self.Trad["PauseText"])
            self.ui.mkv_pause.setStatusTip(self.Trad["PauseStatusTip"])

        ### S'il est en cours
        else:
            ## Mise en pause
            Process.suspend()

            ## Bouton reprise
            Icon = QIcon.fromTheme("media-playback-start", QIcon(":/img/media-playback-start.png"))
            self.ui.mkv_pause.setIcon(Icon)
            self.ui.mkv_pause.setText(self.Trad["ResumeText"])
            self.ui.mkv_pause.setStatusTip(self.Trad["ResumeStatusTip"])


    #========================================================================
    def WorkStop(self, Type):
        """Fonction d'arrêt du travail en cours."""
        # Type :
            # Error (en cas de plantage)
            # Stop (en cas d'arrêt du travail)
            # Close (en cas de fermeture du logiciel)
            # SrtError (en cas d'erreur tesseract)

        ### Teste l'état du processus pour ne pas le killer plusieurs fois (stop puis error)
        if self.process.state() != 0:
            ## Kill le boulot en cours
            self.process.kill()

            if not self.process.waitForFinished(1000):
                self.process.kill() # Attend que le travail soit arrêté pdt 1s

        ### Suppression des fichiers temporaires
        self.RemoveTempFiles()

        ### Dans le cas spécifique de Qtesseract
        if TempValues.contains("Qtesseract5Folder"):
            Qtesseract5Folder = QFileInfo(TempValues.value("Qtesseract5Folder"))

            ## Suppression du dossier temporaire
            if Qtesseract5Folder.exists():
                QDir(Qtesseract5Folder.absoluteFilePath()).removeRecursively()

                TempValues.remove("Qtesseract5Folder")

        ### Réinitialisation de la liste des commandes
        CommandList.clear()

        ### Envoie du texte le plus adapté
        if Type == "Stop":
            self.SetInfo(self.Trad["WorkCanceled"], "FF0000", True) # Travail annulé
            self.RemoveAllTempFiles()

        elif Type in ("Error", "SrtError"):
            self.SetInfo(self.Trad["WorkError"], "FF0000", True) # Erreur pendant le travail
            self.RemoveAllTempFiles()

        elif Type == "Close":
            return

        ### Bouton pause
        if 'psutil' in globals():
            Icon = QIcon.fromTheme("media-playback-pause", QIcon(":/img/media-playback-pause.png"))
            self.ui.mkv_pause.setIcon(Icon)
            self.ui.mkv_pause.setText(self.Trad["PauseText"])
            self.ui.mkv_pause.setStatusTip(self.Trad["PauseStatusTip"])

        ### Modifications graphiques
        self.ui.progressBar.setValue(0) # Remise à 0 de la barre de progression signifiant une erreur
        self.WorkInProgress(False) # Remise en état des widgets


    #========================================================================
    def SysTrayClick(self, event):
        """Fonction gérant les clics sur le system tray."""
        ### Si la fenêtre est cachée ou si elle n'a pas la main
        if not self.isVisible() or (not self.isActiveWindow() and self.isVisible()):
            self.show()
            self.activateWindow()

        ### Si la fenêtre est visible
        else:
            self.hide()


    #========================================================================
    def dragEnterEvent(self, event):
        """Fonction appelée à l'arrivée d'un fichier déposé sur la fenêtre."""
        # Impossible d'utiliser mimetypes car il ne reconnaît pas tous les fichiers...

        ### Récupération du nom du fichier
        try:
            Item = QFileInfo(event.mimeData().urls()[0].path())

        except:
            event.ignore()
            return

        ### Acceptation de l'événement en cas de fichier et de fichier valide (pour le fichier d'entrée)
        if Item.isFile() and Item.suffix().lower() in ("m4a", "mk3d", "mka", "mks", "mkv", "mp4", "nut", "ogg", "ogm", "ogv", "webm", "webma", "webmv", "avi"):
            event.accept()

        ### Acceptation de l'événement en cas de dossier (pour le dossier de sortie)
        elif Item.isDir():
            event.accept()


    #========================================================================
    def dropEvent(self, event):
        """Fonction appelée à la dépose du fichier/dossier sur la fenêtre."""
        # Impossible d'utiliser mimetypes car il ne reconnaît pas tous les fichiers...

        ### Récupération du nom du fichier
        Item = QFileInfo(event.mimeData().urls()[0].path())

        ### En cas de fichier (pour le fichier d'entrée)
        if Item.isFile():
            ## Vérifie que l'extension fasse partie de la liste et lance la fonction d'ouverture du fichier MKV avec le nom du fichier
            if Item.suffix().lower() in ("mka", "mks", "mkv", "mk3d", "webm", "webmv", "webma"):
                self.InputFile(Item.absoluteFilePath())

            ## Nécessite une conversion de la vidéo
            elif Item.suffix().lower() in ("avi", "mp4", "nut", "ogg"):
                self.MKVConvert(Item)

        ### Lancement de la fonction de gestion du dossier de sorti en cas de dossier (pour le dossier de sortie)
        elif Item.isDir():
            self.OutputFolder(Item.absoluteFilePath())


    #========================================================================
    def resizeEvent(self, event):
        """Fonction qui resize le tableau à chaque modification de la taille de la fenêtre."""
        ### Resize de la liste des pistes
        largeur = int((self.ui.mkv_tracks.size().width() - 50) / 3) # Calcul pour définir la taille des colonnes
        self.ui.mkv_tracks.setColumnWidth(3, largeur + 30) # Modification de la largeur des colonnes
        self.ui.mkv_tracks.setColumnWidth(4, largeur + 15) # Modification de la largeur des colonnes

        ### Resize de la liste des options
        largeur = int((self.ui.configuration_table.size().width() - 185) / 2) # Calcul pour définir la taille des colonnes
        self.ui.configuration_table.setColumnWidth(0, 160) # Modification de la largeur des colonnes
        self.ui.configuration_table.setColumnWidth(1, largeur) # Modification de la largeur des colonnes
        self.ui.configuration_table.setColumnWidth(2, largeur) # Modification de la largeur des colonnes

        ### Acceptation de l'événement
        event.accept()


    #========================================================================
    def RebootButton(self):
        """Fonction appelée lors d'un clic droit sur le bouton quitter pour relancer le logiciel."""
        self.CloseMode = "Reboot"
        self.close()


    #========================================================================
    def CloseButton(self):
        """Fonction appelée lors de la fermeture de la fenêtre par les boutons."""
        self.CloseMode = "Button"
        self.close()


    #========================================================================
    def closeEvent(self, event):
        """Fonction exécutée à la fermeture de la fenêtre quelqu'en soit la méthode."""
        ### Mode minimise lors de la fermeture avec la croix et alt+F4
        if not self.CloseMode and Configs.value("SysTrayMinimise"):
            self.hide()
            event.ignore()
            return

        ### Curseur de chargement
        self.setCursor(Qt.WaitCursor)

        ### Bloque les signaux sinon cela save toujours off
        self.ui.feedback_widget.blockSignals(True)

        ### Arrêt du travail en cours
        self.WorkStop("Close")

        ### Si l'option de suppression du fichier des fichiers et url récentes est activée, on l'efface
        if Configs.value("RecentInfos"):
            RecentFile = QFile(QDir.homePath() + '/.config/MKVExtractorQt5.pyrc')

            if RecentFile.exists():
                RecentFile.remove()

        ### Enregistrement de l'intérieur de la fenêtre (dockwidget)
        Configs.setValue("WinState", self.saveState())

        ### Si on a demandé à conserver l'aspect
        if Configs.value("WindowAspect"):
            Configs.setValue("WinGeometry", self.saveGeometry())

        ### Si on a rien demandé, on détruit la valeur
        elif Configs.contains("WinGeometry"):
            Configs.remove("WinGeometry")

        ### Suppression du dossier temporaire
        if self.FolderTempWidget.isValid():
            self.FolderTempWidget.remove()

        ### Acceptation de l'événement
        if self.CloseMode != "Reboot":
            event.accept()

        ### Mode reboot
        else:
            python = sys.executable
            execl(python, python, * sys.argv)

        ### Curseur normal
        self.setCursor(Qt.ArrowCursor)


#############################################################################
if __name__ == '__main__':
    ### Informations sur l'application'
    app = QApplication(sys.argv)
    app.setApplicationVersion("22.08.14b")
    app.setApplicationName("MKV Extractor Qt5")

    ### Gestion de l'emplacement du logiciel
    FileURL = QFileInfo(sys.argv[0])

    while FileURL.isSymLink():
        FileURL = QFileInfo(FileURL.symLinkTarget())

    AppFolder = FileURL.absolutePath()

    ### Création des dictionnaires et listes facilement modifiables partout
    MKVDico = {} # Dictionnaire qui contiendra toutes les pistes du fichier MKV
    MD5Dico = {} # Dictionnaire qui contiendra les sous titres à reconnaître manuellement
    MKVDicoSelect = {} # Dictionnaire qui contiendra les pistes sélectionnées
    MKVLanguages = [] # Liste qui contiendra et affichera dans les combobox les langues dispo (audio et sous titres)
    PowerList = {} # Dictionnaire qui contiendra les widgets de gestion de puissance de fichier AC3
    QualityList = {} # Dictionnaire qui contiendra les widgets de gestion de la qualité de fichier AC3
    QtStyleList = {} # Dictionnaire qui contiendra les styles possibles pour qt
    Sub2Srt = {} # Dictionnaire qui contiendra les widgets de conversion Sub en Srt
    Sup2Sub = {} # Dictionnaire qui contiendra les widgets de conversion Sup en Sub
    TempFiles = [] # Liste des fichiers temporaires pré ré-encapsulage ou conversion sous-titres
    AllTempFiles = [] # Liste des fichiers créés en cas d'arrêt du travail
    CommandList = [] # Liste des commandes à exécuter
    SubtitlesFiles = [] # Adresse des fichiers sous titres à ouvrir avant l'encapsulage
    WarningReply = [] # Retour de mkvmerge en cas de warning

    ### Configs du logiciel
    # Valeurs par défaut des options générales, pas toutes (MMGorMEQ, les valeurs de la fenêtre, l'adresse du dernier fichier ouvert)
    DefaultValues = {
        "AlreadyExistsTest": False, # Option ne signalant que le fichier existe déjà
        "CheckSizeCheckbox": False, # Option ne signalant pas le manque de place
        "ConfirmErrorLastFile": False, # Ne plus prévenir en cas d'absence de fichier au démarrage
        "DebugMode": False, # Option affichant plus ou d'infos
        "DelTempFiles": True, # Option de suppression des fichiers temporaires
        "Feedback": True, # Option affichant ou non les infos de retours
        "FeedbackBlock": False, # Option bloquant les infos de retours
        "FolderParentTemp": QDir.tempPath(), # Dossier temporaire dans lequel extraire les pistes pour visualisation
        "HideOptions": False, # Option cachant ou non les options inutilisables
        "LastFile": False, # Option conservant en mémoire le dernier mkv ouvert
        "Location/AvConv": "", # Adresses des logiciels
        "Location/BDSup2Sub": "",
        "Location/FFMpeg": "",
        "Location/MKClean": "",
        "Location/MKVInfo": "",
        "Location/MKVToolNix": "",
        "Location/MKValidator": "",
        "Location/Qtesseract5": "",
        "MMGorMEQ": "MEQ", # Logiciel à utiliser entre MKVExtractorQt et mmg
        "MMGorMEQCheckbox": False, # Valeur sautant la confirmation du choix de logiciel à utiliser
        "ConfirmConvert": False, # Valeur sautant la confirmation de conversion
        "ConfirmWarning": False, # Valeur sautant l'information du warning de conversion
        "InputFolder": QDir.homePath(), # Dossier du fichier mkv d'entrée
        "OutputFolder": QDir.homePath(), # Dossier de sortie
        "Language": QLocale.system().name(), # Langue du système
        "RecentInfos": True, # Option de suppression du fichier des fichiers et adresses récentes
        "RemuxRename": False, # Renommer automatiquement le fichier de sorti remux
        "OutputSameFolder": True, # Option d'utilisation du même dossier de sortie que celui du fichier mkv
        "SysTray": True, # Option affichant l'icône du system tray
        "SysTrayMinimise": False, # Option minimisant la fenêtre dans le systray lors de sa fermeture avec la croix
        "WindowAspect": True, # Conserver la fenêtre et sa géométrie
        "QtStyle": QApplication.style().objectName() # Conserver la fenêtre et sa géométrie
    }

    ### Système de gestion des configurations QSettings
    # Création ou ouverture du fichier de config
    Configs = QSettings(QSettings.NativeFormat, QSettings.UserScope, "MKV Extractor Qt5")

    # Gestion du bon type de variable
    # Boucle sur les valeurs par défaut
    for Key, Value in DefaultValues.items():
        # Si l'option n'existe pas, on l'ajoute au fichier avec la valeur de base
        if not Configs.contains(Key):
            Configs.setValue(Key, Value)

        # Si l'option existe, on la change dans le bon format
        else:
            try:
                KeyType = type(Value)

                # Si c'est censé ếtre un bool
                if KeyType is bool:
                    if Configs.value(Key).lower() == "true":
                        Configs.setValue(Key, True)

                    else:
                        Configs.setValue(Key, False)

                # Si ça doit être un int
                elif KeyType is int:
                    Configs.setValue(Key, int(Configs.value(Key)))

                # Si c'est un str
                elif KeyType is str:
                    Configs.setValue(Key, str(Configs.value(Key)))

                # Sinon, on réinitialise
                else:
                    Configs.setValue(Key, Value)

            # S'il y a un souci, la valeur est réinitialisée
            except:
                Configs.setValue(Key, Value)

    ### Valeurs temporaires
    # Valeurs par défaut des boutons et actions, pas toutes (MMGorMEQ, les valeurs de la fenêtre, l'adresse du dernier fichier ouvert)
    DefaultTempValues = {
        "AllTracks": False,
        "AudioConvert": False,
        "AudioBoost": 0,
        "AudioQuality": 0,
        "AudioStereo": False,
        "ChaptersFile": "",
        "Command": "",
        "DurationFile": 0,
        "FFMpeg": False,
        "FirstRun": True,
        "FolderTemp": "",
        "MKVLoaded": False,
        "OutputFile": "",
        "Qtesseract5Folder": "",
        "Sub2Srt": 0,
        "Sup2Sub": 0,
        "BDSup2Sub": False,
        "Reencapsulate": False,
        "SubtitlesConvert": False,
        "SubtitlesOpen": False,
        "SuperBlockTemp": False,
        "TagsFile": "",
        "TitleFile": "",
        "SubtitlesConvert": False,
        "WorkOldLine": ""
    }

    # Création ou ouverture du fichier de config
    TempValues = QSettings(QSettings.NativeFormat, QSettings.UserScope, "MKV Extractor Qt5")

    # Chargement des valeurs par défaut
    for Key, Value in DefaultTempValues.items():
        TempValues.setValue(Key, Value)

    ### Lancement de l'application
    MKVExtractorQt5Class = MKVExtractorQt5()
    MKVExtractorQt5Class.setAttribute(Qt.WA_DeleteOnClose)
    sys.exit(app.exec())
