"""Logika halaman Manajemen Data: validasi berkas CSV, penandaan harga curiga, dan penyimpanan ke database.

Modul ini tidak bergantung pada Streamlit, jadi validasinya bisa diuji sendiri.
"""
import pandas as pd

KOLOM_WAJIB = ["tanggal", "pasar", "komoditas", "harga"]      # kolom lain (kelompok, satuan) boleh ada
RASIO_CURIGA = (0.2, 5.0)                                     # harga <= 0,2x atau >= 5x median komoditas = curiga

TEMPLAT_CSV = (
    "tanggal,pasar,kelompok,komoditas,satuan,harga\n"
    "2026-09-01,Pabean,SAYUR-SAYURAN,Tomat,Kg,9000\n"
    "2026-09-01,Kembang,SAYUR-SAYURAN,Tomat,Kg,8500\n"
)


def validasi(df: pd.DataFrame, pasar_ok, satuan_komoditas: dict):
    """Periksa isi berkas.

    Mengembalikan (bersih, ditolak, dilewati):
      bersih    : baris valid (tanggal, pasar, komoditas, harga) siap disimpan
      ditolak   : baris bermasalah beserta kolom `alasan`
      dilewati  : jumlah baris yang harganya kosong atau "-" (dianggap tidak ada harga)
    """
    df = df.copy()
    df.columns = [str(c).strip().lower().lstrip("﻿") for c in df.columns]
    hilang = [c for c in KOLOM_WAJIB if c not in df.columns]
    if hilang:
        raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(hilang) + ". Gunakan templat CSV.")

    df = df.reset_index(drop=True)
    df["baris"] = df.index + 2                                   # nomor baris di berkas (baris 1 = judul kolom)
    df["pasar"] = df["pasar"].astype(str).str.strip()
    df["komoditas"] = df["komoditas"].astype(str).str.strip()

    teks_harga = df["harga"].astype(str).str.strip()
    kosong = teks_harga.isin(["", "-", "nan", "None", "NaN"])
    dilewati = int(kosong.sum())
    df = df[~kosong].copy()

    tgl = pd.to_datetime(df["tanggal"], errors="coerce", format="ISO8601")
    harga = pd.to_numeric(df["harga"].astype(str).str.strip(), errors="coerce")
    df["tanggal_dt"], df["harga_num"] = tgl, harga

    alasan = pd.Series("", index=df.index, dtype=object)

    def tandai(mask, pesan):
        nonlocal alasan
        alasan = alasan.where((alasan != "") | ~mask, pesan)

    tandai(df["tanggal_dt"].isna(), "tanggal tidak valid (gunakan format YYYY-MM-DD)")
    tandai(~df["pasar"].isin(set(pasar_ok)), "pasar tidak dikenal")
    tandai(~df["komoditas"].isin(satuan_komoditas), "komoditas tidak dikenal")
    tandai(df["harga_num"].isna() | (df["harga_num"] <= 0), "harga bukan angka positif")
    if "satuan" in df.columns:
        satuan_db = df["komoditas"].map(satuan_komoditas)
        satuan_file = df["satuan"].astype(str).str.strip()
        tandai((satuan_file != "") & satuan_db.notna() & (satuan_file.str.lower() != satuan_db.astype(str).str.lower()),
               "satuan berbeda dengan database")
    valid = alasan == ""
    kunci = df.loc[valid, ["tanggal_dt", "pasar", "komoditas"]]
    dobel = kunci.duplicated(keep="last")
    tandai(df.index.isin(dobel[dobel].index), "duplikat di dalam berkas (baris lain memakai tanggal, pasar, komoditas yang sama)")

    ditolak = df.loc[alasan != "", ["baris", "tanggal", "pasar", "komoditas", "harga"]].assign(alasan=alasan[alasan != ""])
    bersih = (df.loc[alasan == "", ["baris", "tanggal_dt", "pasar", "komoditas", "harga_num"]]
                .rename(columns={"tanggal_dt": "tanggal", "harga_num": "harga"}).reset_index(drop=True))
    bersih["tanggal"] = bersih["tanggal"].dt.date
    bersih["harga"] = bersih["harga"].round(2)
    return bersih, ditolak.reset_index(drop=True), dilewati


def tandai_curiga(bersih: pd.DataFrame, median_acuan: dict) -> pd.DataFrame:
    """Baris valid yang harganya jauh dari median komoditas (kemungkinan salah ketik, mis. kelebihan satu nol)."""
    if bersih.empty:
        return bersih.assign(median_acuan=[], rasio=[])
    m = bersih["komoditas"].map(median_acuan)
    rasio = (bersih["harga"] / m).round(2)
    kena = (rasio <= RASIO_CURIGA[0]) | (rasio >= RASIO_CURIGA[1])
    return bersih.assign(median_acuan=m.round(0), rasio=rasio)[kena]


# ---------- penyimpanan ke database ----------
SQL_KALENDER = """
INSERT INTO dw.dim_tanggal (tanggal_key, tanggal, tahun, kuartil, bulan, nama_bulan, hari, nama_hari, akhir_pekan, ada_data, alasan_tanpa_data)
SELECT to_char(k.d, 'YYYYMMDD')::int, k.d, extract(year FROM k.d)::int, extract(quarter FROM k.d)::int, extract(month FROM k.d)::int,
       (ARRAY['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'])[extract(month FROM k.d)::int],
       extract(day FROM k.d)::int,
       (ARRAY['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu'])[extract(isodow FROM k.d)::int],
       extract(isodow FROM k.d) >= 6, FALSE, NULL
FROM (SELECT d::date AS d FROM generate_series(
          LEAST(CAST(:awal AS date), (SELECT min(tanggal) FROM dw.dim_tanggal)),
          GREATEST(CAST(:akhir AS date), (SELECT max(tanggal) FROM dw.dim_tanggal)), interval '1 day') AS g(d)) k
ON CONFLICT (tanggal_key) DO NOTHING
"""

