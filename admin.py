"""SIMONIKA - Sistem Monitoring dan Informasi Harga Komoditas.

Halaman: Dashboard, Monitoring Harga, Pantau Pasar, Manajemen Data (admin).
Jalankan: streamlit run app.py
"""
import base64
import hmac
from decimal import Decimal
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import admin
import metrik
import tema

FOLDER = Path(__file__).parent
LOGO = next((f for f in (FOLDER / "assets").glob("logo.*") if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".webp"}), None) \
    if (FOLDER / "assets").is_dir() else None

st.set_page_config(page_title="SIMONIKA", page_icon=str(LOGO) if LOGO and LOGO.suffix.lower() != ".svg" else "📈", layout="wide", initial_sidebar_state="expanded")
conn = st.connection("simonika", type="sql")          # dibaca dari .streamlit/secrets.toml

gelap = bool(st.session_state.get("gelap", False))
P = tema.palet(gelap)
st.markdown(f"<style>{tema.css(gelap)}</style>", unsafe_allow_html=True)

MENU = ["Dashboard", "Monitoring Harga", "Pantau Pasar", "Manajemen Data"]
BULAN = tema.BULAN_ID
PERIODE = {"1 Minggu": 7, "1 Bulan": 30, "6 Bulan": 182, "1 Tahun": 365}      # Pantau Pasar


def uri_logo():
    if LOGO is None:
        return None
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp"}
    return f"data:{mime[LOGO.suffix.lower()]};base64," + base64.b64encode(LOGO.read_bytes()).decode()


# ---------- data ----------
def muat(sql: str, ttl=3600, params=None) -> pd.DataFrame:
    """Ambil data dari database; numeric (Decimal) diubah ke float dan tanggal ke datetime."""
    df = conn.query(sql, ttl=ttl, params=params)
    for c in df.columns:
        s = df[c].dropna()
        if len(s) and isinstance(s.iloc[0], Decimal):
            df[c] = df[c].astype(float)
    if "tanggal" in df.columns:
        df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df


dinamika = muat("SELECT * FROM dw.v_dinamika_komoditas")      # volatilitas per tanggal
nasional = muat("SELECT * FROM dw.v_nasional_harian")         # harga nasional harian + min/maks antar-pasar
tmin, tmax = nasional["tanggal"].min(), nasional["tanggal"].max()
n_pasar = int(nasional["n_pasar"].max())
n_kom = int(nasional["komoditas"].nunique())

# tanggal acuan = tanggal terbaru yang seluruh komoditasnya punya harga (dipakai semua halaman)
_per_tgl = nasional.groupby("tanggal")["komoditas"].nunique()
_penuh = _per_tgl[_per_tgl == n_kom]
T = _penuh.index.max() if len(_penuh) else tmax


def jendela(df: pd.DataFrame, hari: int) -> pd.DataFrame:
    """Baris dengan tanggal dalam `hari` hari kalender yang berakhir di tanggal acuan."""
    return df[(df["tanggal"] > T - pd.Timedelta(days=hari)) & (df["tanggal"] <= T)]


def kartu(nama: str):
    return st.container(key=f"kartu_{nama}")


def tampil(fig, tinggi=360, legenda=False):
    tema.atur_grafik(fig, gelap, tinggi, legenda)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def navbar(judul: str, sub: str):
    status = "Admin" if st.session_state.get("admin_ok") else "Pengunjung"
    st.markdown(tema.navbar(judul, sub, T, status), unsafe_allow_html=True)


def buka_monitoring(nama: str):
    """Dipakai tombol di kartu komoditas: pindah ke Monitoring Harga dengan komoditas terpilih."""
    st.session_state["mon_kom"] = nama
    st.session_state["menu"] = MENU[1]


