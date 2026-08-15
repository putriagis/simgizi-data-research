# Handoff Modul AI SimGizi — untuk Tim Web Development

Dokumen ini menjelaskan cara mengintegrasikan modul kalkulasi status gizi dan rekomendasi AI (hasil kerja divisi Data Research) ke dalam backend aplikasi SimGizi.

## File yang perlu diambil

Hanya 3 file ini yang dibutuhkan untuk produksi (file lain seperti `test_*.py` dan `clean_validate.py` hanya dipakai untuk pengujian internal, tidak perlu diikutsertakan ke backend):

| File | Fungsi |
|---|---|
| `zscore_who_permenkes_2020.csv` | Tabel referensi Z-score resmi (730 baris). Wajib ada satu folder dengan `zscore.py`. |
| `zscore.py` | Mesin kalkulasi Z-score dan klasifikasi status gizi (rule-based). |
| `rekomendasi_ai.py` | Modul pemanggil AI generatif (Gemini API) untuk membuat saran tindak lanjut. |

## Dependency yang dibutuhkan

```
pip install requests
```
(`zscore.py` dan `rekomendasi_ai.py` hanya membutuhkan `requests`, tidak butuh `pandas` — itu cuma dipakai di script pengujian.)

## Environment variable

```
GEMINI_API_KEY=<api-key-dari-aistudio.google.com>
```
Wajib di-set di server tempat backend berjalan. Tanpa ini, `generate_rekomendasi()` akan melempar `RuntimeError`.

## Cara pakai — alur lengkap satu sesi pengukuran

```python
from zscore import load_reference, nilai_gizi_anak
from rekomendasi_ai import generate_rekomendasi

# 1. Load tabel referensi (cukup sekali saat backend start, jangan load ulang tiap request)
ref = load_reference()

# 2. Input dari form pencatatan (FR-02)
umur_bulan = 30
jenis_kelamin = "laki-laki"   # HARUS persis "laki-laki" atau "perempuan", lowercase
berat_kg = 10.5
tinggi_cm = 85.0

# 3. Hitung Z-score + status gizi (FR-03)
hasil_gizi = nilai_gizi_anak(ref, umur_bulan, jenis_kelamin, berat_kg, tinggi_cm)
# -> {'BB/U': {'z_score': ..., 'status': ...}, 'TB/U': {...}, 'BB/TB': {...}}

# 4. Generate rekomendasi AI (FR-04)
rekomendasi = generate_rekomendasi(hasil_gizi, umur_bulan, jenis_kelamin)
# -> {'tingkat_risiko': 'rendah'|'sedang'|'tinggi', 'is_alert': bool, 'saran_tindak_lanjut': str}
```

## Pemetaan ke skema database (ERD)

Field hasil dua fungsi di atas langsung cocok disimpan ke entitas berikut sesuai ERD yang sudah dirancang di BAB III:

**Tabel `Pengukuran`**
- `z_score_bb_u`, `z_score_tb_u`, `z_score_bb_tb` ← dari `hasil_gizi[indeks]['z_score']`

**Tabel `Rekomendasi AI`**
- `status_gizi` ← dari `hasil_gizi[indeks]['status']`
- `tingkat_risiko` ← `rekomendasi['tingkat_risiko']`
- `saran_tindak_lanjut` ← `rekomendasi['saran_tindak_lanjut']`
- `is_alert` ← `rekomendasi['is_alert']` (dipakai langsung untuk Fitur Peringatan Dini FR-06 dan Dashboard Monitoring FR-09)

## Penanganan error yang perlu ditangani di sisi backend

`nilai_gizi_anak()` / `hitung_zscore()` bisa melempar `ValueError` dengan pesan yang sudah jelas (bukan crash tanpa keterangan) untuk kasus:
- Input kosong/`None`
- Input bukan angka (misal salah ketik)
- Umur di luar rentang 0–60 bulan
- Jenis kelamin dengan format tidak baku (harus persis `"laki-laki"` atau `"perempuan"`, lowercase)

**Wajib** dibungkus `try/except ValueError` di endpoint API, lalu tampilkan pesan errornya ke frontend supaya petugas tahu bagian mana yang perlu diperbaiki — jangan biarkan error ini menyebabkan response 500 generik.

`generate_rekomendasi()` **tidak akan pernah crash** karena kegagalan API AI generatif (sudah ada retry otomatis, fallback model kedua, dan fallback pesan aman) — jadi tidak perlu dibungkus penanganan error tambahan untuk skenario itu.

## Catatan performa

- `load_reference()` membaca file CSV dan cukup dipanggil **satu kali** saat aplikasi backend start (bukan setiap request), karena hasilnya bisa dipakai berulang.
- `generate_rekomendasi()` melakukan pemanggilan API eksternal dan bisa memakan waktu 1–5 detik (lebih lama jika terjadi retry). Pastikan endpoint yang memanggilnya bersifat asynchronous atau punya timeout yang wajar di sisi frontend.
