# -*- coding: utf-8 -*-
"""
Model_S3_Ekstra_Agaclar.py  -  Extra Trees  (Ek, Tablo S1)
400 agacli Extra Trees.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S3_Ekstra_Agaclar.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S3')
"""
from model_ortak import *
from sklearn.ensemble import ExtraTreesClassifier

calistir("S3", "Extra Trees", ExtraTreesClassifier(n_estimators=400, random_state=SEED), yer="Ek, Tablo S1")
