# -*- coding: utf-8 -*-
"""
Model_2_Destek_Vektor_Makinesi.py  -  Support Vector Machine  (Makale, Tablo 3)
RBF cekirdekli SVM, varsayilan ayarlar.
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_2_Destek_Vektor_Makinesi.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_2')
"""
from model_ortak import *
from sklearn.svm import SVC

calistir("2", "Support Vector Machine", SVC(C=1, gamma="scale", probability=True, random_state=SEED), yer="Makale, Tablo 3")
