# Arac Paylasim Sistemi (Car Sharing)

Saatlik arac kiralama uzerine kurulu, masaustu calisan kurumsal goruntulu bir
arac paylasim uygulamasi. Tek dosyalik SQLite veritabani, katmanli mimari ve
modern bir GUI (CustomTkinter) sunar.

> Akademik proje 1 ("Arac Paylasim Sistemi") gereksinimlerinin uzerine,
> profesyonel bir SaaS deneyimi taklit edecek sekilde genisletilmistir.

---

## Ozellik Ozeti

### Kimlik / Yetkilendirme
- Login & Register ekrani (Enter ile giris/kayit, sifre tekrari, ehliyet no zorunlu).
- `admin` ve `user` rolleri; aktif/pasif kullanici durumu.
- Sistem admini (`admin@carshare.local`) silinemez/duzenlenemez kritik islemlerle korunur.

### Kullanici Akisi
- Arac ekleme: marka, model, kilometre ve gorsel (file picker + canli onizleme).
- Ilan olusturma: arac secimi, baslik/aciklama, saatlik ucret, konum.
- Onayli ilanlardan saat bazli kiralama:
  - Saat sayisi formu (1-720 saat),
  - Otomatik tutar hesabi,
  - Atomik islem (transaction): bakiye dusur, sahibe yatir, arac musait_mi bayraktan dus.
- Bakiye yonetimi:
  - Sanal kart ile bakiye yukleme simulasyonu (16 hane kart no, MM/YY, 3-4 hane CVV),
  - Yukleme animasyonu (indeterminate progress) ve basari/hata mesajlari.
- Yorum & Puan:
  - Sadece o ilani kiralamis kullanici yorum yazabilir/puan verebilir,
  - **Her ilana 1 yorum + 1 puan hakki** (DB UNIQUE + servis dogrulama + UI disable).
- Begeni (toggle) sistemi.
- Kiralamalarim sekmesi:
  - Aktif kiralamalar icin canli geri sayim (gun/saat/dakika/saniye),
  - Kullanim yuzdesi progress bar,
  - "Kiralamayi Bitir" eylemi,
  - Tarihce listesi.
- Ilanlarim sekmesi:
  - Kullanicinin kendi ilanlarini kart goruntusunde listeler,
  - Duzenleme modali (basariyla guncellenince ilan yeniden admin onayina dusurulur),
  - Aktif kiralamasi olan ilan duzenleme engelli.
- Bildirim merkezi (kiralama, onay, ilan guncelleme, ticket yaniti).
- Ticket destek sistemi: olusturma, durum takibi, admin yanitinin yanitlayan ad/rol bilgisiyle gosterimi.

### Admin Akisi
- Kullanici yonetimi (rol/aktiflik degisikligi, bakiye yukleme).
- Ilan moderasyonu (`pending` / `approved` / `rejected`).
- Ticket yonetimi (kart goruntulu liste, modal icinden yanitlama).
- Sistem yonetimi:
  - **Veritabani yedek alma** (kullanici secimli yol),
  - **Veritabani sifirlama** (sistem admini disindaki tum veriyi siler, kirmizi onayli),
- Dashboard KPI metrikleri.

### Arayuz (UX)
- Sol scrollable sidebar, kullanici/admin bolumleriyle.
- Tum admin sayfalari kart bazli (Treeview yok).
- Dark / Light tema secimi (Ayarlar -> Uygulama Ayarlari).
- Otomatik yenileme (auto-sync): veri imzasi degisince UI tazelenir; ayarlardan kapatilabilir.
- Tutarli emoji / Unicode ikonografi.
- Login ekranindaki "credential" yazisi yok; demo erisim asagida belgelenmistir.

### Mimari Garantiler
- `kiralama_baslat` ve `kiralama_bitir` islemleri `Database.transaction()` ile atomiktir
  (rollback'a duser, parsel parsel veri kalmaz).
- Eski (legacy) sema migrasyonu otomatiktir; eski `kiralamalar.arac_id` /
  `kullanici_id` NOT NULL kolonlari yeni sema ile guvenle yeniden yazilir,
  veriler `ilanlar.arac_id` uzerinden taşinir.
- Sahip kendi ilanini kiralayamaz/yorumlayamaz/puanlayamaz.
- Yetersiz bakiye, dolu arac, onaysiz ilan, mukerrer aktif kiralama gibi ihlaller
  net hata mesaji ile reddedilir.

---

## Hizli Baslangic

### 1) Sanal ortam ve bagimliliklar

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Calistirma
```bash
python run.py
```

Ilk acilista veritabani `src/carshare/data/carshare.db` icinde olusturulur ve
sistem admini ekilir.

### Demo Admin Hesabi
- Email: `admin@carshare.local`
- Sifre: `admin123`

> Production kullaniminda ilk acilistan sonra bu sifreyi degistirin.

---

## Proje Yapisi

```
AracPaylasim/
├── run.py                       # Entry point (python run.py)
├── requirements.txt
├── README.md
├── .gitignore
└── src/
    └── carshare/
        ├── main.py              # MainWindow baslatici
        ├── models.py            # Dataclass tabanli alan modelleri
        ├── repository.py        # SQLite + sema/migrasyon + transaction
        ├── services.py          # Is kurallari / uygulama servisleri
        ├── data/                # Yerel SQLite db (git'te yok sayilir)
        └── ui/
            └── main_window.py   # CustomTkinter GUI
```

## Bagimliliklar

| Paket          | Versiyon       | Aciklama                               |
| -------------- | -------------- | -------------------------------------- |
| customtkinter  | >= 5.2.2       | Modern Tk tabanli GUI bilesenleri      |
| pillow         | >= 10.2.0      | Arac gorseli onizleme/kart thumbnail   |

Python 3.10+ tavsiye edilir (dataclass + tip ipuclari kullanimi).

---

## GitHub Push'a Hazirlik

`.gitignore` su anki klasoru push'a hazirlamak icin yapilandirilmistir.
Asagidaki dosyalar dahil **edilmez**:

- Sanal ortam: `.venv/`, `venv/`
- Python cache: `__pycache__/`, `*.pyc`
- Yerel veritabani: `src/carshare/data/*.db` ve journal dosyalari
- Yedekler: `carshare_backup_*.db`, `backups/`
- Editor: `.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db`

Ilk push:
```bash
git init
git add .
git commit -m "feat: initial release of Car Sharing System"
git branch -M main
git remote add origin <repo-url>
git push -u origin main
```

---

## Sik Karsilasilan Sorunlar

- **`no such column: durum` veya `kiralamalar.arac_id` constraint hatasi:**
  Eski bir DB sahipsiniz demektir. Uygulamayi tekrar baslatmak migrasyonu calistirir;
  yine de calismazsa `src/carshare/data/carshare.db` dosyasini silip uygulamayi acabilirsiniz
  (admin yedek alma ozelligini once kullaniniz).
- **Tema degistirince bazi widget'lar geri donmuyor:**
  Ayarlar sayfasindan tema secip "Uygula" diyiniz; otomatik yenileme kalan
  bilesenleri yeniden cizecektir.

---

## Lisans

Bu proje akademik amaclar icin olusturulmustur. Kurumsal kullanim oncesi
sifre/secret yonetimi, audit log, dis kimlik dogrulama gibi ek katmanlar
eklenmelidir.
