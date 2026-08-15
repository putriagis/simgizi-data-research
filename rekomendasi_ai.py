"""
Modul rekomendasi AI (FR-04) SimGizi.
Ambil hasil Z-score dari zscore.py, generate saran tindak lanjut pakai LLM (Google Gemini API).

Gemini API gratis (free tier, gak perlu kartu kredit) -- daftar API key di
https://aistudio.google.com/ , tab "Get API Key".

Environment variable yang dibutuhkan:
    GEMINI_API_KEY=<api-key-kamu>

Cara pakai:
    from zscore import load_reference, nilai_gizi_anak
    from rekomendasi_ai import generate_rekomendasi

    ref = load_reference()
    hasil_gizi = nilai_gizi_anak(ref, umur_bulan=30, jenis_kelamin="laki-laki",
                                  berat_kg=10.5, panjang_tinggi_cm=85.0)
    rekomendasi = generate_rekomendasi(hasil_gizi, umur_bulan=30, jenis_kelamin="laki-laki")
"""

import os
import json
import time
import requests

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")  # alias -> otomatis ikut versi flash terbaru
GEMINI_MODEL_FALLBACK = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-flash-lite-latest")  # dicoba kalau model utama gagal terus (lebih ringan/jarang penuh)


def _url_model(model):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# --- Guardrail: system prompt yang MENGUNCI output AI ---
# Tujuannya: AI cuma boleh generate saran edukasi umum, gak boleh diagnosis medis,
# gak boleh keluar dari kategori status gizi yang UDAH dihitung rule-based (zscore.py).
SYSTEM_PROMPT = """Kamu adalah asisten edukasi gizi untuk petugas posyandu di Indonesia.

ATURAN KETAT:
1. Status gizi anak SUDAH ditentukan lewat perhitungan Z-score resmi (WHO/Permenkes No. 2/2020).
   Kamu TIDAK BOLEH mengubah, meragukan, atau mendiagnosis ulang status gizi tsb.
2. Tugasmu HANYA membuat saran tindak lanjut edukatif berbahasa Indonesia,
   berdasarkan status gizi yang diberikan.
3. DILARANG memberi diagnosis medis, resep obat, atau dosis suplemen spesifik.
4. Kalau status gizi mengindikasikan risiko (stunted/severely stunted/wasted/severely wasted),
   WAJIB sertakan anjuran rujuk ke tenaga kesehatan/puskesmas -- jangan cuma saran umum.
5. Jawaban singkat, maksimal 3-4 kalimat, bahasa mudah dipahami orang awam.
6. Jangan mengarang data, statistik, atau klaim medis yang tidak ada di input.

Format jawaban HARUS JSON valid, tanpa teks lain di luar JSON:
{"saran_tindak_lanjut": "..."}
"""


def tentukan_tingkat_risiko(status_gizi_map):
    """Tentukan level risiko keseluruhan dari kombinasi status BB/U, TB-atau-PB/U, BB/TB-atau-BB/PB."""
    statuses = [v["status"] for v in status_gizi_map.values()]
    tinggi_keywords = ["sangat kurang", "sangat pendek", "severely", "gizi buruk"]
    sedang_keywords = ["kurang", "pendek", "wasted", "stunted"]

    if any(any(k in s.lower() for k in tinggi_keywords) for s in statuses):
        return "tinggi"
    if any(any(k in s.lower() for k in sedang_keywords) for s in statuses):
        return "sedang"
    return "rendah"


def tentukan_alert(tingkat_risiko):
    return tingkat_risiko in ("sedang", "tinggi")


def _build_user_prompt(status_gizi_map, umur_bulan, jenis_kelamin, tingkat_risiko):
    ringkasan = "\n".join(
        f"- {indeks}: Z-score={info['z_score']}, status={info['status']}"
        for indeks, info in status_gizi_map.items()
    )
    return (
        f"Data anak:\n"
        f"- Umur: {umur_bulan} bulan\n"
        f"- Jenis kelamin: {jenis_kelamin}\n"
        f"- Tingkat risiko keseluruhan: {tingkat_risiko}\n\n"
        f"Hasil perhitungan status gizi (SUDAH FINAL, jangan diubah):\n{ringkasan}\n\n"
        f"Buatkan saran tindak lanjut sesuai aturan sistem."
    )


