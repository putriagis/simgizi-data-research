# SimGizi — Modul AI & Data Research

Sistem Informasi Gizi Anak dan Deteksi Dini Stunting. Folder ini berisi seluruh hasil kerja divisi **Data Research** untuk kompetisi CCI The Hack Intelliweb 2026: sumber data acuan, mesin kalkulasi status gizi, modul rekomendasi AI, beserta bukti pengujian dan validasinya.

## Ringkasan

SimGizi membantu petugas posyandu mendeteksi dini risiko stunting dan gizi buruk pada balita (0–59 bulan) melalui otomatisasi perhitungan Z-score (standar WHO/Permenkes) dan rekomendasi tindak lanjut berbasis AI generatif.

Komponen AI dalam produk ini terbagi dua:
1. **Mesin kalkulasi status gizi** — rule-based, deterministik, mengikuti standar resmi.
2. **Modul rekomendasi generatif** — Large Language Model (Google Gemini API), menghasilkan saran tindak lanjut berbahasa Indonesia.

## Alur Pipeline

```
Sumber data acuan resmi (PDF Permenkes No. 2/2020)
        │
        ▼
Ekstraksi otomatis → CSV terstruktur      (extract_zscore_from_pdf.py)
        │
        ▼
Validasi silang terhadap WHO Excel        (crosscheck_who.py)  →  100% cocok (730/730 baris)
        │
        ▼
Mesin kalkulasi Z-score & status gizi     (zscore.py)
        │
        ▼
Validasi terhadap dataset independen      (clean_validate.py)  →  99,13% akurasi (39.425 baris uji)
        │
        ▼
Pengujian kasus batas & input tidak valid (test_edge_case.py)  →  7/7 skenario lolos
        │
        ▼
Modul rekomendasi AI generatif            (rekomendasi_ai.py)  →  Google Gemini API
        │
        ▼
Pengujian reliabilitas API                (test_rekomendasi_data_asli.py)
```

## Daftar File

| File | Keterangan |
|---|---|
| `Permenkes No 2 Tahun 2020 - Standar Antropometri Anak.pdf` | Sumber hukum resmi (Kementerian Kesehatan RI), diunduh dari database resmi peraturan.bpk.go.id |
| `extract_zscore_from_pdf.py` | Script ekstraksi tabel Z-score dari PDF menjadi CSV terstruktur |
| `zscore_who_permenkes_2020.csv` | Hasil ekstraksi: 730 baris tabel referensi (5 indeks × 2 jenis kelamin), tervalidasi 100% terhadap WHO |
| `who_excel_official/` | Tabel Excel resmi WHO Child Growth Standards, dipakai sebagai pembanding validasi |
| `zscore.py` | Mesin kalkulasi Z-score dan klasifikasi status gizi (rule-based) |
| `rekomendasi_ai.py` | Modul pemanggil LLM (Gemini API) untuk menghasilkan saran tindak lanjut |
| `data_balita.csv` | Dataset uji sintetis dari Kaggle (121.000 baris, sebelum dibersihkan) |
| `clean_validate.py` | Script pembersihan data + validasi silang mesin kalkulasi terhadap dataset uji |
| `data_balita_cleaned_validated.csv` | Dataset uji setelah dibersihkan (39.425 baris) beserta hasil validasi |
| `test_edge_case.py` | Pengujian kasus batas (usia kritis, input tidak valid, nilai ekstrem) |
| `test_rekomendasi.py` / `test_rekomendasi_data_asli.py` | Pengujian modul rekomendasi AI dengan berbagai skenario status gizi |
| `README_HANDOFF_WEBDEV.md` | Panduan integrasi modul untuk tim Web Development |
| `BAB_II_F_Kebutuhan_AI.md` | Draf isi laporan PRD bagian Kebutuhan AI |

## Ringkasan Hasil Kerja

| Aspek yang diuji | Hasil |
|---|---|
| Validasi tabel referensi terhadap sumber resmi WHO | 730/730 baris cocok (100%) |
| Akurasi mesin kalkulasi terhadap dataset uji independen | 99,13% (39.082/39.425 baris) |
| Pengujian kasus batas (edge case) | 7/7 skenario tertangani dengan benar |
| Reliabilitas pemanggilan API AI generatif setelah perbaikan retry/fallback | Naik dari 50% menjadi 100% keberhasilan |

## Cara Menjalankan Ulang (Reproducibility)

Dibutuhkan Python 3.13+ dengan dependency: `pypdf`, `pandas`, `openpyxl`, `requests`.

```bash
# 1. Ekstraksi tabel referensi dari PDF resmi
python extract_zscore_from_pdf.py

# 2. Validasi silang terhadap WHO (opsional, butuh file di folder who_excel_official/)
python crosscheck_who.py

# 3. Bersihkan dataset uji dan validasi mesin kalkulasi
python clean_validate.py

# 4. Uji kasus batas
python test_edge_case.py

# 5. Uji modul rekomendasi AI (butuh environment variable GEMINI_API_KEY)
python test_rekomendasi_data_asli.py
```

## Sumber Data

- **Peraturan Menteri Kesehatan RI Nomor 2 Tahun 2020** tentang Standar Antropometri Anak — [peraturan.bpk.go.id](https://peraturan.bpk.go.id/Details/152505/permenkes-no-2-tahun-2020)
- **WHO Child Growth Standards** — [who.int/tools/child-growth-standards](https://www.who.int/tools/child-growth-standards)
- **Stunting Toddler (Balita) Detection Dataset** (Kaggle, lisensi MIT) — dataset sintetis untuk pengujian sistem
