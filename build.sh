#! /bin/bash

# set -e
# set -v

# Fichier servant :
# - Lors de la création du paquet sources
# - Après la création d'un paquet source, les fichiers sont supprimés, il faut donc les recréer

# la paquet pyqt5-dev-tools est nécessaire

chemin="$(cd "$(dirname "$0")";pwd)"
cd "${chemin}"

### Mise à jour des fichiers ts : -noobsolete
pylupdate5 ui_MKVExtractorQt5.ui MKVExtractorQt5.py -ts MKVExtractorQt5_fr_FR.ts MKVExtractorQt5_cs_CZ.ts MKVExtractorQt5_es_ES.ts
pylupdate5 QFileDialogCustom/QFileDialogCustom.py -ts QFileDialogCustom/QFileDialogCustom_fr_FR.ts QFileDialogCustom/QFileDialogCustom_cs_CZ.ts QFileDialogCustom/QFileDialogCustom_es_ES.ts


### Conversion des fichiers ts en qm
if [[ -e "/usr/lib/x86_64-linux-gnu/qt5/bin/lrelease" ]]
then
    /usr/lib/x86_64-linux-gnu/qt5/bin/lrelease *.ts QFileDialogCustom/*.ts

elif [[ -e "/usr/lib/i386-linux-gnu/qt5/bin/lrelease" ]]
then
    /usr/lib/i386-linux-gnu/qt5/bin/lrelease *.ts QFileDialogCustom/*.ts

else
    echo "cannot find 'lrelease'"
    exit 1
fi


### Création d'un fichier source python (contient les icônes)
echo '<RCC>
  <qresource prefix="/">' > MKVRessources.qrc

for icon in img/*
do
    echo "    <file>${icon}</file>" >> MKVRessources.qrc
done

echo '  </qresource>
</RCC>' >> MKVRessources.qrc

pyrcc5 MKVRessources.qrc -o MKVRessources_rc.py


### Conversion de l'interface graphique en fichier python
pyuic5 ui_MKVExtractorQt5.ui -o ui_MKVExtractorQt5.py


### Création d'un système d'icône de secours sur le fichier python ci-dessus
for icon in img/*
do
    nom=${icon##*/}
    nom=${nom%.*}
    sed -i "s@QtGui.QIcon.fromTheme(\"${nom}\")@QtGui.QIcon.fromTheme(\"${nom}\", QtGui.QIcon(\":/${icon}\"))@" ui_MKVExtractorQt5.py
done
