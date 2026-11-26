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

import kelola_data as admin
import metrik
import tema

FOLDER = Path(__file__).parent
LOGO = next((f for f in (FOLDER / "assets").glob("logo.*") if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".webp"}), None) \
    if (FOLDER / "assets").is_dir() else None

st.set_page_config(page_title="SIMONIKA", page_icon=str(LOGO) if LOGO and LOGO.suffix.lower() != ".svg" else "📈", layout="wide", initial_sidebar_state="expanded")
conn = st.connection("simonika", type="sql")          # dibaca dari .streamlit/secrets.toml

P = tema.palet()
st.markdown(f"<style>{tema.css()}</style>", unsafe_allow_html=True)

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
    tema.atur_grafik(fig, None, tinggi, legenda)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def pilih(label: str, opsi: list, key: str, awal: str) -> str:
    """Filter pilihan tunggal berbentuk segmented control (radio bila Streamlit-nya lama)."""
    if hasattr(st, "segmented_control"):
        v = st.segmented_control(label, opsi, default=awal, key=key)
        return v if v in opsi else awal
    return st.radio(label, opsi, index=opsi.index(awal), horizontal=True, key=key)


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
                                                     spark.get(r["komoditas"], []), murah.get(r["komoditas"]), r["penanda"]),
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


def agregat(df: pd.DataFrame, agr: str) -> pd.DataFrame:
    """Harga nasional per hari / minggu (Senin–Minggu) / bulan sampai tanggal acuan.
    Kolom: mulai, akhir, harga (rata-rata pada periode itu), n (jumlah hari ada data), perubahan (% dari periode sebelumnya)."""
    d = df[df["tanggal"] <= T]
    if agr == "Harian":
        g = pd.DataFrame({"mulai": d["tanggal"].values, "akhir": d["tanggal"].values, "terakhir": d["tanggal"].values,
                          "harga": d["harga_rata"].values, "n": 1})
    else:
        p = d["tanggal"].dt.to_period("W-SUN" if agr == "Mingguan" else "M")
        r = d.groupby(p).agg(rata=("harga_rata", "mean"), n=("harga_rata", "count"), terakhir=("tanggal", "max"))
        g = pd.DataFrame({"mulai": r.index.start_time.normalize(), "akhir": r.index.end_time.normalize(),
                          "terakhir": r["terakhir"].values, "harga": r["rata"].values, "n": r["n"].values})
    g = g.sort_values("mulai").reset_index(drop=True)
    g["perubahan"] = g["harga"].pct_change(fill_method=None) * 100
    return g