# =====================================================================
# 1. DASHBOARD
# =====================================================================
def halaman_dashboard():
    navbar("Selamat datang di SIMONIKA!",
           f"Pantau pergerakan harga komoditas di Kota Surabaya berdasarkan data {n_pasar} pasar tradisional.")

    ring = metrik.ringkasan(nasional, T)
    vol = dinamika[dinamika["tanggal"] == T].dropna(subset=["volatilitas_30h_pct"]).set_index("komoditas")["volatilitas_30h_pct"]

    # --- 4 kartu ringkasan ---
    naik = int((ring["mingguan_pct"] > 0).sum())
    turun = int((ring["mingguan_pct"] < 0).sum())
    st.markdown('<div class="grid-kpi">'
                + tema.kartu_kpi("Komoditas dipantau", str(len(ring)), f"di {n_pasar} pasar tradisional")
                + tema.kartu_kpi("Harga naik", str(naik), "komoditas, minggu ini vs minggu lalu")
                + tema.kartu_kpi("Harga turun", str(turun), "komoditas, minggu ini vs minggu lalu")
                + tema.kartu_kpi("Volatilitas tertinggi", (vol.idxmax() if len(vol) else "–"),
                                 (f"{tema.angka(vol.max(), 1)}% simpangan baku harian, 30 hari" if len(vol) else ""))
                + "</div>", unsafe_allow_html=True)

    # --- perubahan terbesar + sorotan ---
    kiri, kanan = st.columns([3, 2])
    with kiri:
        with kartu("terbesar"):
            st.markdown(tema.judul_kartu("Komoditas dengan perubahan terbesar",
                                         "Rata-rata harga 7 hari terakhir dibanding 7 hari sebelumnya", "trofi"), unsafe_allow_html=True)
            tab_n, tab_t = st.tabs(["Naik", "Turun"])
            kolom = ["komoditas", "harga", "satuan", "mingguan_pct"]
            with tab_n:
                x = ring[ring["mingguan_pct"] > 0].nlargest(5, "mingguan_pct")[kolom]
                st.markdown(tema.daftar_perubahan(x.itertuples(index=False), "Tidak ada komoditas yang naik."), unsafe_allow_html=True)
            with tab_t:
                x = ring[ring["mingguan_pct"] < 0].nsmallest(5, "mingguan_pct")[kolom]
                st.markdown(tema.daftar_perubahan(x.itertuples(index=False), "Tidak ada komoditas yang turun."), unsafe_allow_html=True)
    with kanan:
        with kartu("sorotan"):
            st.markdown(tema.judul_kartu("Sorotan", "Dihitung otomatis dari data", "lampu"), unsafe_allow_html=True)
            st.markdown(tema.sorotan_html(metrik.sorotan(ring)), unsafe_allow_html=True)

    # --- kartu 10 komoditas ---
    st.markdown(tema.judul_seksi("Seluruh komoditas"), unsafe_allow_html=True)
    rec = jendela(nasional, 60).sort_values("tanggal")
    spark = rec.groupby("komoditas")["harga_rata"].apply(list).to_dict()
    murah = metrik.pasar_termurah(muat("SELECT tanggal, komoditas, pasar, harga FROM dw.v_harga_lengkap WHERE tanggal = :t",
                                       params={"t": T.date()}))
    urut = ring.sort_values(["kelompok", "komoditas"]).reset_index(drop=True)
    per_baris = 5
    for awal in range(0, len(urut), per_baris):
        kolom_st = st.columns(per_baris)
        for kol, (i, r) in zip(kolom_st, urut.iloc[awal:awal + per_baris].iterrows()):
            with kol:
                with kartu(f"kom_{i}"):
                    st.markdown(tema.kartu_komoditas(r["kelompok"], r["komoditas"], r["satuan"], r["harga"], r["mingguan_pct"],
                                                     spark.get(r["komoditas"], []), gelap, murah.get(r["komoditas"]), r["penanda"]),
                                unsafe_allow_html=True)
                    st.button("Lihat detail →", key=f"detail_{i}", on_click=buka_monitoring, args=(r["komoditas"],),
                              use_container_width=True)

    # --- kesegaran data + tabel ---
    nt = nasional[nasional["tanggal"] == T]["n_pasar"]
    st.caption(f"Data per {tema.tgl(T)}. Harga = rata-rata pasar yang mencatat pada hari itu "
               f"({int(nt.min())}–{int(nt.max())} dari {n_pasar} pasar per komoditas). "
               "Persen pada kartu = rata-rata 7 hari terakhir dibanding 7 hari sebelumnya.")
    with st.expander("Tabel ringkasan KPI"):
        t = ring[["kelompok", "komoditas", "satuan", "harga", "mingguan_pct", "mom_pct", "yoy_pct", "ytd_pct"]].copy()
        t["volatilitas"] = t["komoditas"].map(vol)
        t = t.sort_values(["kelompok", "komoditas"]).rename(columns={
            "kelompok": "Kelompok", "komoditas": "Komoditas", "satuan": "Satuan", "harga": "Harga",
            "mingguan_pct": "Minggu ini vs lalu", "mom_pct": "MoM", "yoy_pct": "YoY", "ytd_pct": "YtD",
            "volatilitas": "Volatilitas 30 hari"})
        fmt = {"Harga": tema.rp, "Minggu ini vs lalu": tema.pct, "MoM": tema.pct, "YoY": tema.pct, "YtD": tema.pct,
               "Volatilitas 30 hari": lambda v: tema.angka(v, 1) + "%" if pd.notna(v) else "–"}
        st.markdown(tema.tabel_html(t, fmt), unsafe_allow_html=True)
        st.caption("MoM = dibanding tanggal yang sama bulan lalu; YoY = tanggal yang sama tahun lalu; YtD = dibanding harga "
                   "penutupan 31 Desember tahun lalu. Bila tanggal pembanding kosong, dipakai harga terakhir dalam 3 hari sebelumnya.")


