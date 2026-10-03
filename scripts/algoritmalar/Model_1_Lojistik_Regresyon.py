# -*- coding: utf-8 -*-
"""
Model_1_Lojistik_Regresyon.py  -  Logistic Regression  (Makale, Tablo 3)
Birincil model: L2 cezali lojistik regresyon, C = 0.01.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_1_Lojistik_Regresyon.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_1')
"""
from model_ortak import *
from sklearn.linear_model import LogisticRegression

calistir("1", "Logistic Regression", LogisticRegression(C=C, max_iter=2000), yer="Makale, Tablo 3")
