# -*- coding: utf-8 -*-
"""
Model_S8_Yumusak_Oylama.py  -  Soft Voting  (Ek, Tablo S1)
LR + Naive Bayes + Random Forest yumusak oylama; esik birincil LR esigi (tau).
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S8_Yumusak_Oylama.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S8')
"""
from model_ortak import *
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.naive_bayes import GaussianNB

calistir("S8", "Soft Voting", VotingClassifier([("lr", boru()), ("nb", boru(GaussianNB())), ("rf", boru(RandomForestClassifier(n_estimators=400, random_state=SEED)))], voting="soft"), topluluk=True, yer="Ek, Tablo S1")