# =====================================================================
# alat bantu grafik waktu (sumbu x berbahasa Indonesia)
# =====================================================================
AGREGASI = ["Harian", "Mingguan", "Bulanan"]
PERIODE_MON = {"Harian": {"1 Minggu": 7, "1 Bulan": 30, "1 Tahun": 365, "Semua": None},
               "Mingguan": {"1 Bulan": 30, "1 Tahun": 365, "Semua": None},
               "Bulanan": {"1 Tahun": 365, "Semua": None}}
PERIODE_AWAL = {"Harian": "1 Bulan", "Mingguan": "1 Tahun", "Bulanan": "1 Tahun"}
SATUAN_WAKTU = {"Harian": "hari", "Mingguan": "minggu", "Bulanan": "bulan"}
MIN_HARI_PARSIAL = {"Mingguan": 4, "Bulanan": 7}      # minggu/bulan berjalan yang datanya lebih sedikit disembunyikan


def agregat(df: pd.DataFrame, agr: str) -> pd.DataFrame:
    """Harga nasional per hari / minggu (Senin–Minggu) / bulan sampai tanggal acuan.
    Kolom: mulai, akhir, harga (rata-rata pada periode itu), n (jumlah hari ada data), perubahan (% dari periode sebelumnya)."""
    d = df[df["tanggal"] <= T]
    if agr == "Harian":
        g = pd.DataFrame({"mulai": d["tanggal"].values, "akhir": d["tanggal"].values,
                          "harga": d["harga_rata"].values, "n": 1})
    else:
        p = d["tanggal"].dt.to_period("W-SUN" if agr == "Mingguan" else "M")
        r = d.groupby(p)["harga_rata"].agg(["mean", "count"])
        g = pd.DataFrame({"mulai": r.index.start_time.normalize(), "akhir": r.index.end_time.normalize(),
                          "harga": r["mean"].values, "n": r["count"].values})
    g = g.sort_values("mulai").reset_index(drop=True)
    g["perubahan"] = g["harga"].pct_change(fill_method=None) * 100
    return g


def label_periode(mulai, akhir, agr: str) -> str:
    if agr == "Harian":
        return tema.tgl(mulai)
    if agr == "Bulanan":
        return f"{BULAN[mulai.month - 1]} {mulai.year}"
    return f"{tema.tgl(mulai)} – {tema.tgl(min(akhir, T))}"


def awal_jendela(agr: str, hari) -> pd.Timestamp:
    if hari is None:
        return tmin
    if agr == "Bulanan":                                   # 1 Tahun = 12 bulan terakhir, tepat
        return (T.to_period("M") - 11).start_time
    return T - pd.Timedelta(days=hari - 1)


def tick_tanggal(awal, akhir):
    """Posisi dan label sumbu x dengan nama bulan Indonesia (Plotly bawaannya berbahasa Inggris)."""
    awal, akhir = pd.Timestamp(awal), pd.Timestamp(akhir)
    span = (akhir - awal).days
    if span <= 70:
        titik = pd.date_range(awal, akhir, freq="D" if span <= 14 else "7D")
        teks = [f"{t.day} {BULAN[t.month - 1]}" for t in titik]
    else:
        titik = pd.date_range(awal.to_period("M").start_time, akhir, freq="MS" if span <= 400 else "QS")
        teks = [f"{BULAN[t.month - 1]} {t.year}" for t in titik]
    return list(titik), teks


