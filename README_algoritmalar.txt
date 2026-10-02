ALGORITMA BETIKLERI (her algoritma ayri .py)
Ayni klasorde ya da ust klasorde: sizintisiz_veri.xlsx, aiveri2026_haz.xlsx
Calistirma (terminal):  py tum_modelleri_calistir.py      (hepsi)
                        py Model_1_Lojistik_Regresyon.py  (tek model)
Cikti: model_sonuclari.xlsx  -> 'ozet' sayfasi (Tablo 3 / Tablo S1 sutunlari) + her model icin test olasiliklari
Hasta adi/numarasi yazilmaz.

MAKALE (Tablo 3, Bolum 3.8)          EK (Tablo S1)
Model_1  Lojistik regresyon (birincil)   Model_S1 Naive Bayes
Model_2  Destek vektor makinesi          Model_S2 AdaBoost
Model_3  Rastgele orman                  Model_S3 Extra Trees
Model_4  Gradyan artirma                 Model_S4 Hist. gradyan artirma
Model_5  Yatak basi referans (7 deg.)    Model_S5 k-en yakin komsu (k=7)
                                         Model_S6 Cok katmanli algilayici
                                         Model_S7 Karar agaci
                                         Model_S8 Yumusak oylama (LR+NB+RF)
                                         Model_S9 Yigma (LR+NB+RF)
Ortak boru hatti: model_ortak.py (SEED=42, K=20, C=0.01; secim yalnizca egitim verisinde).
Beklenen: Model_1 AUROC 0.755, tau 0.428.
