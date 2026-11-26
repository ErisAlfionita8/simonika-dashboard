"""Perhitungan metrik SIMONIKA (murni pandas, tidak bergantung pada Streamlit agar mudah diuji).

Aturan yang disepakati:
  - Perubahan mingguan = rata-rata harga 7 hari terakhir dibanding rata-rata 7 hari sebelumnya (tanpa kategori naik/turun/stabil).
  - MoM  = harga pada tanggal acuan dibanding harga tanggal yang sama bulan lalu.
  - YoY  = dibanding tanggal yang sama tahun lalu.
  - YtD  = dibanding harga penutupan tahun lalu (31 Desember).
  - Bila tanggal pembanding tidak punya harga, dipakai harga terakhir dalam TOLERANSI_HARI hari sebelumnya; bila tetap
    kosong hasilnya kosong (tidak dihitung).
"""
import numpy as np
import pandas as pd

import tema

TOLERANSI_HARI = 3          # sama dengan ffill limit 3 pada KPI di database
MIN_HARI_MA7 = 4            # rata-rata 7 hari dihitung bila minimal 4 dari 7 hari ada harga
JENDELA_EKSTREM = 90        # hari, untuk penanda tertinggi/terendah
AMBANG_RATA_TAHUN = 0.20    # 20% di atas/bawah rata-rata 1 tahun


def seri(nasional: pd.DataFrame, komoditas: str) -> pd.Series:
    """Harga nasional harian (rata-rata pasar yang mencatat) satu komoditas, indeks tanggal, tanpa NaN."""
    s = nasional.loc[nasional["komoditas"] == komoditas, ["tanggal", "harga_rata"]].dropna()
    s = s.drop_duplicates("tanggal").set_index("tanggal")["harga_rata"].sort_index()
    return s


def ma7(s: pd.Series, t: pd.Timestamp) -> float:
    """Rata-rata harga tercatat dalam 7 hari kalender yang berakhir di t."""
    w = s[(s.index > t - pd.Timedelta(days=7)) & (s.index <= t)]
    return float(w.mean()) if len(w) >= MIN_HARI_MA7 else float("nan")


def perubahan_mingguan(s: pd.Series, t: pd.Timestamp) -> float:
    """Persen: rata-rata 7 hari terakhir vs rata-rata 7 hari sebelumnya."""
    a, b = ma7(s, t), ma7(s, t - pd.Timedelta(days=7))
    return (a / b - 1) * 100 if pd.notna(a) and pd.notna(b) and b != 0 else float("nan")


def harga_pada(s: pd.Series, target: pd.Timestamp):
    """Harga terakhir pada atau sebelum target, paling jauh TOLERANSI_HARI hari. Mengembalikan (tanggal, harga)."""
    w = s[(s.index <= target) & (s.index >= target - pd.Timedelta(days=TOLERANSI_HARI))]
    if w.empty:
        return pd.NaT, float("nan")
    return w.index[-1], float(w.iloc[-1])


def tanggal_pembanding(t: pd.Timestamp, jenis: str) -> pd.Timestamp:
    if jenis == "mom":
        return t - pd.DateOffset(months=1)               # 31 Mar -> 28/29 Feb (akhir bulan itu)
    if jenis == "yoy":
        return t - pd.DateOffset(years=1)
    if jenis == "ytd":
        return pd.Timestamp(year=t.year - 1, month=12, day=31)
    raise ValueError(jenis)


def pembanding(s: pd.Series, t: pd.Timestamp, jenis: str) -> dict:
    now_tgl, now = harga_pada(s, t)
    ref_tgl, ref = harga_pada(s, tanggal_pembanding(t, jenis))
    p = (now / ref - 1) * 100 if pd.notna(now) and pd.notna(ref) and ref != 0 else float("nan")
    return dict(now_tgl=now_tgl, now=now, ref_tgl=ref_tgl, ref=ref, pct=p)


def kpi_deret(s: pd.Series, tanggal) -> pd.DataFrame:
    """Perubahan mingguan, MoM, YoY, YtD pada banyak tanggal sekaligus (aturan sama dengan fungsi per tanggal di atas)."""
    t = pd.DatetimeIndex(tanggal)
    raw = s.reindex(pd.date_range(s.index.min(), s.index.max()))
    cal = raw.ffill(limit=TOLERANSI_HARI)                       # harga terakhir dalam 3 hari
    r7 = raw.rolling(7, min_periods=MIN_HARI_MA7).mean()

    def ambil(seri, tgl):
        return seri.reindex(pd.DatetimeIndex(tgl)).to_numpy(dtype=float)

    def persen(now, ref):
        ref = np.where(ref == 0, np.nan, ref)
        return (now / ref - 1) * 100

    now = ambil(cal, t)
    awal_tahun = pd.to_datetime(pd.DataFrame({"year": t.year - 1, "month": 12, "day": 31}))
    return pd.DataFrame({
        "mingguan_pct": persen(ambil(r7, t), ambil(r7, t - pd.Timedelta(days=7))),
        "mom_pct": persen(now, ambil(cal, t - pd.DateOffset(months=1))),
        "yoy_pct": persen(now, ambil(cal, t - pd.DateOffset(years=1))),
        "ytd_pct": persen(now, ambil(cal, pd.DatetimeIndex(awal_tahun))),
    }, index=t)


