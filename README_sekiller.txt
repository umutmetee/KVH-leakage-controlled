SEKIL BETIKLERI - KVH makalesi (JCM) ve tez
============================================
Her figur ayri bir .py dosyasidir. Hesap ve cizim ayrilmistir:

ADIM 1 (bir kez, birkac dakika):
    py 00_sekil_verisi_uret.py
  -> sizintisiz_veri.xlsx + aiveri2026_haz.xlsx okunur, analiz KVH_TAM_ANALIZ.py ile
     ayni ayarlarla (SEED=42, C=0.01, K=20) calisir ve her figurun sayilari
     sekil_verileri.xlsx dosyasina yazilir (figur basina bir sayfa).
     Bu dosyada hasta adi veya hasta numarasi YOKTUR; yalnizca ozet sayilar ve
     test kumesindeki 187 hastanin sonuc (0/1) ve tahmin olasiliklari vardir.
  -> Ekranda KONTROL satirlari: AUROC 0.755, tau 0.428, n 931 / olay 371 vb.
     Bu degerler tutmuyorsa sekilleri cizmeden once haber verin.

ADIM 2 (her figur saniyeler icinde):
    py Figure_2_katsayi_forest.py        (tek figur)
    py tum_sekilleri_ciz.py              (hepsi)
  -> cikti_sekil/en/Figure_2.png (makale, 600 dpi) ve .pdf
     cikti_sekil/tr/Figure_2.png (tez, Turkce etiketler)

Makaledeki numara -> betik
  Figure 1  akis semasi                Figure_1_akis_semasi.py
  Figure 2  katsayi forest             Figure_2_katsayi_forest.py
  Figure 3  ROC (4 model)              Figure_3_roc_modeller.py
  Figure 4  k secimi                   Figure_4_k_secimi.py
  Figure 5  kalibrasyon                Figure_5_kalibrasyon.py
  Figure 6  nomogram                   Figure_6_nomogram.py
  Figure 7  ek deger (referans model)  Figure_7_ek_deger.py
  Figure 8  karar egrisi               Figure_8_karar_egrisi.py
  Figure 9  duyarlilik forest          Figure_9_duyarlilik_forest.py
  Figure S1-S11  ek dosya figurleri    Figure_S1_... - Figure_S11_...

Tum figurlerin ortak stili (yazi tipi, renkler, 600 dpi): ortak.py
Bu klasordeki tum dosyalar 07_Analiz klasorune, veri dosyalarinin yanina konur.
GitHub'a yalnizca .py dosyalari ve bu README yuklenir; .xlsx dosyalari YUKLENMEZ.
