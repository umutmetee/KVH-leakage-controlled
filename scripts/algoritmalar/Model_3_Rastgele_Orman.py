# -*- coding: utf-8 -*-
"""
Model_3_Rastgele_Orman.py  -  Random Forest  (Makale, Tablo 3)
400 agacli rastgele orman.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_3_Rastgele_Orman.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_3')
"""
from model_ortak import *
from sklearn.ensemble import RandomForestClassifier

calistir("3", "Random Forest", RandomForestClassifier(n_estimators=400, random_state=SEED), yer="Makale, Tablo 3")