# =====================================================================
# 2. MONITORING HARGA
# =====================================================================
def halaman_monitoring():
    navbar("Monitoring Harga", "Pemantauan historis harga setiap komoditas")

    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 2])
    kom = c1.selectbox("Komoditas", sorted(nasional["komoditas"].unique()), key="mon_kom")
    agr = c2.radio("Tampilkan harga per", AGREGASI, index=2, horizontal=True, key="mon_agr")
    opsi = list(PERIODE_MON[agr])
    per = c3.radio("Rentang waktu", opsi, index=opsi.index(PERIODE_AWAL[agr]), horizontal=True, key=f"mon_per_{agr}")
    ma = c4.checkbox("Garis rata-rata 7 hari", key="mon_ma", disabled=(agr != "Harian"),
                     help="Opsional, hanya untuk tampilan harian: garis yang menghaluskan naik-turun harga sehari-hari.")
    lalu = c5.checkbox("Bandingkan dengan tahun lalu", key="mon_lalu",
                       help="Opsional: garis putus-putus berisi harga pada periode yang sama tahun lalu.")

    s = metrik.seri(nasional, kom)
    semua = nasional[nasional["komoditas"] == kom].sort_values("tanggal")
    satuan = semua["satuan"].iloc[0]
    g_all = agregat(semua, agr)
    awal = awal_jendela(agr, PERIODE_MON[agr][per])
    cur = g_all[g_all["akhir"] >= awal].copy()
    tersembunyi = None
    if agr != "Harian" and len(cur) and cur.iloc[-1]["akhir"] > T and cur.iloc[-1]["n"] < MIN_HARI_PARSIAL[agr]:
        tersembunyi, cur = cur.iloc[-1], cur.iloc[:-1]       # periode berjalan yang baru berisi sedikit hari
    if cur.empty:
        st.info("Tidak ada data pada rentang waktu ini.")
        return

    # --- ringkasan dan kartu perbandingan ---
    mom, yoy, ytd = (metrik.pembanding(s, T, j) for j in ("mom", "yoy", "ytd"))
    mg = metrik.perubahan_mingguan(s, T)
    st.markdown('<div class="grid-kpi">'
                + tema.kartu_kpi("Harga terakhir", tema.rp(mom["now"]), f"per {satuan} · {tema.tgl(mom['now_tgl'])}",
                                 f"Minggu ini vs lalu: {tema.pct(mg)}")
                + tema.kartu_banding("MoM", "dibanding bulan lalu", mom)
                + tema.kartu_banding("YoY", "dibanding tahun lalu", yoy)
                + tema.kartu_banding("YtD", "dibanding akhir tahun lalu", ytd)
                + "</div>", unsafe_allow_html=True)

    # --- grafik historis harga ---
    with kartu("tren"):
        st.markdown(tema.judul_kartu("Grafik historis harga",
                                     f"{kom} · harga per {SATUAN_WAKTU[agr]} · Rp per {satuan} · {per.lower()}", "tren"),
                    unsafe_allow_html=True)
        nama_periode = [label_periode(a, b, agr) for a, b in zip(cur["mulai"], cur["akhir"])]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cur["mulai"], y=cur["harga"], name=kom, mode="lines+markers" if len(cur) <= 60 else "lines",
            line=dict(width=2.2, color=P["aksen"]), marker=dict(size=6, color=P["aksen"]), customdata=nama_periode,
            hovertemplate="%{customdata}<br><b>Rp %{y:,.0f}</b><extra></extra>"))
        if ma and agr == "Harian":
            rm = semua.set_index("tanggal")["harga_rata"].rolling("7D", min_periods=3).mean().rename("v").reset_index()
            rm = rm[(rm["tanggal"] >= awal) & (rm["tanggal"] <= T)]
            fig.add_trace(go.Scatter(x=rm["tanggal"], y=rm["v"], name="Rata-rata 7 hari", mode="lines",
                                     line=dict(width=2, color=tema.KATEGORI[gelap][1], dash="dot"),
                                     hovertemplate="Rata-rata 7 hari<br><b>Rp %{y:,.0f}</b><extra></extra>"))
        if lalu:
            pr = g_all.assign(x=g_all["mulai"] + pd.DateOffset(years=1))
            pr = pr[(pr["x"] >= cur["mulai"].min()) & (pr["x"] <= cur["mulai"].max())]
            if pr.empty:
                st.caption("Belum ada data tahun lalu untuk rentang waktu ini.")
            else:
                fig.add_trace(go.Scatter(
                    x=pr["x"], y=pr["harga"], name="Tahun lalu", mode="lines+markers" if len(pr) <= 60 else "lines",
                    line=dict(width=2, color=P["redup"], dash="dash"), marker=dict(size=5, color=P["redup"]),
                    customdata=["Tahun lalu · " + label_periode(a, b, agr) for a, b in zip(pr["mulai"], pr["akhir"])],
                    hovertemplate="%{customdata}<br><b>Rp %{y:,.0f}</b><extra></extra>"))
        fig.update_layout(hovermode="x")
        fig.update_yaxes(tickformat=",.0f", title_text=f"Harga (Rp per {satuan})")
        tv, tt = tick_tanggal(cur["mulai"].min(), cur["mulai"].max())
        fig.update_xaxes(tickmode="array", tickvals=tv, ticktext=tt)
        tampil(fig, 420, legenda=bool(lalu or (ma and agr == "Harian")))
        if agr != "Harian":
            st.caption(f"Setiap titik adalah harga rata-rata selama satu {SATUAN_WAKTU[agr]}, dari semua hari yang ada datanya.")
            akhir_baris = cur.iloc[-1]
            if tersembunyi is not None:
                st.caption(f"{SATUAN_WAKTU[agr].capitalize()} berjalan ({label_periode(tersembunyi['mulai'], tersembunyi['akhir'], agr)}) "
                           f"belum ditampilkan karena baru berisi {int(tersembunyi['n'])} hari data.")
            elif akhir_baris["akhir"] > T:
                st.caption(f"{SATUAN_WAKTU[agr].capitalize()} terakhir ({label_periode(akhir_baris['mulai'], akhir_baris['akhir'], agr)}) "
                           f"baru berisi {int(akhir_baris['n'])} hari data, jadi angkanya belum final.")

    # --- tabel data historis ---
    with kartu("tabel"):
        unit = SATUAN_WAKTU[agr]
        st.markdown(tema.judul_kartu("Tabel data historis", f"{kom} · harga per {unit} · data terbaru di atas", "data"),
                    unsafe_allow_html=True)
        t = cur.sort_values("mulai", ascending=False)
        kol_harga, kol_ubah = f"Harga (per {satuan})", f"Perubahan dari {unit} sebelumnya"
        tabel = pd.DataFrame({"Periode": [label_periode(a, b, agr) for a, b in zip(t["mulai"], t["akhir"])],
                              kol_harga: t["harga"].values, kol_ubah: t["perubahan"].values})
        fmt = {kol_harga: tema.rp,
               kol_ubah: lambda v: "–" if pd.isna(v) else ("▲ " if v > 0 else "▼ " if v < 0 else "● ") + tema.pct(v)}
        if agr != "Harian":
            tabel["Hari ada data"] = t["n"].values
            fmt["Hari ada data"] = tema.angka
        MAKS_BARIS = 500
        st.markdown(tema.tabel_html(tabel.head(MAKS_BARIS), fmt, 420), unsafe_allow_html=True)
        if len(tabel) > MAKS_BARIS:
            st.caption(f"Menampilkan {MAKS_BARIS} data terbaru dari {tema.angka(len(tabel))}. Unduh CSV untuk data lengkap.")
        csv = pd.DataFrame({"periode_mulai": t["mulai"].dt.strftime("%Y-%m-%d"),
                            "periode_akhir": t["akhir"].clip(upper=T).dt.strftime("%Y-%m-%d"),
                            "harga": t["harga"].round(2).values, "perubahan_pct": t["perubahan"].round(2).values,
                            "hari_ada_data": t["n"].values}).to_csv(index=False).encode("utf-8-sig")
        nama_berkas = "".join(c if c.isalnum() else "_" for c in kom)
        st.download_button("Unduh tabel (CSV)", csv, f"riwayat_harga_{nama_berkas}_{agr.lower()}.csv", "text/csv", key="unduh_riwayat")

    # --- seberapa stabil harganya ---
    with kartu("volatilitas"):
        st.markdown(tema.judul_kartu("Volatilitas 30 hari", f"Simpangan baku perubahan harian (%) · {kom}"), unsafe_allow_html=True)
        v = dinamika[(dinamika["komoditas"] == kom) & (dinamika["tanggal"] >= awal) & (dinamika["tanggal"] <= T)]
        v = v.dropna(subset=["volatilitas_30h_pct"])
        if v.empty:
            st.caption("Volatilitas belum tersedia pada rentang waktu ini.")
        else:
            fig = go.Figure(go.Scatter(x=v["tanggal"], y=v["volatilitas_30h_pct"], mode="lines",
                                       line=dict(width=2, color=P["aksen"]), fill="tozeroy", fillcolor="rgba(57,135,229,0.12)",
                                       customdata=[tema.tgl(x) for x in v["tanggal"]],
                                       hovertemplate="%{customdata}<br><b>%{y:.1f}%</b><extra></extra>"))
            fig.update_layout(hovermode="x")
            fig.update_yaxes(ticksuffix="%", rangemode="tozero")
            tv, tt = tick_tanggal(v["tanggal"].min(), v["tanggal"].max())
            fig.update_xaxes(tickmode="array", tickvals=tv, ticktext=tt)
            tampil(fig, 240)


