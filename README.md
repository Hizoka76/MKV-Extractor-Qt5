![icon](icons/mkv-extractor-qt5.png)
# MKV-Extractor-Qt5

## Version Française :

![01](https://user-images.githubusercontent.com/48289933/138563147-9bf32ec0-674f-4fb1-88b2-377d43b9e5de.png)


### Principe de base :
MKV Extracto Qt5 est écrit en **python 3 + Qt5**.
Il est à utiliser en complément de **MKVToolNix** [MKVToolNix](https://mkvtoolnix.download/index.html).

Fonctionnement :
 - Indiquer un fichier matroska (mkv).
 - Cocher les pistes à extraires.
 - Presser le bouton "Executer".

Le logiciel permet de :
 - Extraire les pistes contenu dans des fichiers matroska (mkv).
 - Convertir des fichiers audio DTS en AC3 afin que le fichier matroska (mkv) via ffmpeg ou avconv.
   - Le format ac3 permet plus de compatibilité matériel (comme la FreeBox v5)
   - Il est également possible d'amplifier l'audio et de passer en stéréo.
 - Ré-encapsuler un fichier matroska (mkv) après avoir enlevé des pistes ou la conversion de fichiers audio DTS.
   - Si seule la rencapsulation vous interresse, il vous sera proposer d'utiliser **mkvtoolnix-gui** s'il est installé.
 - Vérifier la conformité du fichier matroska (mkv) via **mkvalidator**.
 - Optimiser le fichier matroska (mkv) via **mkclean**.
 - Visualiser (ectration + lancement) les pièces jointes au fichier matroska (mkv).
 - Convertir automatiquement un fichier vobsub en srt via **tesseract** avec multi cpu.


### Dépendances :
 - **AvConv / FFMpeg** [FFMPeg](https://ffmpeg.org/) : Pour la conversion audio.
 - **BDSup2Sub** [BDSup2Sub](https://github.com/mjuhasz/BDSup2Sub) : Pour la conversion des fichiers sous-titres Sup en Sub (Logiciel inclut dans MKV Extractor Qt5).
 - **MKClean** [MKClean](https://matroska.org/downloads/mkclean.html) : Pour l'optimisation des fichiers matroska.
 - **MKVToolNix** [MKVToolNix](https://mkvtoolnix.download/index.html): **Obligatoire** pour récupérer les informations sur les pistes.
   - Contient la commande _mkvextract_ qui est primordiale.
   - Contient également _mkvmerge_ pour réencapsuler les pistes.
 - **MKVToolNixGui** [MKVToolNixGui](https://mkvtoolnix.download/index.html): Pour afficher toutes les informations du fichier matroska depuis MKVToolNix.
 - **MKValidator** [MKValidator](https://matroska.org/downloads/mkvalidator.html) : Pour vérifier les fichiers matroska.
 - **QTesseract5** : Pour la conversion automatique des sous-titres sub en srt avec _tesseract_.


*** ***

## English Version :

![02](https://user-images.githubusercontent.com/48289933/138563203-081bf6b5-61d9-49bf-9d32-52494414c5b1.png)


### Basic principle:
MKV Extracto Qt5 is written in **python3 + Qt5**.
It is to be used in addition to **MKVToolNix** [MKVToolNix](https://mkvtoolnix.download/index.html).

How it works:
 - Specify a matroska file (mkv).
 - Check the tracks to extract.
 - Press the button "Execute".

The software allows to :
 - Extract tracks from matroska (mkv) files.
 - Convert DTS audio files to AC3 so that the matroska (mkv) file via ffmpeg or avconv.
   - The ac3 format allows more hardware compatibility (like the FreeBox v5)
   - It is also possible to amplify the audio and switch to stereo.
 - Re-encapsulate a matroska (mkv) file after removing tracks or converting DTS audio files.
   - If you are only interested in re-encapsulation, you will be offered to use **mkvtoolnix-gui** if it is installed.
 - Check the conformity of the matroska (mkv) file via **mkvalidator**.
 - Optimize the matroska (mkv) file via **mkclean**.
 - View (run + launch) attachments to matroska (mkv) file.
 - Automatically convert a vobsub file to srt via **tesseract** with multi cpu.


### Dependencies:
 - AvConv / FFMpeg** [FFMPeg](https://ffmpeg.org/) : For audio conversion.
 - BDSup2Sub** [BDSup2Sub](https://github.com/mjuhasz/BDSup2Sub) : For converting Sup to Sub files (software included in MKV Extractor Qt5).
 - MKClean** [MKClean](https://matroska.org/downloads/mkclean.html): For optimization of matroska files.
 - MKVToolNix** [MKVToolNix](https://mkvtoolnix.download/index.html): **Required** to get track information.
   - Contains the _mkvextract_ command which is essential.
   - Also contains _mkvmerge_ to re-encapsulate tracks.
 - MKVToolNixGui** [MKVToolNixGui](https://mkvtoolnix.download/index.html): To display all information of the matroska file from MKVToolNix.
 - MKValidator** [MKValidator](https://matroska.org/downloads/mkvalidator.html): To check the matroska files.
 - QTesseract5**: For automatic conversion of subtitles to srt with _tesseract_.
