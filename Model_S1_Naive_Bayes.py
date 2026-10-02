# -*- coding: utf-8 -*-
"""
Model_S1_Naive_Bayes.py  -  Naive Bayes  (Ek, Tablo S1)
Gauss Naive Bayes.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S1_Naive_Bayes.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S1')
"""
from model_ortak import *
from sklearn.naive_bayes import GaussianNB

calistir("S1", "Naive Bayes", GaussianNB(), yer="Ek, Tablo S1")