# =====================================================================
# 3. PANTAU PASAR
# =====================================================================
def halaman_pasar():
    navbar("Pantau Pasar", f"Perbandingan harga di {n_pasar} pasar tradisional Surabaya")
    hp = muat("SELECT * FROM dw.v_harga_lengkap")                # tanggal, kelompok, komoditas, satuan, pasar, harga
    c1, c2 = st.columns([2, 3])
    kom = c1.selectbox("Komoditas", sorted(hp["komoditas"].unique()), key="pasar_kom")
    per = c2.radio("Rentang waktu", list(PERIODE), index=2, horizontal=True, key="pasar_per")

    k = jendela(hp[hp["komoditas"] == kom], PERIODE[per]).copy()
    if k.empty:
        st.info("Tidak ada data pada rentang waktu ini.")
        return
    k["selisih"] = (k["harga"] / k.groupby("tanggal")["harga"].transform("mean") - 1) * 100
    satuan = k["satuan"].iloc[0]
    hari_ada = k["tanggal"].nunique()

    rk = (k.groupby("pasar").agg(rata=("harga", "mean"), terendah=("harga", "min"), tertinggi=("harga", "max"),
                                 hari=("tanggal", "nunique"), selisih=("selisih", "mean")).reset_index().sort_values("rata"))
    rk["kelengkapan"] = rk["hari"] / hari_ada * 100
    murah, mahal = rk.iloc[0], rk.iloc[-1]
    sering = metrik.paling_sering_termurah(k)
    beda = (mahal["rata"] / murah["rata"] - 1) * 100

    st.markdown('<div class="grid-kpi">'
                + tema.kartu_kpi("Pasar termurah", murah["pasar"], f"rata-rata {tema.rp(murah['rata'])} ({tema.pct(murah['selisih'])})")
                + tema.kartu_kpi("Pasar termahal", mahal["pasar"], f"rata-rata {tema.rp(mahal['rata'])} ({tema.pct(mahal['selisih'])})")
                + tema.kartu_kpi("Selisih termurah–termahal", tema.angka(beda, 1) + "%", f"rata-rata harga per {satuan}")
                + tema.kartu_kpi("Paling sering termurah", sering[0] if sering else "–",
                                 f"termurah pada {tema.angka(sering[1], 0)}% hari" if sering else "perlu minimal 2 pasar mencatat")
                + "</div>", unsafe_allow_html=True)

    with kartu("tren_pasar"):
        st.markdown(tema.judul_kartu(f"Harga {kom} per pasar", f"Rp per {satuan} · {per.lower()}", "tren"), unsafe_allow_html=True)
        fig = go.Figure()
        for nama in tema.PASAR_URUT:
            g = k[k["pasar"] == nama].sort_values("tanggal")
            if len(g):
                fig.add_trace(go.Scatter(x=g["tanggal"], y=g["harga"], name=nama, mode="lines",
                                         line=dict(width=1.8, color=tema.warna_pasar(nama, gelap)),
                                         hovertemplate="Rp %{y:,.0f}<extra>" + nama + "</extra>"))
        fig.update_layout(hovermode="x unified")
        fig.update_yaxes(tickformat=",.0f", title_text=f"Harga (Rp per {satuan})")
        tv, tt = tick_tanggal(k["tanggal"].min(), k["tanggal"].max())
        fig.update_xaxes(tickmode="array", tickvals=tv, ticktext=tt, hoverformat="%d-%m-%Y")
        tampil(fig, 400, legenda=True)

    kiri, kanan = st.columns(2)
    with kiri:
        with kartu("bar_pasar"):
            st.markdown(tema.judul_kartu("Rata-rata harga per pasar", f"{kom} · {per.lower()} · Rp per {satuan}"), unsafe_allow_html=True)
            ada = rk.set_index("pasar").reindex([p for p in tema.PASAR_URUT if p in set(rk["pasar"])])   # urutan tetap, tidak diurutkan
            fig = go.Figure(go.Bar(
                x=list(ada.index), y=ada["rata"], marker_color=[tema.warna_pasar(p, gelap) for p in ada.index],
                text=[tema.rp(v) for v in ada["rata"]], textposition="outside", cliponaxis=False,
                hovertemplate="%{x}<br>%{text}<extra></extra>", textfont=dict(color=P["sedang"], size=11)))
            fig.update_yaxes(tickformat=",.0f", range=[0, ada["rata"].max() * 1.2])
            fig.update_xaxes(type="category")
            tampil(fig, 380)
    with kanan:
        with kartu("tabel_pasar"):
            st.markdown(tema.judul_kartu(f"Peringkat pasar: {kom}", "Dari termurah ke termahal"), unsafe_allow_html=True)
            t = rk.rename(columns={"pasar": "Pasar", "rata": "Rata-rata harga", "selisih": "Selisih vs rata-rata 7 pasar",
                                   "terendah": "Terendah", "tertinggi": "Tertinggi", "kelengkapan": "Kelengkapan"})[
                ["Pasar", "Rata-rata harga", "Selisih vs rata-rata 7 pasar", "Terendah", "Tertinggi", "Kelengkapan"]]
            fmt = {"Rata-rata harga": tema.rp, "Selisih vs rata-rata 7 pasar": tema.pct, "Terendah": tema.rp, "Tertinggi": tema.rp,
                   "Kelengkapan": lambda v: tema.angka(v, 0) + "%"}
            st.markdown(tema.tabel_html(t, fmt, 380), unsafe_allow_html=True)
            st.caption("Harga tercatat belum tentu untuk kualitas barang yang sama antar-pasar. Selisih dihitung hanya pada hari pasar itu mencatat harga.")


