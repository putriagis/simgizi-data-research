"""
Uji rekomendasi_ai.py pakai baris ASLI dari dataset yang udah di-cleaning + divalidasi
(data_balita_cleaned_validated.csv) -- bukan data karangan.

Catatan: dataset ini cuma punya kolom Tinggi Badan (gak ada Berat Badan), jadi cuma
indeks TB/U atau PB/U yang bisa dihitung dari data ini (bukan BB/U atau BB/TB).
Nilai z_score & status yang dipakai = hasil hitung zscore.py yang udah divalidasi
99.13% akurat terhadap label dataset (lihat clean_validate.py).

Jalanin (GEMINI_API_KEY harus udah di-set di environment variable):
    python test_rekomendasi_data_asli.py
"""

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from rekomendasi_ai import generate_rekomendasi

DATA_PATH = Path(__file__).parent / "data_balita_cleaned_validated.csv"
JEDA_ANTAR_REQUEST_DETIK = 2  # cegah numpuk request beruntun -> kurangin risiko kena rate limit (429)

df = pd.read_csv(DATA_PATH)

# ambil 1 baris acak per kategori status gizi, biar variasinya kekover
sampel = df.groupby("status_gizi_dataset").sample(n=1, random_state=42).reset_index(drop=True)

for i, row in sampel.iterrows():
    if i > 0:
        time.sleep(JEDA_ANTAR_REQUEST_DETIK)
    umur = int(row["umur_bulan"])
    gender = row["jenis_kelamin"]
    indeks = "PB/U" if umur < 24 else "TB/U"

    print("=" * 70)
    print(f"Baris asli dataset: umur={umur}bln, {gender}, tinggi={row['tinggi_cm']:.1f}cm")
    print(f"Label dataset asli : {row['status_gizi_dataset']}")
    print("-" * 70)

    status_gizi_map = {
        indeks: {
            "z_score": row["z_score_hitung"],
            "status": row["status_gizi_hitung"],
        }
    }
    print(f"  {indeks}: Z={row['z_score_hitung']}  -> {row['status_gizi_hitung']}")

    rekomendasi = generate_rekomendasi(status_gizi_map, umur_bulan=umur, jenis_kelamin=gender)
    print(f"\n  tingkat_risiko : {rekomendasi['tingkat_risiko']}")
    print(f"  is_alert       : {rekomendasi['is_alert']}")
    print(f"  saran_tindak_lanjut:\n    {rekomendasi['saran_tindak_lanjut']}")
    print()