def penanda(s: pd.Series, t: pd.Timestamp):
    """Satu penanda ringkas untuk kartu komoditas: (teks, 'naik'|'turun') atau None."""
    _, now = harga_pada(s, t)
    if pd.isna(now):
        return None
    w90 = s[(s.index > t - pd.Timedelta(days=JENDELA_EKSTREM)) & (s.index <= t)]
    if len(w90) >= 30:
        if now >= w90.max():
            return f"Tertinggi {JENDELA_EKSTREM} hari", "naik"
        if now <= w90.min():
            return f"Terendah {JENDELA_EKSTREM} hari", "turun"
    w365 = s[(s.index > t - pd.Timedelta(days=365)) & (s.index <= t)]
    if len(w365) >= 200:
        r = now / w365.mean() - 1
        if r >= AMBANG_RATA_TAHUN:
            return f"{r * 100:.0f}% di atas rata-rata 1 tahun", "naik"
        if r <= -AMBANG_RATA_TAHUN:
            return f"{abs(r) * 100:.0f}% di bawah rata-rata 1 tahun", "turun"
    return None


def ringkasan(nasional: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    """Satu baris per komoditas pada tanggal acuan t."""
    meta = nasional.drop_duplicates("komoditas").set_index("komoditas")[["kelompok", "satuan"]]
    baris = []
    for kom, m in meta.iterrows():
        s = seri(nasional, kom)
        mom, yoy, ytd = (pembanding(s, t, j) for j in ("mom", "yoy", "ytd"))
        baris.append(dict(komoditas=kom, kelompok=m["kelompok"], satuan=m["satuan"],
                          tgl_harga=mom["now_tgl"], harga=mom["now"], mingguan_pct=perubahan_mingguan(s, t),
                          mom_pct=mom["pct"], yoy_pct=yoy["pct"], ytd_pct=ytd["pct"], penanda=penanda(s, t)))
    return pd.DataFrame(baris)


def sorotan(ring: pd.DataFrame) -> list[str]:
    """Kalimat fakta otomatis (tanpa klaim sebab), maksimal tiga."""
    out = []
    w = ring.dropna(subset=["mingguan_pct"])
    if not w.empty:
        a = w.loc[w["mingguan_pct"].idxmax()]
        if a["mingguan_pct"] > 0:
            out.append(f"{a['komoditas']} paling naik minggu ini: {tema.pct(a['mingguan_pct'])} "
                       "(rata-rata 7 hari dibanding 7 hari sebelumnya).")
        b = w.loc[w["mingguan_pct"].idxmin()]
        if b["mingguan_pct"] < 0:
            out.append(f"{b['komoditas']} paling turun minggu ini: {tema.pct(b['mingguan_pct'])}.")
    tinggi = [r.komoditas for r in ring.itertuples() if r.penanda and r.penanda[0].startswith("Tertinggi")]
    if tinggi:
        out.append(f"Berada di harga tertinggi {JENDELA_EKSTREM} hari: {', '.join(tinggi)}.")
    else:
        y = ring.dropna(subset=["yoy_pct"])
        if not y.empty:
            r = y.loc[y["yoy_pct"].abs().idxmax()]
            arah = "lebih mahal" if r["yoy_pct"] > 0 else "lebih murah"
            out.append(f"{r['komoditas']} {tema.angka(abs(r['yoy_pct']), 1)}% {arah} dibanding tahun lalu.")
    return out[:3]


def pasar_termurah(hp_hari: pd.DataFrame) -> dict:
    """{komoditas: (pasar, harga)} dari harga per pasar pada satu hari; hanya bila minimal 2 pasar mencatat."""
    hasil = {}
    for kom, g in hp_hari.groupby("komoditas"):
        g = g.dropna(subset=["harga"])
        if g["pasar"].nunique() >= 2:
            r = g.loc[g["harga"].idxmin()]
            hasil[kom] = (r["pasar"], float(r["harga"]))
    return hasil


def paling_sering_termurah(k: pd.DataFrame):
    """Pasar yang paling sering menjadi termurah (hari dengan minimal 2 pasar mencatat). (pasar, persen hari) atau None."""
    jumlah = k.groupby("tanggal")["pasar"].transform("nunique")
    k = k[jumlah >= 2]
    if k.empty:
        return None
    termurah = k["harga"] == k.groupby("tanggal")["harga"].transform("min")
    hari = k["tanggal"].nunique()
    n = k[termurah].groupby("pasar")["tanggal"].nunique()
    return n.idxmax(), float(n.max() / hari * 100)
