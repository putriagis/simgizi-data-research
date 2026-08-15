"""
Kalkulasi Z-score status gizi anak (0-59 bulan) berdasar Permenkes No. 2 Tahun 2020.
Butuh file referensi: zscore_who_permenkes_2020.csv (satu folder sama file ini).
"""

import csv
from pathlib import Path

REF_CSV = Path(__file__).parent / "zscore_who_permenkes_2020.csv"


def load_reference(csv_path=REF_CSV):
    """Load tabel referensi jadi dict {(indeks, jenis_kelamin): [baris...]} terurut nilai_x."""
    ref = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["indeks"], row["jenis_kelamin"])
            ref.setdefault(key, []).append({
                "x": float(row["nilai_x"]),
                "sd3neg": float(row["sd3neg"]),
                "sd2neg": float(row["sd2neg"]),
                "sd1neg": float(row["sd1neg"]),
                "median": float(row["median"]),
                "sd1pos": float(row["sd1pos"]),
                "sd2pos": float(row["sd2pos"]),
                "sd3pos": float(row["sd3pos"]),
            })
    for rows in ref.values():
        rows.sort(key=lambda r: r["x"])
    return ref


def _interpolasi(rows, x):
    """Interpolasi linear antar baris tabel terdekat kalau nilai_x gak persis ada di tabel."""
    if x <= rows[0]["x"]:
        return rows[0]
    if x >= rows[-1]["x"]:
        return rows[-1]
    for lo, hi in zip(rows, rows[1:]):
        if lo["x"] <= x <= hi["x"]:
            frac = 0.0 if hi["x"] == lo["x"] else (x - lo["x"]) / (hi["x"] - lo["x"])
            return {k: lo[k] + frac * (hi[k] - lo[k]) for k in lo if k != "x"}
    return rows[-1]


def hitung_zscore(ref, indeks, jenis_kelamin, nilai_x, nilai_ukur):
    """
    indeks: 'BB/U' | 'PB/U' | 'TB/U' | 'BB/PB' | 'BB/TB'
    jenis_kelamin: 'laki-laki' | 'perempuan'
    nilai_x: umur (bulan) untuk BB/U,PB/U,TB/U -- atau panjang/tinggi (cm) untuk BB/PB,BB/TB
    nilai_ukur: hasil ukur aktual anak (kg untuk *berat, cm untuk *panjang/tinggi)
    """
    key = (indeks, jenis_kelamin)
    if key not in ref:
        raise ValueError(f"Tidak ada data referensi untuk indeks={indeks}, jenis_kelamin={jenis_kelamin}")

    if nilai_x is None or nilai_ukur is None:
        raise ValueError(
            f"Input tidak boleh kosong (nilai_x={nilai_x!r}, nilai_ukur={nilai_ukur!r}) "
            f"untuk indeks={indeks}"
        )
    try:
        nilai_x = float(nilai_x)
        nilai_ukur = float(nilai_ukur)
    except (TypeError, ValueError):
        raise ValueError(f"nilai_x dan nilai_ukur harus berupa angka, dapat: {nilai_x!r}, {nilai_ukur!r}")

    x_min, x_max = ref[key][0]["x"], ref[key][-1]["x"]
    if not (x_min <= nilai_x <= x_max):
        raise ValueError(
            f"nilai_x={nilai_x} di luar rentang tabel referensi {indeks} ({x_min}-{x_max}). "
            f"Cek kembali input umur/tinggi -- bisa jadi typo atau anak di luar target usia (0-59 bulan)."
        )

    baris = _interpolasi(ref[key], nilai_x)
    median = baris["median"]

    if nilai_ukur >= median:
        sd = baris["sd1pos"] - median
    else:
        sd = median - baris["sd1neg"]

    if sd == 0:
        return 0.0
    return round((nilai_ukur - median) / sd, 2)


def klasifikasi_status_gizi(indeks, z):
    """Klasifikasi status gizi sesuai ambang batas Permenkes No. 2/2020."""
    if indeks == "BB/U":
        if z < -3:
            return "Berat badan sangat kurang (severely underweight)"
        if z < -2:
            return "Berat badan kurang (underweight)"
        if z <= 1:
            return "Berat badan normal"
        return "Risiko berat badan lebih"

    if indeks in ("PB/U", "TB/U"):
        if z < -3:
            return "Sangat pendek (severely stunted)"
        if z < -2:
            return "Pendek (stunted)"
        if z <= 3:
            return "Normal"
        return "Tinggi"

    if indeks in ("BB/PB", "BB/TB"):
        if z < -3:
            return "Gizi buruk (severely wasted)"
        if z < -2:
            return "Gizi kurang (wasted)"
        if z <= 1:
            return "Gizi baik (normal)"
        if z <= 2:
            return "Risiko gizi lebih"
        if z <= 3:
            return "Gizi lebih"
        return "Obesitas"

    raise ValueError(f"Indeks tidak dikenal: {indeks}")


def nilai_gizi_anak(ref, umur_bulan, jenis_kelamin, berat_kg, panjang_tinggi_cm, posisi_ukur=None):
    """
    Hitung status gizi lengkap (BB/U, TB-atau-PB/U, BB/TB-atau-BB/PB) dari satu sesi pengukuran.

    posisi_ukur: 'telentang' atau 'berdiri'. Kalau None, dipilih otomatis dari umur
      (< 24 bulan -> telentang/PB, >= 24 bulan -> berdiri/TB), sesuai keterangan tabel resmi.
    """
    if posisi_ukur is None:
        posisi_ukur = "telentang" if umur_bulan < 24 else "berdiri"

    indeks_panjang = "PB/U" if posisi_ukur == "telentang" else "TB/U"
    indeks_bb_panjang = "BB/PB" if posisi_ukur == "telentang" else "BB/TB"

    z_bbu = hitung_zscore(ref, "BB/U", jenis_kelamin, umur_bulan, berat_kg)
    z_pbu = hitung_zscore(ref, indeks_panjang, jenis_kelamin, umur_bulan, panjang_tinggi_cm)
    z_bbpb = hitung_zscore(ref, indeks_bb_panjang, jenis_kelamin, panjang_tinggi_cm, berat_kg)

    return {
        "BB/U": {"z_score": z_bbu, "status": klasifikasi_status_gizi("BB/U", z_bbu)},
        indeks_panjang: {"z_score": z_pbu, "status": klasifikasi_status_gizi(indeks_panjang, z_pbu)},
        indeks_bb_panjang: {"z_score": z_bbpb, "status": klasifikasi_status_gizi(indeks_bb_panjang, z_bbpb)},
    }


if __name__ == "__main__":
    ref = load_reference()

    # Contoh: anak laki-laki, umur 30 bulan, BB 10.5 kg, TB 85.0 cm
    hasil = nilai_gizi_anak(ref, umur_bulan=30, jenis_kelamin="laki-laki",
                             berat_kg=10.5, panjang_tinggi_cm=85.0)

    for indeks, info in hasil.items():
        print(f"{indeks}: Z-score = {info['z_score']}  ->  {info['status']}")
