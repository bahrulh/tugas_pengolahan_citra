from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import cv2
import csv
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "ini_rahasia"  # Ganti dengan kunci rahasia kuat
UPLOAD_FOLDER = 'uploads'
DATABASE_FOLDER = 'static/database' # Path corrected to be relative to the app.py
HISTORY_FILE = 'history.csv'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_FOLDER, exist_ok=True) # Pastikan folder database ada

# User login sederhana
users = {"admin": "admin"}

# Decorator untuk halaman yang perlu login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Fungsi pencocokan sidik jari
def match_fingerprint(img1_path, img2_path):
    img1 = cv2.imread(img1_path, 0)
    img2 = cv2.imread(img2_path, 0)

    # Periksa apakah gambar berhasil dimuat
    if img1 is None:
        print(f"Error: Could not load image at {img1_path}")
        return 0
    if img2 is None:
        print(f"Error: Could not load image at {img2_path}")
        return 0

    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    if des1 is None or des2 is None:
        return 0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    # Logika good matches sudah benar, pertimbangkan untuk menyesuaikan ambang batas berdasarkan pengujian
    good_matches = [m for m in matches if m.distance < 50] # Ambang batas 50 adalah titik awal yang umum
    return len(good_matches)

# Fungsi simpan histori ke CSV
def simpan_histori(input_file, hasil_match, skor):
    with open(HISTORY_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), input_file, hasil_match, skor])

# Route halaman login
@app.route("/login.html", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if users.get(username) == password:
            session["user"] = username
            return redirect(url_for("index"))
        else:
            flash("Username atau password salah!")
    return render_template("login.html")

# Route logout
@app.route("/logout")
@login_required
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# Halaman utama: upload + pencocokan
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    result = None
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename != '': # Ditambahkan pemeriksaan untuk nama file kosong
            filename = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filename)

            best_score = 0
            best_match = None

            # Periksa apakah DATABASE_FOLDER ada dan berisi file
            if os.path.exists(DATABASE_FOLDER) and os.listdir(DATABASE_FOLDER):
                for db_file in os.listdir(DATABASE_FOLDER):
                    db_path = os.path.join(DATABASE_FOLDER, db_file)
                    # Pastikan itu adalah file, bukan direktori
                    if os.path.isfile(db_path):
                        score = match_fingerprint(filename, db_path)
                        if score > best_score:
                            best_score = score
                            best_match = db_file
            else:
                flash("Database sidik jari kosong atau tidak ditemukan.") # Beri tahu pengguna jika tidak ada gambar database

            # Sesuaikan ambang batas (misalnya, 20) berdasarkan kualitas gambar sidik jari Anda dan keketatan yang diinginkan
            status = "Cocok" if best_score > 20 else "Tidak cocok"
            simpan_histori(file.filename, best_match if best_match else "Tidak ada", best_score)

            result = {
                "input": file.filename,
                "match": best_match,
                "score": best_score,
                "status": status
            }
        else:
            flash("Tidak ada file yang dipilih.") # Beri tahu pengguna jika tidak ada file yang dipilih
    return render_template("index.html", result=result)

# Halaman histori pencocokan
@app.route("/history")
@login_required
def history():
    if not os.path.exists(HISTORY_FILE):
        data = []
    else:
        with open(HISTORY_FILE, newline="") as file:
            reader = csv.reader(file)
            data = list(reader)
    return render_template("history.html", data=data)

if __name__ == "__main__": # __name__ dan __main__ yang sudah dikoreksi
    app.run(debug=True)
