# -*- coding: utf-8 -*-
"""
Model_S2_AdaBoost.py  -  AdaBoost  (Ek, Tablo S1)
AdaBoost, varsayilan ayarlar.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S2_AdaBoost.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S2')
"""
from model_ortak import *
from sklearn.ensemble import AdaBoostClassifier

calistir("S2", "AdaBoost", AdaBoostClassifier(random_state=SEED), yer="Ek, Tablo S1")
