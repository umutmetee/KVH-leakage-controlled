# -*- coding: utf-8 -*-
"""
Model_S7_Karar_Agaci.py  -  Decision Tree  (Ek, Tablo S1)
Derinligi 5 ile sinirli karar agaci.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S7_Karar_Agaci.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S7')
"""
from model_ortak import *
from sklearn.tree import DecisionTreeClassifier

calistir("S7", "Decision Tree", DecisionTreeClassifier(max_depth=5, random_state=SEED), yer="Ek, Tablo S1")
