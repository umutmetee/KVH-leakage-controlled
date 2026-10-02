# -*- coding: utf-8 -*-
"""
Model_5_Yatak_Basi_Referans.py  -  Bedside reference (logistic regression, 7 variables)  (Makale, Bolum 3.8 / Sekil 7)
Yatak basi referans modeli: yas, cinsiyet, BKI, sistolik/diastolik KB, sigara, diyabet suresi (Bolum 3.8, Sekil 7).
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_5_Yatak_Basi_Referans.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_5')
"""
from model_ortak import *
from sklearn.linear_model import LogisticRegression

calistir("5", "Bedside reference (logistic regression, 7 variables)", LogisticRegression(C=C, max_iter=2000), degiskenler=KLINIK, yer="Makale, Bolum 3.8 / Sekil 7")
