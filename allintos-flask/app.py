"""
Allintos — Flask uygulaması
Hostinger Website Builder sitesinin Flask'e taşınmış hâli.
"""
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "degistir-bu-anahtari-uretimde"  # üretimde ortam değişkeninden okuyun

# Menüdeki üst navigasyon linkleri (tüm şablonlarda kullanılıyor)
NAV = [
    {"label": "HAKKIMIZDA", "endpoint": "index"},
    {"label": "DİJİTAL DÖNÜŞÜM", "endpoint": "dijital_donusum"},
    {"label": "AI DANIŞMAN", "endpoint": "ai_danisman"},
    {
        "label": "GLOBALLEŞME",
        "endpoint": "globallesme",
        "children": [
            {"label": "TURQUALITY", "endpoint": "turquality"},
            {"label": "E-TURQUALITY", "endpoint": "e_turquality"},
        ],
    },
    {"label": "Blog", "endpoint": "blog"},
]

# İletişim bilgileri (footer + iletişim bölümü)
CONTACT = {
    "email": "info@buyumevizyon.com",
    "phone": "+90 212 555 1234",
}


@app.context_processor
def inject_globals():
    """Her şablona NAV ve CONTACT değişkenlerini otomatik geçir."""
    return {"nav": NAV, "contact": CONTACT}


@app.route("/")
def index():
    return render_template("index.html", active="index")


# Hakkımızda ana sayfa ile aynı yerdir; eski bağlantılar için yönlendirme.
@app.route("/hakkimizda")
def hakkimizda():
    return redirect(url_for("index"))


@app.route("/dijital-donusum")
def dijital_donusum():
    return render_template("dijital-donusum.html", active="dijital_donusum")


@app.route("/ai-danisman")
def ai_danisman():
    return render_template("ai-danisman.html", active="ai_danisman")


@app.route("/globallesme")
def globallesme():
    return render_template("globallesme.html", active="globallesme")


@app.route("/globallesme/turquality")
def turquality():
    return render_template("program-detail.html", active="globallesme",
                           program_title="Turquality ve Marka Programı")


@app.route("/globallesme/e-turquality")
def e_turquality():
    return render_template("program-detail.html", active="globallesme",
                           program_title="E - Turquality Programı")


@app.route("/blog")
def blog():
    return render_template("blog.html", active="blog")


# --- Form işleyicileri ---
@app.route("/bultene-abone-ol", methods=["POST"])
def newsletter():
    name = request.form.get("name", "").strip()
    # Gerçek uygulamada burada bir veritabanına / e-posta listesine kaydedin.
    if name:
        flash(f"Teşekkürler {name}, bültene başarıyla abone oldunuz!", "success")
    else:
        flash("Lütfen adınızı girin.", "error")
    return redirect(request.referrer or url_for("index"))


@app.route("/iletisim", methods=["POST"])
def contact_submit():
    name = request.form.get("name", "").strip()
    if name:
        flash(f"Mesajınız alındı {name}, en kısa sürede dönüş yapacağız.", "success")
    else:
        flash("Lütfen adınızı girin.", "error")
    return redirect((request.referrer or url_for("index")) + "#iletisim")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
