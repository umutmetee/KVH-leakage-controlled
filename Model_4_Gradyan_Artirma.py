# -*- coding: utf-8 -*-
"""
Model_4_Gradyan_Artirma.py  -  Gradient Boosting  (Makale, Tablo 3)
Gradyan artirma, varsayilan ayarlar.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_4_Gradyan_Artirma.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_4')
"""
from model_ortak import *
from sklearn.ensemble import GradientBoostingClassifier

calistir("4", "Gradient Boosting", GradientBoostingClassifier(random_state=SEED), yer="Makale, Tablo 3")
