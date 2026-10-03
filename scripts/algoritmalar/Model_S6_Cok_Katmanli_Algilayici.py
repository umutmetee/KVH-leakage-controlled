# -*- coding: utf-8 -*-
"""
Model_S6_Cok_Katmanli_Algilayici.py  -  Multilayer Perceptron  (Ek, Tablo S1)
Tek gizli katman (64 noron).
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S6_Cok_Katmanli_Algilayici.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S6')
"""
from model_ortak import *
from sklearn.neural_network import MLPClassifier

calistir("S6", "Multilayer Perceptron", MLPClassifier(hidden_layer_sizes=(64,), max_iter=1000, random_state=SEED), yer="Ek, Tablo S1")