def generate_rekomendasi(status_gizi_map, umur_bulan, jenis_kelamin, api_key=None, dry_run=False):
    """
    status_gizi_map: output dari zscore.nilai_gizi_anak()
    dry_run=True -> gak panggil API, cuma return prompt yang akan dikirim (buat testing/demo tanpa API key)
    """
    tingkat_risiko = tentukan_tingkat_risiko(status_gizi_map)
    is_alert = tentukan_alert(tingkat_risiko)
    user_prompt = _build_user_prompt(status_gizi_map, umur_bulan, jenis_kelamin, tingkat_risiko)

    if dry_run:
        return {
            "tingkat_risiko": tingkat_risiko,
            "is_alert": is_alert,
            "saran_tindak_lanjut": None,
            "_dry_run_prompt": {"system": SYSTEM_PROMPT, "user": user_prompt},
        }

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY belum di-set. Set environment variable atau pass api_key=...")

    saran = None
    error_terakhir = None
    percobaan_per_model = 2
    daftar_model = [GEMINI_MODEL, GEMINI_MODEL_FALLBACK]

    for model in daftar_model:
        for percobaan in range(1, percobaan_per_model + 1):
            try:
                resp = requests.post(
                    _url_model(model),
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={
                        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,  # rendah -> jawaban lebih konsisten, kurang "kreatif"/ngarang
                            "responseMimeType": "application/json",
                        },
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(content)
                saran = parsed["saran_tindak_lanjut"]
                break  # sukses -> keluar dari loop retry model ini
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                error_terakhir = f"[{model}] HTTP {status}: {e.response.text[:300] if e.response is not None else e}"
                bisa_retry = status in (429, 500, 502, 503, 504)
            except requests.exceptions.Timeout as e:
                error_terakhir = f"[{model}] Timeout: {e}"
                bisa_retry = True
            except requests.exceptions.RequestException as e:
                error_terakhir = f"[{model}] Request error: {e}"
                bisa_retry = False
            except (json.JSONDecodeError, KeyError) as e:
                error_terakhir = f"[{model}] Gagal parse response JSON dari model: {e}"
                bisa_retry = False

            if bisa_retry and percobaan < percobaan_per_model:
                tunggu = 5 * percobaan
                print(f"  [retry {model} #{percobaan}] {error_terakhir} -> tunggu {tunggu}s")
                time.sleep(tunggu)
                continue
            break  # gagal & gak layak retry lagi di model ini -> lanjut ke model fallback
        if saran is not None:
            break  # sukses -> gak perlu coba model fallback

    if saran is None:
        print(f"  [GAGAL] {error_terakhir}")
        # fallback kalau API gagal terus / model gak patuh format JSON -- jangan crash sistem
        saran = "Saran tidak dapat dibuat otomatis. Mohon konsultasikan langsung ke tenaga kesehatan."

    return {
        "tingkat_risiko": tingkat_risiko,
        "is_alert": is_alert,
        "saran_tindak_lanjut": saran,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from zscore import load_reference, nilai_gizi_anak

    ref = load_reference()
    hasil_gizi = nilai_gizi_anak(
        ref, umur_bulan=30, jenis_kelamin="laki-laki", berat_kg=9.5, panjang_tinggi_cm=80.0
    )
    print("Hasil zscore.py:")
    for k, v in hasil_gizi.items():
        print(f"  {k}: {v}")

    ada_key = bool(os.environ.get("GEMINI_API_KEY"))
    hasil = generate_rekomendasi(
        hasil_gizi, umur_bulan=30, jenis_kelamin="laki-laki", dry_run=not ada_key
    )

    print("\nHasil rekomendasi AI:")
    print(json.dumps(hasil, indent=2, ensure_ascii=False))

    if not ada_key:
        print("\n[INFO] GEMINI_API_KEY belum di-set -> mode dry_run, gak manggil API beneran.")
        print("Set environment variable GEMINI_API_KEY buat coba panggilan API asli.")