# =====================================================================
# 4. MANAJEMEN DATA (admin)
# =====================================================================
def gerbang_admin() -> bool:
    if st.session_state.get("admin_ok"):
        return True
    try:
        sandi = st.secrets["admin"]["password"]
    except Exception:
        sandi = None
    if not sandi:
        st.error("Kata sandi admin belum diatur. Tambahkan ke `.streamlit/secrets.toml`:")
        st.code('[admin]\npassword = "GANTI_DENGAN_SANDI_KAMU"', language="toml")
        return False
    with kartu("login"):
        st.markdown(tema.judul_kartu("Masuk admin", "Halaman ini khusus pengelola data."), unsafe_allow_html=True)
        with st.form("form_login"):
            isi = st.text_input("Kata sandi", type="password")
            masuk = st.form_submit_button("Masuk")
        if masuk:
            if hmac.compare_digest(isi.encode(), str(sandi).encode()):
                st.session_state["admin_ok"] = True
                st.rerun()
            else:
                st.error("Kata sandi salah.")
    return False


def simpan_ke_db(bersih: pd.DataFrame, sumber: str) -> bool:
    try:
        with conn.session as sesi:
            hasil = admin.simpan(sesi, bersih, sumber)
    except Exception as e:
        st.error(f"Gagal menyimpan, tidak ada data yang berubah: {e}")
        return False
    st.cache_data.clear()                                      # muat ulang data di semua halaman
    st.success(f"Tersimpan: {hasil['baru']} baris baru, {hasil['diperbarui']} baris diperbarui.")
    return True


