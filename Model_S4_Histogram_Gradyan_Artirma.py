# -*- coding: utf-8 -*-
"""
Model_S4_Histogram_Gradyan_Artirma.py  -  Hist. Gradient Boosting  (Ek, Tablo S1)
Histogram tabanli gradyan artirma.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S4_Histogram_Gradyan_Artirma.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S4')
"""
from model_ortak import *
from sklearn.ensemble import HistGradientBoostingClassifier

calistir("S4", "Hist. Gradient Boosting", HistGradientBoostingClassifier(random_state=SEED), yer="Ek, Tablo S1")
