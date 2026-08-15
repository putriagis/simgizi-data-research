"""
Uji coba beberapa skenario anak dengan status gizi berbeda-beda,
buat mastiin rekomendasi_ai.py konsisten (gak cuma bagus di 1 kasus doang).

Jalanin (GEMINI_API_KEY harus udah di-set di environment variable):
    python test_rekomendasi.py
"""

import json
from zscore import load_reference, nilai_gizi_anak
from rekomendasi_ai import generate_rekomendasi

# skenario: (label, umur_bulan, jenis_kelamin, berat_kg, tinggi_cm)
skenario = [
    ("Anak status gizi NORMAL",            18, "perempuan", 10.2, 79.0),
    ("Anak risiko UNDERWEIGHT ringan",     12, "laki-laki",  7.0, 74.0),
    ("Anak STUNTED (pendek)",              36, "laki-laki",  12.0, 88.0),
    ("Anak SEVERELY STUNTED + wasted",     24, "perempuan",  7.5, 74.0),
    ("Anak status TINGGI (di atas rata-rata)", 6, "laki-laki", 9.0, 74.0),
]

ref = load_reference()

for label, umur, gender, bb, tb in skenario:
    print("=" * 70)
    print(f"{label}  (umur={umur}bln, {gender}, BB={bb}kg, TB={tb}cm)")
    print("-" * 70)

    hasil_gizi = nilai_gizi_anak(ref, umur_bulan=umur, jenis_kelamin=gender,
                                  berat_kg=bb, panjang_tinggi_cm=tb)
    for indeks, info in hasil_gizi.items():
        print(f"  {indeks}: Z={info['z_score']:>6}  -> {info['status']}")

    rekomendasi = generate_rekomendasi(hasil_gizi, umur_bulan=umur, jenis_kelamin=gender)
    print(f"\n  tingkat_risiko : {rekomendasi['tingkat_risiko']}")
    print(f"  is_alert       : {rekomendasi['is_alert']}")
    print(f"  saran_tindak_lanjut:\n    {rekomendasi['saran_tindak_lanjut']}")
    print()
