#!/bin/sh

chemin="$(cd "$(dirname "$0")";pwd)"
cd "${chemin}"


rm -rf __pycache__ MKVRessources_rc.py ui_MKVExtractorQt5.py Languages/*.qm

rm -rf QFileDialogCustom/__pycache__ QFileDialogCustom/*.qm

rm -rf WhatsUp/__pycache__