SQL_DIPERBARUI = """
SELECT count(*) FROM stg.unggahan u
JOIN dw.dim_pasar p ON p.nama_pasar = u.pasar
JOIN dw.dim_komoditas k ON k.komoditas = u.komoditas
JOIN dw.fact_harga_harian f ON f.tanggal_key = to_char(u.tanggal, 'YYYYMMDD')::int
                           AND f.pasar_key = p.pasar_key AND f.komoditas_key = k.komoditas_key
"""

SQL_UPSERT = """
INSERT INTO dw.fact_harga_harian (tanggal_key, pasar_key, komoditas_key, harga)
SELECT to_char(u.tanggal, 'YYYYMMDD')::int, p.pasar_key, k.komoditas_key, u.harga
FROM stg.unggahan u
JOIN dw.dim_pasar p ON p.nama_pasar = u.pasar
JOIN dw.dim_komoditas k ON k.komoditas = u.komoditas
ON CONFLICT (tanggal_key, pasar_key, komoditas_key) DO UPDATE SET harga = EXCLUDED.harga
"""

SQL_TANDAI_ADA = """
UPDATE dw.dim_tanggal SET ada_data = TRUE, alasan_tanpa_data = NULL
WHERE tanggal IN (SELECT DISTINCT tanggal FROM stg.unggahan)
"""

SQL_LOG_BUAT = """
CREATE TABLE IF NOT EXISTS dw.log_perubahan (
    id serial PRIMARY KEY, waktu timestamptz NOT NULL DEFAULT now(), sumber text,
    baris_baru int, baris_diperbarui int, keterangan text)
"""

SQL_LOG_ISI = """
INSERT INTO dw.log_perubahan (sumber, baris_baru, baris_diperbarui, keterangan)
VALUES (:sumber, :baru, :diperbarui, :ket)
"""


def simpan(session, bersih: pd.DataFrame, sumber: str) -> dict:
    """Simpan baris valid ke dw.fact_harga_harian (insert atau perbarui bila kuncinya sudah ada).

    `session` = SQLAlchemy Session (mis. `with conn.session as s:`). Semua langkah dalam satu transaksi;
    bila gagal, tidak ada yang tersimpan.
    """
    from sqlalchemy import text

    if bersih.empty:
        return {"baru": 0, "diperbarui": 0}
    data = bersih[["tanggal", "pasar", "komoditas", "harga"]].copy()
    awal, akhir = min(data["tanggal"]), max(data["tanggal"])
    try:
        session.execute(text(SQL_KALENDER), {"awal": awal, "akhir": akhir})       # kalender harus tanpa bolong
        data.to_sql("unggahan", session.connection(), schema="stg", if_exists="replace",
                    index=False, method="multi", chunksize=1000)
        diperbarui = int(session.execute(text(SQL_DIPERBARUI)).scalar())
        session.execute(text(SQL_UPSERT))
        session.execute(text(SQL_TANDAI_ADA))
        session.execute(text("DROP TABLE stg.unggahan"))
        baru = len(data) - diperbarui
        session.execute(text(SQL_LOG_BUAT))
        session.execute(text(SQL_LOG_ISI), {"sumber": sumber, "baru": baru, "diperbarui": diperbarui,
                                            "ket": f"{len(data)} baris, {awal} s.d. {akhir}"})
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"baru": baru, "diperbarui": diperbarui}


SQL_HAPUS = """
DELETE FROM dw.fact_harga_harian f
USING dw.dim_pasar p, dw.dim_komoditas k
WHERE p.nama_pasar = :pasar AND k.komoditas = :komoditas
  AND f.pasar_key = p.pasar_key AND f.komoditas_key = k.komoditas_key
  AND f.tanggal_key = to_char(CAST(:tanggal AS date), 'YYYYMMDD')::int
"""

SQL_TANDAI_KOSONG = """
UPDATE dw.dim_tanggal d SET ada_data = FALSE, alasan_tanpa_data = 'data dihapus admin'
WHERE d.tanggal BETWEEN CAST(:awal AS date) AND CAST(:akhir AS date) AND d.ada_data
  AND NOT EXISTS (SELECT 1 FROM dw.fact_harga_harian f WHERE f.tanggal_key = d.tanggal_key)
"""


def hapus(session, target: pd.DataFrame, sumber: str = "hapus manual") -> dict:
    """Hapus harga (tanggal, pasar, komoditas) dari dw.fact_harga_harian.

    Tanggal yang jadi tidak punya harga sama sekali ditandai ada_data = FALSE. Satu transaksi; gagal = tidak ada yang terhapus.
    """
    from sqlalchemy import text

    if target.empty:
        return {"dihapus": 0}
    data = target[["tanggal", "pasar", "komoditas"]].drop_duplicates()
    awal, akhir = min(data["tanggal"]), max(data["tanggal"])
    try:
        n = 0
        for r in data.itertuples(index=False):
            n += int(session.execute(text(SQL_HAPUS), {"tanggal": r.tanggal, "pasar": r.pasar, "komoditas": r.komoditas}).rowcount or 0)
        session.execute(text(SQL_TANDAI_KOSONG), {"awal": awal, "akhir": akhir})
        session.execute(text(SQL_LOG_BUAT))
        session.execute(text(SQL_LOG_ISI), {"sumber": sumber, "baru": 0, "diperbarui": 0,
                                            "ket": f"{n} baris dihapus, {awal} s.d. {akhir}"})
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"dihapus": n}