def label_periode(mulai, akhir, agr: str) -> str:
    if agr == "Harian":
        return tema.tgl(mulai)
    if agr == "Bulanan":
        return f"{BULAN[mulai.month - 1]} {mulai.year}"
    akhir = min(akhir, T)
    return tema.tgl(mulai) if akhir <= mulai else f"{tema.tgl(mulai)} – {tema.tgl(akhir)}"


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

    with kartu("filter"):
        c1, c2, c3 = st.columns([2, 3, 4])
        kom = c1.selectbox("Komoditas", sorted(nasional["komoditas"].unique()), key="mon_kom")
        with c2:
            agr = pilih("Tampilkan harga per", AGREGASI, "mon_agr", "Bulanan")
        with c3:
            per = pilih("Rentang waktu", list(PERIODE_MON[agr]), f"mon_per_{agr}", PERIODE_AWAL[agr])
        o1, o2, _ = st.columns([2, 2, 3])
        ma = o1.checkbox("Garis rata-rata 7 hari", key="mon_ma", disabled=(agr != "Harian"),
                         help="Opsional, hanya untuk tampilan harian: garis yang menghaluskan naik-turun harga sehari-hari.")
        lalu = o2.checkbox("Bandingkan dengan tahun lalu", key="mon_lalu",
                           help="Opsional: garis putus-putus berisi harga pada periode yang sama tahun lalu.")

    s = metrik.seri(nasional, kom)
    semua = nasional[nasional["komoditas"] == kom].sort_values("tanggal")
    satuan = semua["satuan"].iloc[0]
    g_all = agregat(semua, agr)
    awal = awal_jendela(agr, PERIODE_MON[agr][per])
    cur = g_all[g_all["akhir"] >= awal].copy()
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
            line=dict(width=2.4, color=P["sorot"]), marker=dict(size=6, color=P["sorot"]), customdata=nama_periode,
            hovertemplate="%{customdata}<br><b>Rp %{y:,.0f}</b><extra></extra>"))
        if ma and agr == "Harian":
            rm = semua.set_index("tanggal")["harga_rata"].rolling("7D", min_periods=3).mean().rename("v").reset_index()
            rm = rm[(rm["tanggal"] >= awal) & (rm["tanggal"] <= T)]
            fig.add_trace(go.Scatter(x=rm["tanggal"], y=rm["v"], name="Rata-rata 7 hari", mode="lines",
                                     line=dict(width=2.4, color=tema.PAL["c3"], dash="dot"),
                                     hovertemplate="Rata-rata 7 hari<br><b>Rp %{y:,.0f}</b><extra></extra>"))
        if lalu:
            pr = g_all.assign(x=g_all["mulai"] + pd.DateOffset(years=1))
            pr = pr[(pr["x"] >= cur["mulai"].min()) & (pr["x"] <= cur["mulai"].max())]
            if pr.empty:
                st.caption("Belum ada data tahun lalu untuk rentang waktu ini.")
            else:
                fig.add_trace(go.Scatter(
                    x=pr["x"], y=pr["harga"], name="Tahun lalu", mode="lines+markers" if len(pr) <= 60 else "lines",
                    line=dict(width=2.4, color=tema.PAL["c2"], dash="dash"), marker=dict(size=5, color=tema.PAL["c2"]),
                    customdata=["Tahun lalu · " + label_periode(a, b, agr) for a, b in zip(pr["mulai"], pr["akhir"])],
                    hovertemplate="%{customdata}<br><b>Rp %{y:,.0f}</b><extra></extra>"))
        fig.update_layout(hovermode="x")
        fig.update_yaxes(tickformat=",.0f", title_text=f"Harga (Rp per {satuan})")
        tv, tt = tick_tanggal(cur["mulai"].min(), cur["mulai"].max())
        fig.update_xaxes(tickmode="array", tickvals=tv, ticktext=tt)
        tampil(fig, 420, legenda=bool(lalu or (ma and agr == "Harian")))
        if agr != "Harian":
            unit = SATUAN_WAKTU[agr]
            st.caption(f"Setiap titik adalah harga rata-rata selama satu {unit}, dari semua hari yang ada datanya.")
            b_akhir = cur.iloc[-1]
            if b_akhir["akhir"] > T:      # periode terakhir terpotong oleh akhir data, bukan "sedang berjalan"
                st.caption(f"Data tersedia sampai {tema.tgl(T)}, jadi {unit} terakhir "
                           f"({label_periode(b_akhir['mulai'], b_akhir['akhir'], agr)}) baru berisi {int(b_akhir['n'])} hari data.")

    # --- tabel data historis (KPI komoditas) ---
    with kartu("tabel"):
        unit = SATUAN_WAKTU[agr]
        st.markdown(tema.judul_kartu("Tabel data historis", f"KPI {kom} per {unit} · data terbaru di atas", "data"),
                    unsafe_allow_html=True)
        t = cur.sort_values("mulai", ascending=False).reset_index(drop=True)
        kpi = metrik.kpi_deret(s, t["terakhir"])                 # dihitung pada hari terakhir yang ada datanya di tiap periode
        vol_s = dinamika[dinamika["komoditas"] == kom].drop_duplicates("tanggal").set_index("tanggal")["volatilitas_30h_pct"].dropna().sort_index()
        t["vol"] = [vol_s.asof(x) if len(vol_s) else float("nan") for x in t["terakhir"]]
        kol_harga = f"Harga (per {satuan})"
        tabel = pd.DataFrame({"Periode": [label_periode(a_, b_, agr) for a_, b_ in zip(t["mulai"], t["akhir"])],
                              kol_harga: t["harga"].values, "Minggu ini vs lalu": kpi["mingguan_pct"].values,
                              "MoM": kpi["mom_pct"].values, "YoY": kpi["yoy_pct"].values, "YtD": kpi["ytd_pct"].values,
                              "Volatilitas 30 hari": t["vol"].values})
        fmt = {kol_harga: tema.rp, "Minggu ini vs lalu": tema.pct, "MoM": tema.pct, "YoY": tema.pct, "YtD": tema.pct,
               "Volatilitas 30 hari": lambda v: tema.angka(v, 1) + "%" if pd.notna(v) else "–"}
        MAKS_BARIS = 500
        st.markdown(tema.tabel_html(tabel.head(MAKS_BARIS), fmt, 420), unsafe_allow_html=True)
        st.caption("Harga = rata-rata selama periode. Kolom perubahan dan volatilitas dihitung pada hari terakhir yang ada datanya di periode itu: "
                   "minggu ini vs lalu = rata-rata 7 hari dibanding 7 hari sebelumnya; MoM, YoY, YtD = dibanding tanggal yang sama bulan lalu, "
                   "tahun lalu, dan harga penutupan 31 Desember tahun lalu.")
        if len(tabel) > MAKS_BARIS:
            st.caption(f"Menampilkan {MAKS_BARIS} data terbaru dari {tema.angka(len(tabel))}. Unduh CSV untuk data lengkap.")
        csv = pd.DataFrame({"periode_mulai": t["mulai"].dt.strftime("%Y-%m-%d"),
                            "periode_akhir": t["akhir"].clip(upper=T).dt.strftime("%Y-%m-%d"),
                            "tanggal_data_terakhir": t["terakhir"].dt.strftime("%Y-%m-%d"),
                            "harga": t["harga"].round(2).values, "minggu_ini_vs_lalu_pct": kpi["mingguan_pct"].round(2).values,
                            "mom_pct": kpi["mom_pct"].round(2).values, "yoy_pct": kpi["yoy_pct"].round(2).values,
                            "ytd_pct": kpi["ytd_pct"].round(2).values, "volatilitas_30h_pct": t["vol"].round(2).values}
                           ).to_csv(index=False).encode("utf-8-sig")
        nama_berkas = "".join(c if c.isalnum() else "_" for c in kom)
        st.download_button("Unduh tabel (CSV)", csv, f"kpi_historis_{nama_berkas}_{agr.lower()}.csv", "text/csv", key="unduh_riwayat")

    # --- seberapa stabil harganya ---
    with kartu("volatilitas"):
        st.markdown(tema.judul_kartu("Volatilitas 30 hari", f"Simpangan baku perubahan harian (%) · {kom}"), unsafe_allow_html=True)
        v = dinamika[(dinamika["komoditas"] == kom) & (dinamika["tanggal"] >= awal) & (dinamika["tanggal"] <= T)]
        v = v.dropna(subset=["volatilitas_30h_pct"])
        if v.empty:
            st.caption("Volatilitas belum tersedia pada rentang waktu ini.")
        else:
            fig = go.Figure(go.Scatter(x=v["tanggal"], y=v["volatilitas_30h_pct"], mode="lines",
                                       line=dict(width=2, color=P["aksen"]), fill="tozeroy", fillcolor="rgba(128,170,211,0.25)",
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
    with kartu("filter"):
        c1, c2 = st.columns([2, 4])
        kom = c1.selectbox("Komoditas", sorted(hp["komoditas"].unique()), key="pasar_kom")
        with c2:
            per = pilih("Rentang waktu", list(PERIODE), "pasar_per", "6 Bulan")

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

    with kartu("bar_pasar"):
        st.markdown(tema.judul_kartu(f"Harga {kom} di {len(rk)} pasar",
                                     f"Rata-rata harga {per.lower()} terakhir · Rp per {satuan} · batang tergelap = pasar termurah", "pasar"),
                    unsafe_allow_html=True)
        ada = rk.set_index("pasar").reindex([p for p in tema.PASAR_URUT if p in set(rk["pasar"])])      # urutan pasar tetap
        warna = [tema.PAL["c5"] if p == murah["pasar"] else tema.PAL["c2"] for p in ada.index]
        teks = [tema.rp(v) + ("  · termurah" if p == murah["pasar"] else "") for p, v in zip(ada.index, ada["rata"])]
        fig = go.Figure(go.Bar(
            y=list(ada.index), x=ada["rata"], orientation="h", marker_color=warna, text=teks, textposition="outside",
            cliponaxis=False, textfont=dict(color=P["sedang"], size=12),
            customdata=[tema.pct(v) for v in ada["selisih"]],
            hovertemplate="%{y}<br>Rata-rata Rp %{x:,.0f}<br>%{customdata} dari rata-rata 7 pasar<extra></extra>"))
        fig.update_xaxes(tickformat=",.0f", range=[0, ada["rata"].max() * 1.28], title_text=f"Rata-rata harga (Rp per {satuan})")
        fig.update_yaxes(type="category", autorange="reversed", gridcolor="rgba(0,0,0,0)")
        tampil(fig, 70 + 52 * len(ada))

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


def simpan_ke_db(bersih: pd.DataFrame, sumber: str, tunda_pesan: bool = False) -> bool:
    try:
        with conn.session as sesi:
            hasil = admin.simpan(sesi, bersih, sumber)
    except Exception as e:
        st.error(f"Gagal menyimpan, tidak ada data yang berubah: {e}")
        return False
    st.cache_data.clear()                                      # muat ulang data di semua halaman
    pesan = f"Tersimpan: {hasil['baru']} baris baru, {hasil['diperbarui']} baris diperbarui."
    if tunda_pesan:                     # layar akan dimuat ulang; pesan ditampilkan setelahnya
        st.session_state["_pesan_manual"] = st.session_state.get("_pesan_manual", []) + [pesan]
    else:
        st.success(pesan)
    return True


def hapus_dari_db(target: pd.DataFrame) -> bool:
    try:
        with conn.session as sesi:
            hasil = admin.hapus(sesi, target)
    except Exception as e:
        st.error(f"Gagal menghapus, tidak ada data yang berubah: {e}")
        return False
    st.cache_data.clear()
    st.session_state["_pesan_manual"] = st.session_state.get("_pesan_manual", []) + [f"Terhapus: {hasil['dihapus']} harga."]
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

    # ----- input manual: form input + hasil input (sesi ini) yang bisa diedit -----
    with tab_m:
        for pesan in st.session_state.pop("_pesan_manual", []):
            st.success(pesan)
        with kartu("manual"):
            st.markdown(tema.judul_kartu("Input harga manual",
                        "Satu komoditas untuk satu hari. Isi 0 untuk pasar yang tidak mencatat harga."),
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            tgl = c1.date_input("Tanggal", tmax.date(), key="manual_tgl")
            kom = c2.selectbox("Komoditas", sorted(satuan_kom), key="manual_kom")
            ada = muat("SELECT pasar FROM dw.v_harga_lengkap WHERE tanggal = :t AND komoditas = :k",
                       ttl=0, params={"t": tgl, "k": kom})
            if len(ada):
                st.warning(f"Tanggal ini sudah punya {len(ada)} harga untuk {kom}. Menyimpan akan menimpa harga pasar yang sama.")
            ver = st.session_state.get("manual_ver", 0)
            with st.form(f"form_manual_{tgl}_{kom}_{ver}"):
                cols = st.columns(4)
                nilai = {p: cols[i % 4].number_input(f"{p} (Rp/{satuan_kom[kom]})", min_value=0.0, step=100.0, value=0.0,
                                                     key=f"in_{tgl}_{kom}_{p}_{ver}")
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
                    elif simpan_ke_db(baris, "input manual", tunda_pesan=True):
                        hasil = st.session_state.setdefault("hasil_input", [])
                        if (tgl, kom) not in hasil:
                            hasil.append((tgl, kom))
                        st.session_state["manual_ver"] = ver + 1       # kosongkan form untuk input berikutnya
                        st.rerun()

        # ----- hasil input sesi ini: bisa diperbarui atau dihapus -----
        hasil = st.session_state.get("hasil_input", [])
        if hasil:
            with kartu("hasil_input"):
                st.markdown(tema.judul_kartu("Hasil input",
                            "Yang kamu input di sesi ini. Ubah angka untuk memperbarui; kosongkan sel (atau isi 0) untuk menghapus."),
                            unsafe_allow_html=True)
                rows = []
                for (d_, k_) in hasil:
                    sub_ = muat("SELECT pasar, harga FROM dw.v_harga_lengkap WHERE tanggal = :t AND komoditas = :k",
                                ttl=0, params={"t": d_, "k": k_})
                    harga_ = dict(zip(sub_["pasar"], sub_["harga"]))
                    rows.append({"Tanggal": d_.strftime("%d-%m-%Y"), "Komoditas": k_, **{p: harga_.get(p, float("nan")) for p in dim_pasar}})
                lama = pd.DataFrame(rows)
                lama[dim_pasar] = lama[dim_pasar].astype(float)
                diedit = st.data_editor(
                    lama, hide_index=True, use_container_width=True, num_rows="fixed", disabled=["Tanggal", "Komoditas"],
                    key=f"editor_hasil_{len(hasil)}_{st.session_state.get('manual_ver', 0)}",
                    column_config={p: st.column_config.NumberColumn(p, min_value=0, step=100, format="%.0f") for p in dim_pasar})
                nb = diedit[dim_pasar].reset_index(drop=True).astype(float)
                nl = lama[dim_pasar].reset_index(drop=True)
                ada_baru = nb.notna() & (nb > 0)
                sama = (nb - nl).abs() < 0.005
                ubah, hapus_ = [], []
                for i, (d_, k_) in enumerate(hasil):
                    for p in dim_pasar:
                        if ada_baru.at[i, p] and not bool(sama.at[i, p]):
                            ubah.append({"tanggal": d_, "pasar": p, "komoditas": k_, "harga": round(float(nb.at[i, p]), 2)})
                        elif (not ada_baru.at[i, p]) and pd.notna(nl.at[i, p]):
                            hapus_.append({"tanggal": d_, "pasar": p, "komoditas": k_})
                ubah = pd.DataFrame(ubah, columns=["tanggal", "pasar", "komoditas", "harga"])
                hapus_ = pd.DataFrame(hapus_, columns=["tanggal", "pasar", "komoditas"])
                st.markdown(f"**Perubahan belum disimpan:** {len(ubah)} diperbarui, {len(hapus_)} dihapus.")
                tetap2 = yakin = True
                if len(ubah):
                    tetap2 = st.checkbox("Tetap simpan walau ada harga yang ditandai curiga", key="hasil_tetap")
                if len(hapus_):
                    yakin = st.checkbox(f"Saya yakin menghapus {len(hapus_)} harga dari database (tidak bisa dibatalkan)", key="hasil_yakin")
                b1, b2, _ = st.columns([2, 2, 4])
                if b1.button("Simpan perubahan", key="hasil_simpan", disabled=bool(ubah.empty and hapus_.empty)):
                    if not yakin:
                        st.error("Centang konfirmasi penghapusan dulu.")
                    else:
                        siap = True
                        if len(ubah):
                            ubah.insert(0, "baris", range(1, len(ubah) + 1))
                            curiga = admin.tandai_curiga(ubah, median_acuan)
                            if len(curiga) and not tetap2:
                                siap = False
                                st.error("Ada harga yang jauh dari harga biasa. Periksa lagi, atau centang 'Tetap simpan'.")
                                st.markdown(tema.tabel_html(curiga[["tanggal", "pasar", "komoditas", "harga", "median_acuan", "rasio"]],
                                                            {"harga": tema.rp, "median_acuan": tema.rp}, 200), unsafe_allow_html=True)
                        if siap:
                            ok = simpan_ke_db(ubah, "input manual (edit)", tunda_pesan=True) if len(ubah) else True
                            if ok and len(hapus_):
                                ok = hapus_dari_db(hapus_)
                            if ok:
                                st.session_state["manual_ver"] = st.session_state.get("manual_ver", 0) + 1
                                st.rerun()
                if b2.button("Tutup daftar ini", key="hasil_tutup"):
                    st.session_state["hasil_input"] = []
                    st.rerun()

    # ----- riwayat -----
    with tab_r:
        kiri, kanan = st.columns(2)
        with kiri:
            with kartu("riwayat"):
                st.markdown(tema.judul_kartu("Riwayat perubahan", "20 perubahan terakhir"), unsafe_allow_html=True)
                try:
                    log = conn.query("SELECT waktu, sumber, baris_baru, baris_diperbarui, keterangan FROM dw.log_perubahan ORDER BY id DESC LIMIT 20", ttl=0)
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
    st.session_state.setdefault("menu", MENU[0])
    for i, nama_menu in enumerate(MENU):
        st.button(nama_menu, key=f"nav_{i}", use_container_width=True,
                  type="primary" if st.session_state["menu"] == nama_menu else "secondary",
                  on_click=st.session_state.__setitem__, args=("menu", nama_menu))
    menu = st.session_state["menu"]
    st.markdown(tema.side_info(tmin, tmax, n_kom, n_pasar), unsafe_allow_html=True)

if menu == MENU[0]:
    halaman_dashboard()
elif menu == MENU[1]:
    halaman_monitoring()
elif menu == MENU[2]:
    halaman_pasar()
else:
    halaman_admin()