def halaman_admin():
    navbar("Manajemen Data", "Khusus admin: unggah CSV, input manual, dan riwayat perubahan")
    if not gerbang_admin():
        return
    if st.button("Keluar dari mode admin"):
        st.session_state["admin_ok"] = False
        st.rerun()

    dim_pasar = muat("SELECT nama_pasar FROM dw.dim_pasar ORDER BY 1", ttl=60)["nama_pasar"].tolist()
    dk = muat("SELECT komoditas, satuan FROM dw.dim_komoditas ORDER BY 1", ttl=60)
    satuan_kom = dict(zip(dk["komoditas"], dk["satuan"]))
    median_acuan = (nasional[nasional["tanggal"] > tmax - pd.Timedelta(days=90)]
                    .groupby("komoditas")["harga_rata"].median().to_dict())

    tab_u, tab_m, tab_r = st.tabs(["Unggah CSV", "Input manual", "Riwayat dan hari kosong"])

    # ----- unggah CSV -----
    with tab_u:
        with kartu("unggah"):
            st.markdown(tema.judul_kartu("Unggah berkas CSV",
                        "Kolom wajib: tanggal (YYYY-MM-DD), pasar, komoditas, harga. Kolom kelompok dan satuan boleh ada."),
                        unsafe_allow_html=True)
            st.download_button("Unduh templat CSV", admin.TEMPLAT_CSV, "templat_harga.csv", "text/csv")
            f = st.file_uploader("Pilih berkas CSV", type=["csv"], key="unggah_csv")
            if f is not None:
                try:
                    mentah = pd.read_csv(f, dtype=str, keep_default_na=False, sep=None, engine="python", encoding="utf-8-sig")
                    bersih, ditolak, dilewati = admin.validasi(mentah, dim_pasar, satuan_kom)
                except Exception as e:
                    st.error(f"Berkas tidak dapat diproses: {e}")
                    return
                curiga = admin.tandai_curiga(bersih, median_acuan)
                st.markdown('<div class="grid-kpi">'
                            + tema.kartu_kpi("Baris valid", tema.angka(len(bersih)), "siap disimpan")
                            + tema.kartu_kpi("Ditolak", tema.angka(len(ditolak)), "lihat alasan di bawah")
                            + tema.kartu_kpi("Dilewati", tema.angka(dilewati), "harga kosong atau '-'")
                            + tema.kartu_kpi("Ditandai curiga", tema.angka(len(curiga)), "jauh dari harga biasa")
                            + "</div>", unsafe_allow_html=True)
                if len(ditolak):
                    st.markdown("**Baris ditolak** (tidak akan disimpan)")
                    st.markdown(tema.tabel_html(ditolak.head(200), tinggi_maks=260), unsafe_allow_html=True)
                setuju = True
                if len(curiga):
                    st.warning("Harga berikut jauh di atas atau di bawah harga biasa (≤ 0,2× atau ≥ 5× median 90 hari terakhir). "
                               "Periksa kemungkinan salah ketik, mis. kelebihan satu nol.")
                    st.markdown(tema.tabel_html(curiga.head(200), {"median_acuan": tema.rp, "harga": tema.rp}, 260), unsafe_allow_html=True)
                    setuju = st.checkbox("Saya sudah memeriksa baris yang ditandai dan tetap ingin menyimpannya", key="setuju_unggah")
                if len(bersih):
                    st.markdown("**Pratinjau baris valid**")
                    st.markdown(tema.tabel_html(bersih.head(20), {"harga": tema.rp}, 300), unsafe_allow_html=True)
                if st.button("Simpan ke database", disabled=bool(bersih.empty or not setuju), key="simpan_unggah"):
                    simpan_ke_db(bersih, f.name)

    # ----- input manual -----
    with tab_m:
        with kartu("manual"):
            st.markdown(tema.judul_kartu("Input harga manual",
                        "Satu komoditas untuk satu hari. Isi 0 untuk pasar yang tidak mencatat (nilainya tidak diubah)."),
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            tgl = c1.date_input("Tanggal", tmax.date(), key="manual_tgl")
            kom = c2.selectbox("Komoditas", sorted(satuan_kom), key="manual_kom")
            ada = muat("SELECT pasar, harga FROM dw.v_harga_lengkap WHERE tanggal = :t AND komoditas = :k",
                       ttl=0, params={"t": tgl, "k": kom})
            ada = dict(zip(ada["pasar"], ada["harga"]))
            if ada:
                st.caption(f"Sudah ada {len(ada)} harga pada tanggal ini; nilai di bawah terisi dari database dan akan diperbarui.")
            with st.form(f"form_manual_{tgl}_{kom}"):
                cols = st.columns(4)
                nilai = {p: cols[i % 4].number_input(f"{p} (Rp/{satuan_kom[kom]})", min_value=0.0, step=100.0,
                                                     value=float(ada.get(p, 0.0)), key=f"in_{tgl}_{kom}_{p}")
                         for i, p in enumerate(dim_pasar)}
                tetap = st.checkbox("Tetap simpan walau ada harga yang ditandai curiga")
                kirim = st.form_submit_button("Simpan")
            if kirim:
                baris = pd.DataFrame([{"baris": i, "tanggal": tgl, "pasar": p, "komoditas": kom, "harga": round(v, 2)}
                                      for i, (p, v) in enumerate(nilai.items(), start=1) if v > 0])
                if baris.empty:
                    st.warning("Isi minimal satu harga lebih dari 0.")
                else:
                    curiga = admin.tandai_curiga(baris, median_acuan)
                    if len(curiga) and not tetap:
                        st.error("Ada harga yang jauh dari harga biasa. Periksa lagi, atau centang 'Tetap simpan'.")
                        st.markdown(tema.tabel_html(curiga[["pasar", "komoditas", "harga", "median_acuan", "rasio"]],
                                                    {"harga": tema.rp, "median_acuan": tema.rp}, 200), unsafe_allow_html=True)
                    else:
                        simpan_ke_db(baris, "input manual")

    # ----- riwayat -----
    with tab_r:
        kiri, kanan = st.columns(2)
        with kiri:
            with kartu("riwayat"):
                st.markdown(tema.judul_kartu("Riwayat perubahan", "20 perubahan terakhir"), unsafe_allow_html=True)
                try:
                    log = conn.query("SELECT waktu, sumber, baris_baru, baris_diperbarui FROM dw.log_perubahan ORDER BY id DESC LIMIT 20", ttl=0)
                    fmt = {"waktu": lambda v: pd.Timestamp(v).strftime("%d-%m-%Y %H:%M")}
                    st.markdown(tema.tabel_html(log, fmt, 360) if len(log) else "Belum ada perubahan.", unsafe_allow_html=True)
                except Exception:
                    st.info("Belum ada riwayat perubahan.")
        with kanan:
            with kartu("hari_kosong"):
                st.markdown(tema.judul_kartu("Hari tanpa data", "Tanggal yang belum punya harga (dari terbaru)"), unsafe_allow_html=True)
                kosong = muat("SELECT tanggal, alasan_tanpa_data AS alasan FROM dw.dim_tanggal WHERE NOT ada_data ORDER BY tanggal DESC", ttl=60)
                if kosong.empty:
                    st.markdown("Semua hari memiliki data.")
                else:
                    kosong["tanggal"] = kosong["tanggal"].dt.strftime("%d-%m-%Y")
                    st.markdown(tema.tabel_html(kosong, tinggi_maks=360), unsafe_allow_html=True)



# =====================================================================
# kerangka: sidebar + penampil halaman
# =====================================================================
with st.sidebar:
    st.markdown(tema.brand(uri_logo()), unsafe_allow_html=True)
    menu = st.radio("Menu", MENU, label_visibility="collapsed", key="menu")
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.toggle("Mode gelap", key="gelap")
    st.markdown(f'<div class="side-info">Data {tema.tgl(tmin)} s.d. {tema.tgl(tmax)}<br>'
                f'{n_kom} komoditas · {n_pasar} pasar tradisional Surabaya<br>Sumber: Bagian Perekonomian dan SDA</div>',
                unsafe_allow_html=True)

if menu == MENU[0]:
    halaman_dashboard()
elif menu == MENU[1]:
    halaman_monitoring()
elif menu == MENU[2]:
    halaman_pasar()
else:
    halaman_admin()
