# -*- coding: utf-8 -*-
"""
Model_S9_Yigma.py  -  Stacking  (Ek, Tablo S1)
LR + Naive Bayes + Random Forest, ust model lojistik regresyon; esik birincil LR esigi (tau).
Ayni 20 degisken, ayni 80/20 bolme (SEED=42); esik egitim kat-disi tahminlerinden (Youden).
KULLANIM:  py Model_S9_Yigma.py
Cikti: ekranda Tablo satiri + model_sonuclari.xlsx (sayfa 'ozet' ve 'Model_S9')
"""
from model_ortak import *
from sklearn.ensemble import StackingClassifier, RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression

calistir("S9", "Stacking", StackingClassifier([("lr", boru()), ("nb", boru(GaussianNB())), ("rf", boru(RandomForestClassifier(n_estimators=400, random_state=SEED)))], final_estimator=LogisticRegression(max_iter=2000), cv=5), topluluk=True, yer="Ek, Tablo S1")
