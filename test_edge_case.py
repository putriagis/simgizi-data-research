"""
Uji kasus batas (edge case) buat zscore.py + nilai_gizi_anak().

Dua sumber skenario:
1. BATAS UMUR (24 bulan, 0 bulan, 59 bulan) -> ambil baris ASLI dari
   data_balita_cleaned_validated.csv, karena dataset beneran punya baris di umur-umur itu.
2. INPUT RUSAK/EKSTREM (kosong, salah format, di luar rentang) -> HARUS dibuat manual,
   karena dataset yang udah di-cleaning sengaja gak punya baris rusak kayak gitu
   (justru itu yang dibuang pas proses cleaning kemarin).

Jalanin:
    python test_edge_case.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from zscore import load_reference, hitung_zscore, nilai_gizi_anak

ref = load_reference()
DATA_PATH = Path(__file__).parent / "data_balita_cleaned_validated.csv"


def cetak_hasil(judul, fn):
    print("=" * 70)
    print(judul)
    print("-" * 70)
    try:
        hasil = fn()
        print("HASIL:", hasil)
    except Exception as e:
        print(f"EXCEPTION ({type(e).__name__}): {e}")
    print()


# ============================================================
# GROUP A: batas umur -- pakai baris ASLI dari dataset
# ============================================================
df = pd.read_csv(DATA_PATH)

for umur_target in [0, 24, 59]:
    baris_tersedia = df[df["umur_bulan"] == umur_target]
    if baris_tersedia.empty:
        print(f"[SKIP] Gak ada baris umur={umur_target} di dataset\n")
        continue
    row = baris_tersedia.iloc[0]
    indeks = "PB/U" if umur_target < 24 else "TB/U"

    cetak_hasil(
        f"[DATA ASLI] Umur tepat {umur_target} bulan -> harus pilih indeks {indeks} "
        f"(dari dataset: {row['jenis_kelamin']}, tinggi={row['tinggi_cm']:.1f}cm)",
        lambda r=row, idx=indeks, u=umur_target: hitung_zscore(
            ref, idx, r["jenis_kelamin"], u, r["tinggi_cm"]
        ),
    )

# ============================================================
# GROUP B: input rusak/ekstrem -- DIBUAT MANUAL (dataset gak punya ini)
# ============================================================
cetak_hasil(
    "[MANUAL] Tinggi badan kosong (None)",
    lambda: hitung_zscore(ref, "TB/U", "laki-laki", 30, None),
)

cetak_hasil(
    "[MANUAL] Jenis kelamin salah format ('Laki-Laki' kapital)",
    lambda: hitung_zscore(ref, "TB/U", "Laki-Laki", 30, 85.0),
)

cetak_hasil(
    "[MANUAL] Umur di luar rentang tabel (65 bulan)",
    lambda: hitung_zscore(ref, "BB/U", "laki-laki", 65, 15.0),
)

cetak_hasil(
    "[MANUAL] Umur negatif (-1 bulan, human error input)",
    lambda: hitung_zscore(ref, "BB/U", "laki-laki", -1, 4.0),
)

cetak_hasil(
    "[MANUAL] Nilai ukur berupa teks (typo petugas input '12kg' bukan angka)",
    lambda: hitung_zscore(ref, "BB/U", "laki-laki", 12, "12kg"),
)

cetak_hasil(
    "[MANUAL] Kombinasi lengkap nilai_gizi_anak() dengan BB & TB ekstrem "
    "(anak sangat kurus & sangat pendek sekaligus)",
    lambda: nilai_gizi_anak(ref, umur_bulan=36, jenis_kelamin="perempuan",
                             berat_kg=6.0, panjang_tinggi_cm=75.0),
)
