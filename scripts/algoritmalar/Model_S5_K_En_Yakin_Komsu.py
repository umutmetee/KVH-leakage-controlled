# -*- coding: utf-8 -*-
"""
Model_S5_K_En_Yakin_Komsu.py  -  K-Nearest Neighbours  (Ek, Tablo S1)
k = 7 en yakin komsu.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S5_K_En_Yakin_Komsu.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S5')
"""
from model_ortak import *
from sklearn.neighbors import KNeighborsClassifier

calistir("S5", "K-Nearest Neighbours", KNeighborsClassifier(n_neighbors=7), yer="Ek, Tablo S1")
