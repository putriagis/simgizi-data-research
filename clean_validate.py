"""
Cleaning + validasi silang dataset data_balita.csv (Kaggle, sintetis) terhadap
mesin kalkulasi Z-score resmi (zscore.py + tabel referensi Permenkes No. 2/2020).

Output: data_balita_cleaned_validated.csv (baris bersih + kolom hasil cross-check)
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zscore import load_reference

RAW_PATH = Path(__file__).parent / "data_balita.csv"
OUT_PATH = Path(__file__).parent / "data_balita_cleaned_validated.csv"

df = pd.read_csv(RAW_PATH)
df.columns = ["umur_bulan", "jenis_kelamin", "tinggi_cm", "status_gizi_dataset"]
n0 = len(df)
print("=== CLEANING ===")
print(f"Baris awal: {n0}")

# 1. Duplikat
dup_count = df.duplicated().sum()
df = df.drop_duplicates().reset_index(drop=True)
print(f"Duplikat dibuang: {dup_count}  -> sisa: {len(df)}")

# 2. Missing value
null_count = df.isnull().sum().sum()
df = df.dropna().reset_index(drop=True)
print(f"Baris missing value dibuang: {null_count}  -> sisa: {len(df)}")

# 3. Range check umur (0-59 bulan sesuai target SimGizi; dataset punya s.d. 60)
before = len(df)
df = df[(df["umur_bulan"] >= 0) & (df["umur_bulan"] <= 60)].reset_index(drop=True)
print(f"Umur di luar 0-60 bulan dibuang: {before - len(df)}  -> sisa: {len(df)}")

# 4. Range check tinggi badan wajar (30-135 cm, longgar biar gak buang kasus ekstrem sah)
before = len(df)
df = df[(df["tinggi_cm"] >= 30) & (df["tinggi_cm"] <= 135)].reset_index(drop=True)
print(f"Tinggi badan di luar rentang wajar dibuang: {before - len(df)}  -> sisa: {len(df)}")

# 5. Normalisasi jenis_kelamin & status_gizi (lowercase, strip)
df["jenis_kelamin"] = df["jenis_kelamin"].str.strip().str.lower()
df["status_gizi_dataset"] = df["status_gizi_dataset"].str.strip().str.lower()

valid_gender = {"laki-laki", "perempuan"}
before = len(df)
df = df[df["jenis_kelamin"].isin(valid_gender)].reset_index(drop=True)
print(f"Jenis kelamin gak valid dibuang: {before - len(df)}  -> sisa: {len(df)}")

valid_status = {"normal", "stunted", "severely stunted", "tinggi"}
before = len(df)
df = df[df["status_gizi_dataset"].isin(valid_status)].reset_index(drop=True)
print(f"Status gizi gak valid dibuang: {before - len(df)}  -> sisa: {len(df)}")

print(f"\nTotal baris bersih: {len(df)} dari {n0} ({len(df) / n0 * 100:.1f}%)")

# === VALIDASI: hitung ulang Z-score pakai zscore.py, bandingin ke label dataset ===
print("\n=== VALIDASI (cross-check vs zscore.py) ===")
ref = load_reference()


def indeks_untuk_umur(umur):
    return "PB/U" if umur < 24 else "TB/U"


def hitung_z_row(umur, gender, tinggi):
    idx = indeks_untuk_umur(umur)
    rows = ref[(idx, gender)]
    # umur integer selalu persis ada di tabel (0-60), jadi lookup langsung tanpa interpolasi
    baris = next(r for r in rows if r["x"] == float(umur))
    median = baris["median"]
    if tinggi >= median:
        sd = baris["sd1pos"] - median
    else:
        sd = median - baris["sd1neg"]
    return round((tinggi - median) / sd, 2)


def klasifikasi(z):
    if z < -3:
        return "severely stunted"
    if z < -2:
        return "stunted"
    if z <= 3:
        return "normal"
    return "tinggi"


df["z_score_hitung"] = df.apply(
    lambda r: hitung_z_row(r["umur_bulan"], r["jenis_kelamin"], r["tinggi_cm"]), axis=1
)
df["status_gizi_hitung"] = df["z_score_hitung"].apply(klasifikasi)
df["cocok"] = df["status_gizi_hitung"] == df["status_gizi_dataset"]

akurasi = df["cocok"].mean() * 100
print(f"Akurasi kecocokan zscore.py vs label dataset: {akurasi:.2f}%  ({df['cocok'].sum()}/{len(df)})")

print("\nConfusion (dataset label -> hasil hitung zscore.py):")
print(pd.crosstab(df["status_gizi_dataset"], df["status_gizi_hitung"]))

mismatch = df[~df["cocok"]]
print(f"\nContoh baris TIDAK cocok ({len(mismatch)} total):")
print(mismatch.head(10).to_string(index=False))

df.to_csv(OUT_PATH, index=False)
print(f"\nSaved: {OUT_PATH}")
