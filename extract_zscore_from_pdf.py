"""
Ekstraksi tabel Z-score (BB/U, PB/U, TB/U, BB/PB, BB/TB) dari PDF resmi
Peraturan Menteri Kesehatan RI Nomor 2 Tahun 2020 tentang Standar Antropometri Anak,
menjadi file CSV terstruktur (zscore_who_permenkes_2020.csv).

Sumber PDF: peraturan.bpk.go.id/Details/152505/permenkes-no-2-tahun-2020

Cara kerja:
1. Baca teks halaman 16-42 (lampiran tabel) pakai pypdf.
2. Kenali judul tiap tabel ("Tabel N. Standar ... (XX/X)") untuk menentukan indeks aktif.
3. Kenali label jenis kelamin ("Anak Laki-Laki"/"Anak Perempuan").
4. Cocokkan tiap baris data dengan pola: 1 nilai (umur/panjang/tinggi) + 7 nilai SD.
5. Simpan ke CSV, lalu terapkan koreksi manual untuk kesalahan baca yang sudah
   teridentifikasi lewat validasi silang terhadap tabel resmi WHO Excel (lihat
   crosscheck_who.py) -- ini SATU-SATUNYA sel yang perlu dikoreksi dari 730 baris,
   akibat artefak pemotongan digit saat parsing teks PDF.

Jalankan:
    python extract_zscore_from_pdf.py
"""

import re
import csv
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).parent
PDF_PATH = BASE_DIR / "Permenkes No 2 Tahun 2020 - Standar Antropometri Anak.pdf"
OUT_PATH = BASE_DIR / "zscore_who_permenkes_2020.csv"

# Koreksi manual: (indeks, jenis_kelamin, nilai_x) -> {kolom: nilai_benar}
# Ditemukan lewat validasi silang terhadap tabel resmi WHO Excel (crosscheck_who.py):
# baris ini terbaca "6." (bukan "6.3") akibat artefak pemotongan digit oleh pypdf.
KOREKSI_MANUAL = {
    ("BB/TB", "perempuan", "69.5"): {"sd3neg": "6.3"},
}

r = PdfReader(str(PDF_PATH))

text = ""
for i in range(15, 42):  # halaman 16-42 (0-indexed 15-41)
    text += r.pages[i].extract_text() + "\n"

lines = text.split("\n")

header_re = re.compile(r"Tabel\s+\d+\.\s+Standar\s+.*?\(([A-Za-z/]+)\)")
gender_re = re.compile(r"Anak\s+(Laki-[Ll]aki|[Pp]erempuan)", re.IGNORECASE)
row_re = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*\*?\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$"
)

xtype_map = {
    "BB/U": "umur_bulan",
    "PB/U": "umur_bulan",
    "TB/U": "umur_bulan",
    "BB/PB": "panjang_cm",
    "BB/TB": "tinggi_cm",
}

current_index = None
current_gender = None
skip = False
rows = []
anomalies = []

for ln in lines:
    ln = ln.strip()
    if not ln:
        continue
    hm = header_re.search(ln)
    if hm:
        code = hm.group(1)
        if code == "IMT/U":
            skip = True
            current_index = None
        else:
            skip = False
            current_index = code
        continue
    gm = gender_re.search(ln)
    if gm:
        g = gm.group(1).lower()
        current_gender = "laki-laki" if "laki" in g else "perempuan"
        continue
    if skip or current_index is None:
        continue
    rm = row_re.match(ln)
    if rm:
        x = rm.group(1)
        vals = rm.groups()[1:8]
        rows.append([current_index, current_gender, xtype_map[current_index], x] + list(vals))
    else:
        if re.match(r"^\d", ln) and current_index:
            anomalies.append((current_index, current_gender, ln))

print("Total rows parsed:", len(rows))
print("Anomalies:", len(anomalies))
for a in anomalies:
    print(" ANOMALY:", a)

kolom = ["indeks", "jenis_kelamin", "tipe_x", "nilai_x", "sd3neg", "sd2neg", "sd1neg", "median", "sd1pos", "sd2pos", "sd3pos"]

koreksi_terpakai = 0
for row in rows:
    key = (row[0], row[1], row[3])
    if key in KOREKSI_MANUAL:
        for kolom_nama, nilai_benar in KOREKSI_MANUAL[key].items():
            idx_kolom = kolom.index(kolom_nama)
            row[idx_kolom] = nilai_benar
        koreksi_terpakai += 1

print(f"Koreksi manual diterapkan: {koreksi_terpakai}/{len(KOREKSI_MANUAL)}")

with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(kolom)
    w.writerows(rows)
print("Saved to", OUT_PATH)

c = Counter((row[0], row[1]) for row in rows)
for k, v in sorted(c.items()):
    print(k, v)
