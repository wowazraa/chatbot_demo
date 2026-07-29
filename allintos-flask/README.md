# Allintos — Flask Projesi

Hostinger Website Builder ile yapılmış Allintos sitesinin Python/Flask'e
taşınmış hâli. Ana sayfa içeriği, tasarımı, logo ve arka plan görseli
orijinal siteden alınmıştır.

## Kurulum ve çalıştırma

```bash
# 1) (Önerilir) sanal ortam oluşturun
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2) Bağımlılıkları kurun
pip install -r requirements.txt

# 3) Uygulamayı başlatın
python app.py
```

Ardından tarayıcıdan `http://127.0.0.1:5000` adresini açın.

## Proje yapısı

```
project/
├── app.py                # Flask uygulaması ve rotalar
├── requirements.txt
├── static/
│   ├── css/style.css     # Tüm stiller
│   ├── js/main.js        # Mobil menü + açılır menü
│   └── img/              # logo.png, hero.jpg, favicon.ico
└── templates/
    ├── base.html         # Ortak iskelet (header + footer)
    ├── index.html        # Ana sayfa
    ├── page.html         # Alt sayfalar için genel şablon
    └── icons/            # Sosyal medya SVG ikonları
```

## Sayfalar (rotalar)

| URL                         | Açıklama                          |
|-----------------------------|-----------------------------------|
| `/`                         | Ana sayfa (Hakkımızda ile aynı)   |
| `/hakkimizda`               | Ana sayfaya yönlendirir (`/`)     |
| `/dijital-donusum`          | Dijital Dönüşüm                   |
| `/ai-danisman`              | AI Danışman                       |
| `/globallesme`              | Globalleşme                       |
| `/globallesme/turquality`   | Turquality ve Marka Programı      |
| `/globallesme/e-turquality` | E-Turquality Programı             |
| `/blog`                     | Blog                              |

Not: Sitede HAKKIMIZDA menüsü ana sayfayı gösterir (ikisi aynı sayfadır).
Tüm menü sayfaları tam içeriklidir. `page.html` yalnızca yedek/iskelet
şablon olarak projede durur.

## Görseller hakkında

- `logo.png` ve `hero.jpg` orijinal siteden çıkarıldı (`static/img/`).
- Başarı Hikayeleri bölümündeki iki fotoğraf **Unsplash** üzerinden
  doğrudan bağlanıyor (orijinal sitedeki gibi). Kendi görsellerinizi
  kullanmak isterseniz `templates/index.html` içindeki `<img src="...">`
  adreslerini `static/img/` altındaki kendi dosyalarınızla değiştirin.
- Logo, HAR kaydındaki 375px'lik sürümden alındığı için görece küçük.
  Daha yüksek çözünürlüklü sürümü Hostinger medya yöneticisinden indirip
  `static/img/logo.png` ile değiştirebilirsiniz.

## Formlar

Bülten ve iletişim formları şu an sadece bir onay mesajı gösteriyor.
Gerçek kullanımda `app.py` içindeki `newsletter()` ve `contact_submit()`
fonksiyonlarına veritabanına kaydetme veya e-posta gönderme kodunu
ekleyin.

## Üretime alırken

- `app.secret_key` değerini ortam değişkeninden okuyun.
- `debug=True` yerine bir WSGI sunucusu kullanın (ör. `gunicorn app:app`).
