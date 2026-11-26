"""Tema SIMONIKA (terang): palet biru dari acuan desain, CSS gaya SaaS dashboard, dan komponen HTML kecil.

Palet acuan: #c0e6fd #80aad3 #5b86b6 #3f6593 #1b3554 #000f22
  - warna besar/dekoratif (latar, sidebar, header): semua tingkat palet
  - teks dan garis data: hanya #3f6593 ke gelap (kontras >= 5:1 di atas latar terang)
  - #80aad3 dan #5b86b6 dipakai untuk isian, garis sekunder, dan batang non-sorot
  - naik = merah, turun = biru palet (selalu disertai panah dan tanda +/-)
"""
from html import escape
from urllib.parse import quote

import pandas as pd

# ---------- palet ----------
PAL = dict(c1="#c0e6fd", c2="#80aad3", c3="#5b86b6", c4="#3f6593", c5="#1b3554", c6="#000f22")
PASAR_URUT = ["Balongsari", "Genteng Baru", "Kembang", "Pabean", "Pucang Anom", "Tambahrejo", "Wonokromo"]

TEMA = dict(
    bg1="#f6fbff", bg2="#d6ebfb", kartu="rgba(255,255,255,0.74)", kartu_solid="#ffffff",
    garis="rgba(27,53,84,0.14)", teks=PAL["c6"], sedang=PAL["c5"], redup=PAL["c4"],
    input="rgba(255,255,255,0.92)", popup="#ffffff", grid="rgba(27,53,84,0.10)",
    aksen=PAL["c4"], aksen2=PAL["c3"], naik="#cf3f3b", turun=PAL["c4"], sorot=PAL["c5"],
    bayangan="0 8px 26px rgba(27,53,84,0.10)")


def palet(_=None) -> dict:
    return TEMA


# ---------- format angka dan tanggal (gaya Indonesia) ----------
BULAN_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def angka(x, desimal=0) -> str:
    if x is None or pd.isna(x):
        return "–"
    return f"{x:,.{desimal}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rp(x) -> str:
    return "–" if x is None or pd.isna(x) else "Rp " + angka(x, 0)


def pct(x, desimal=1) -> str:
    return "–" if x is None or pd.isna(x) else ("+" if x > 0 else "") + angka(x, desimal) + "%"


def tgl(t) -> str:
    """31 Agu 2026"""
    if t is None or pd.isna(t):
        return "–"
    t = pd.Timestamp(t)
    return f"{t.day} {BULAN_ID[t.month - 1]} {t.year}"


# ---------- ikon (SVG garis) ----------
_IKON = {
    "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
    "tren": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "pasar": '<path d="M4 9l1.5-5h13L20 9"/><path d="M4 9a2.5 2.5 0 0 0 5 0 2.5 2.5 0 0 0 6 0 2.5 2.5 0 0 0 5 0"/>'
             '<path d="M5 12v8h14v-8"/><path d="M10 20v-5h4v5"/>',
    "data": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/>'
            '<path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "kalender": '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    "lampu": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    "trofi": '<path d="M8 4h8v5a4 4 0 0 1-8 0V4z"/><path d="M8 6H4v1a4 4 0 0 0 4 4M16 6h4v1a4 4 0 0 1-4 4"/>'
             '<path d="M12 13v4M8 20h8M10 17h4"/>',
}
_BUKA = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'


def ikon(nama: str, ukuran: int = 20) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{ukuran}" height="{ukuran}" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_IKON[nama]}</svg>')


def _uri_ikon(nama: str) -> str:
    return 'url("data:image/svg+xml,' + quote(_BUKA + _IKON[nama] + "</svg>") + '")'


# ---------- CSS ----------
def css(_=None) -> str:
    p = TEMA
    ikon_menu = "\n".join(
        f'[data-testid="stSidebar"] .st-key-nav_{i} button p::before {{ -webkit-mask-image: {_uri_ikon(n)}; mask-image: {_uri_ikon(n)}; }}'
        for i, n in enumerate(["home", "tren", "pasar", "data"]))
    return f"""
:root {{
  --c1:{PAL['c1']}; --c2:{PAL['c2']}; --c3:{PAL['c3']}; --c4:{PAL['c4']}; --c5:{PAL['c5']}; --c6:{PAL['c6']};
  --bg1:{p['bg1']}; --bg2:{p['bg2']}; --kartu:{p['kartu']}; --garis:{p['garis']};
  --teks:{p['teks']}; --sedang:{p['sedang']}; --redup:{p['redup']}; --input:{p['input']}; --popup:{p['popup']};
  --aksen:{p['aksen']}; --aksen2:{p['aksen2']}; --naik:{p['naik']}; --turun:{p['turun']};
  --bayangan:{p['bayangan']};
}}
.stApp {{ background: linear-gradient(135deg, var(--bg1) 0%, var(--bg2) 100%); color: var(--teks); }}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"], footer {{ visibility: hidden; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1480px; }}
[data-testid="stMarkdownContainer"], h1, h2, h3, h4, label, .stCaption {{ color: var(--teks); }}
[data-testid="stWidgetLabel"] *, .stCaption, [data-testid="stCaptionContainer"] * {{ color: var(--redup) !important; }}

/* ---- sidebar: selalu terbuka, navigasi ringkas ---- */
[data-testid="stSidebar"] {{ background: #0b2139; border-right: 0;
  min-width: 250px !important; max-width: 250px !important; transform: none !important; }}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stSidebarHeader"] {{ display: none !important; }}
[data-testid="stSidebarUserContent"] {{ padding: 1.2rem .8rem 1rem .8rem; }}
[data-testid="stSidebar"] * {{ color: var(--c1); }}
.brand {{ display:flex; align-items:center; gap:.7rem; padding:.1rem .5rem 1rem .5rem; margin-bottom:1rem;
  border-bottom:1px solid rgba(192,230,253,.14); }}
.brand-logo {{ flex:none; width:44px; height:44px; display:grid; place-items:center; }}
.brand-logo img {{ max-width:44px; max-height:44px; object-fit:contain; }}
.brand-logo.cadangan {{ border-radius:12px; background: linear-gradient(135deg, var(--c3), var(--c2)); color:#fff; }}
.brand-teks {{ min-width:0; }}
.brand-nama {{ font-weight:800; letter-spacing:.1em; font-size:1.1rem; color:#ffffff !important; line-height:1.2; }}
.brand-sub {{ font-size:.66rem; color: var(--c2) !important; line-height:1.3; margin-top:.15rem; }}
.menu-judul {{ font-size:.68rem; letter-spacing:.08em; color: var(--c2) !important; padding:0 .6rem .45rem .6rem; font-weight:700; text-transform:uppercase; }}
/* menu = deretan tombol bergaya segmented control (aktif terisi, lainnya pil transparan) */
[data-testid="stSidebar"] [class*="st-key-nav_"] {{ margin-bottom:.4rem; }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button {{ width:100%; justify-content:flex-start; min-height:2.8rem; padding:.55rem .9rem;
  border-radius:12px; box-shadow:none; transition: background .15s, border-color .15s; }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"] {{
  background: rgba(192,230,253,.07); border:1px solid rgba(192,230,253,.20); color: var(--c1); }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-secondary"]:hover {{
  background: rgba(192,230,253,.16); border-color: var(--c2); }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {{
  background: linear-gradient(90deg, var(--c3), var(--c4)); border:1px solid var(--c2); color:#ffffff; }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button * {{ color: inherit !important; }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button [data-testid="stMarkdownContainer"] {{ width:100%; }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button p {{ display:flex; align-items:center; justify-content:flex-start; gap:.7rem; margin:0;
  font-size:.95rem; font-weight:600; text-align:left; }}
[data-testid="stSidebar"] [class*="st-key-nav_"] button p::before {{ content:""; flex:none; width:19px; height:19px; background-color: currentColor;
  -webkit-mask-repeat:no-repeat; mask-repeat:no-repeat; -webkit-mask-position:center; mask-position:center;
  -webkit-mask-size:contain; mask-size:contain; }}
{ikon_menu}
.side-info {{ margin-top:1.4rem; padding:.8rem .6rem 0 .6rem; border-top:1px solid rgba(192,230,253,.14);
  font-size:.7rem; color: var(--c2) !important; line-height:1.5; }}
.side-info b {{ color: var(--c1) !important; font-weight:600; }}

/* ---- header halaman (banner berwarna) ---- */
.hero {{ display:flex; justify-content:space-between; align-items:center; gap:1.2rem; flex-wrap:wrap; padding:1.6rem 1.9rem; margin-bottom:1.2rem;
  border-radius:24px; background: linear-gradient(120deg, var(--c5) 0%, var(--c4) 58%, var(--c3) 100%); box-shadow: 0 14px 32px rgba(27,53,84,.28); }}
.hero-judul {{ font-size:2.35rem; font-weight:800; line-height:1.15; color:#ffffff !important; letter-spacing:-.01em; }}
.hero-sub {{ font-size:1rem; color: var(--c1) !important; margin-top:.4rem; max-width:62ch; }}
.hero-kanan {{ display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; }}
.hero-chip {{ display:flex; align-items:center; gap:.65rem; padding:.55rem .95rem; border-radius:16px; background: rgba(255,255,255,.14);
  border:1px solid rgba(255,255,255,.24); font-size:.78rem; line-height:1.3; color: var(--c1) !important; }}
.hero-chip b {{ display:block; color:#ffffff !important; font-weight:700; font-size:.88rem; }}
.hero-chip svg {{ color:#ffffff; }}
.avatar {{ width:34px; height:34px; border-radius:50%; display:grid; place-items:center; background: rgba(255,255,255,.2); color:#ffffff; }}

/* ---- kartu transparan ---- */
[class*="st-key-kartu"] {{ background: var(--kartu); border:1px solid var(--garis); border-radius:18px; padding:1rem 1.15rem;
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); box-shadow: var(--bayangan); }}
.judul-kartu {{ font-weight:700; font-size:.98rem; color:var(--teks); margin-bottom:.15rem; display:flex; align-items:center; gap:.5rem; }}
.judul-kartu svg {{ color: var(--aksen); }}
.sub-kartu {{ font-size:.78rem; color:var(--redup); margin-bottom:.4rem; }}
.judul-seksi {{ font-weight:700; font-size:1.05rem; color:var(--teks); margin:1.2rem 0 .6rem 0; }}
.grid-kpi {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:.9rem; margin-bottom:1rem; }}
.kpi, .kom {{ background: var(--kartu); border:1px solid var(--garis); border-radius:18px; padding:.95rem 1.1rem;
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); box-shadow: var(--bayangan); }}
.kpi-label {{ font-size:.78rem; color:var(--redup); }}
.kpi-nilai {{ font-size:1.65rem; font-weight:800; color:var(--teks); line-height:1.25; }}
.kpi-nilai.naik {{ color: var(--naik); }} .kpi-nilai.turun {{ color: var(--turun); }}
.kpi-cat {{ font-size:.76rem; color:var(--sedang); }}
.kom-kel {{ font-size:.66rem; letter-spacing:.07em; color:var(--redup); text-transform:uppercase; }}
.kom-nama {{ font-weight:700; font-size:.95rem; color:var(--teks); line-height:1.25; min-height:2.6em; }}
.kom-harga {{ font-size:1.3rem; font-weight:800; color:var(--teks); }}
.kom-sat {{ font-size:.72rem; font-weight:500; color:var(--redup); }}
.kom-baris {{ display:flex; flex-wrap:wrap; gap:.3rem; align-items:flex-start; }}
.kom-tanda {{ display:flex; flex-wrap:wrap; gap:.3rem; min-height:1.65rem; margin-top:.3rem; align-items:flex-start; }}
.kom-murah {{ font-size:.74rem; color:var(--sedang); margin-top:.1rem; min-height:1.1em; }}
.chip {{ display:inline-block; font-size:.74rem; padding:.12rem .55rem; border-radius:999px; color:var(--teks); border:1px solid var(--garis); }}
.chip.naik {{ background: color-mix(in srgb, var(--naik) 14%, transparent); border-color: color-mix(in srgb, var(--naik) 45%, transparent); }}
.chip.turun {{ background: color-mix(in srgb, var(--turun) 14%, transparent); border-color: color-mix(in srgb, var(--turun) 45%, transparent); }}
.chip.naik b {{ color: var(--naik); }} .chip.turun b {{ color: var(--turun); }}
.spark {{ width:100%; height:44px; margin-top:.2rem; display:block; }}

/* kartu komoditas yang bisa dibuka ke Monitoring */
[class*="st-key-kartu_kom"] {{ padding:.85rem 1rem .7rem 1rem; }}
[class*="st-key-kartu_kom"] .kom {{ background:none; border:0; box-shadow:none; padding:0; backdrop-filter:none; -webkit-backdrop-filter:none; }}
[class*="st-key-kartu_kom"] .stButton > button {{ background: transparent; color: var(--aksen) !important; border:1px solid var(--garis);
  font-size:.78rem; font-weight:600; padding:.15rem .6rem; min-height:0; width:100%; }}
[class*="st-key-kartu_kom"] .stButton > button:hover {{ background: color-mix(in srgb, var(--aksen) 10%, transparent); filter:none; }}

/* daftar perubahan terbesar */
.baris-ubah {{ display:grid; grid-template-columns:1.6rem 1fr auto auto; align-items:center; gap:.7rem; padding:.55rem .1rem; border-bottom:1px solid var(--garis); font-size:.9rem; color:var(--teks); }}
.baris-ubah:last-child {{ border-bottom:0; }}
.baris-ubah .no {{ color:var(--redup); font-size:.82rem; }}
.baris-ubah .hrg {{ color:var(--sedang); font-size:.8rem; font-variant-numeric: tabular-nums; }}
.kosong {{ color:var(--redup); font-size:.86rem; padding:.8rem 0; }}
ul.sorotan {{ list-style:none; margin:.2rem 0 0 0; padding:0; }}
ul.sorotan li {{ padding:.5rem 0; border-bottom:1px solid var(--garis); font-size:.88rem; color:var(--teks); line-height:1.4; }}
ul.sorotan li:last-child {{ border-bottom:0; }}

/* ---- tabel ---- */
.tbl-wrap {{ overflow:auto; border-radius:14px; border:1px solid var(--garis); }}
table.tbl {{ width:100%; border-collapse:collapse; font-size:.82rem; color:var(--teks); }}
table.tbl th {{ position:sticky; top:0; text-align:left; padding:.55rem .75rem; background: var(--c1); color:var(--c5); font-weight:700; border-bottom:1px solid var(--garis); white-space:nowrap; }}
table.tbl td {{ padding:.5rem .75rem; border-bottom:1px solid var(--garis); white-space:nowrap; background: rgba(255,255,255,.55); }}
table.tbl td.num, table.tbl th.num {{ text-align:right; font-variant-numeric: tabular-nums; }}
table.tbl tr:last-child td {{ border-bottom:0; }}

/* ---- kontrol ---- */
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="textarea"] {{
  background: var(--input) !important; border-color: var(--garis) !important; border-radius: 12px !important; }}
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] * {{ color: var(--teks) !important; }}
[data-baseweb="popover"] ul, [data-baseweb="popover"] [role="listbox"], [data-baseweb="calendar"] {{ background: var(--popup) !important; color: var(--teks) !important; }}
[data-baseweb="popover"] li, [data-baseweb="calendar"] * {{ color: var(--teks) !important; }}
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {{
  border-radius: 12px; border: 0; color: #fff; font-weight: 600; background: linear-gradient(90deg, var(--c5), var(--c4)); }}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {{ filter: brightness(1.12); color:#fff; }}
.stButton > button *, .stDownloadButton > button *, [data-testid="stFormSubmitButton"] > button * {{ color:#fff !important; }}
[class*="st-key-kartu_kom"] .stButton > button * {{ color: var(--aksen) !important; }}

/* filter segmented control */
[data-testid="stButtonGroup"] {{ gap:.3rem; flex-wrap:wrap; }}
button[data-testid="stBaseButton-segmented_control"], button[data-testid="stBaseButton-segmented_controlActive"] {{
  border-radius:12px; border:1px solid var(--garis); padding:.35rem 1rem; font-weight:600; font-size:.86rem; min-height:2.35rem; }}
button[data-testid="stBaseButton-segmented_control"] {{ background: rgba(255,255,255,.85); color: var(--sedang); }}
button[data-testid="stBaseButton-segmented_control"]:hover {{ background: var(--c1); border-color: var(--c2); }}
button[data-testid="stBaseButton-segmented_controlActive"] {{ background: linear-gradient(90deg, var(--c5), var(--c4)); color:#ffffff; border-color: var(--c5); }}
button[data-testid="stBaseButton-segmented_control"] *, button[data-testid="stBaseButton-segmented_controlActive"] * {{ color: inherit !important; }}
/* cadangan bila Streamlit lama memakai radio */
[data-testid="stMain"] [role="radiogroup"] {{ gap:.4rem; flex-wrap: wrap; }}
[data-testid="stMain"] [role="radiogroup"] label {{ padding:.3rem .85rem; border-radius:12px; border:1px solid var(--garis); background: rgba(255,255,255,.85); cursor:pointer; }}
[data-testid="stMain"] [role="radiogroup"] label > div:first-child {{ display:none; }}
[data-testid="stMain"] [role="radiogroup"] label:has(input:checked) {{ background: linear-gradient(90deg, var(--c5), var(--c4)); border-color: var(--c5); }}
[data-testid="stMain"] [role="radiogroup"] label:has(input:checked) * {{ color:#fff !important; }}
.st-key-kartu_filter [data-testid="stWidgetLabel"] * {{ font-weight:600; color: var(--sedang) !important; }}

[data-testid="stFileUploaderDropzone"] {{ background: var(--input); border:1px dashed var(--c2); border-radius:14px; }}
[data-testid="stFileUploaderDropzone"] * {{ color: var(--sedang) !important; }}
button[data-baseweb="tab"] {{ color: var(--redup); }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: var(--teks); }}
[data-baseweb="tab-highlight"] {{ background: var(--aksen) !important; }}
[data-testid="stExpander"] {{ background: var(--kartu); border:1px solid var(--garis); border-radius:14px; }}
"""


# ---------- grafik Plotly ----------
def atur_grafik(fig, _=None, tinggi=360, legenda=False):
    p = TEMA
    fig.update_layout(
        height=tinggi, margin=dict(l=8, r=8, t=10, b=8), separators=",.",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=p["sedang"]),
        hoverlabel=dict(bgcolor=p["kartu_solid"], font=dict(color=p["teks"]), bordercolor=p["garis"]),
        showlegend=legenda, legend=dict(orientation="h", y=1.12, x=0, font=dict(color=p["sedang"])))
    fig.update_xaxes(gridcolor=p["grid"], zerolinecolor=p["grid"], linecolor=p["grid"], tickfont=dict(color=p["redup"]))
    fig.update_yaxes(gridcolor=p["grid"], zerolinecolor=p["grid"], linecolor=p["grid"], tickfont=dict(color=p["redup"]))
    return fig


# ---------- komponen HTML ----------
def brand(logo_uri: str | None = None) -> str:
    if logo_uri:
        logo = f'<div class="brand-logo"><img src="{logo_uri}" alt="Logo"></div>'
    else:                                    # cadangan sampai berkas logo diletakkan di assets/
        logo = f'<div class="brand-logo cadangan">{ikon("tren", 26)}</div>'
    return (f'<div class="brand">{logo}<div class="brand-teks"><div class="brand-nama">SIMONIKA</div>'
            '<div class="brand-sub">Sistem Monitoring dan Informasi Harga Komoditas</div></div></div>'
            '<div class="menu-judul">Main Menu</div>')


def side_info(awal, akhir, n_kom: int, n_pasar: int) -> str:
    return (f'<div class="side-info"><b>Rentang data</b><br>{escape(tgl(awal))} – {escape(tgl(akhir))}<br>'
            f'{n_kom} komoditas · {n_pasar} pasar Surabaya</div>')


def navbar(judul: str, sub: str, tanggal_data, status: str) -> str:
    """Banner judul halaman berlatar warna palet."""
    return (f'<div class="hero"><div><div class="hero-judul">{escape(judul)}</div><div class="hero-sub">{escape(sub)}</div></div>'
            f'<div class="hero-kanan"><div class="hero-chip">{ikon("kalender", 22)}<div>Data per<b>{escape(tgl(tanggal_data))}</b></div></div>'
            f'<div class="hero-chip"><div class="avatar">{ikon("user", 18)}</div><div>Status<b>{escape(status)}</b></div></div></div></div>')


def judul_kartu(judul: str, sub: str = "", ikon_nama: str | None = None) -> str:
    i = ikon(ikon_nama, 18) if ikon_nama else ""
    return f'<div class="judul-kartu">{i}{escape(judul)}</div>' + (f'<div class="sub-kartu">{escape(sub)}</div>' if sub else "")


def judul_seksi(teks: str) -> str:
    return f'<div class="judul-seksi">{escape(teks)}</div>'


def kartu_kpi(label: str, nilai: str, catatan: str = "", catatan2: str = "") -> str:
    c2 = f'<div class="kpi-cat">{escape(catatan2)}</div>' if catatan2 else ""
    return (f'<div class="kpi"><div class="kpi-label">{escape(label)}</div><div class="kpi-nilai">{escape(nilai)}</div>'
            f'<div class="kpi-cat">{escape(catatan)}</div>{c2}</div>')


def kartu_banding(label: str, ket: str, p: dict) -> str:
    """Kartu pembanding periode. p = hasil metrik.pembanding (now, now_tgl, ref, ref_tgl, pct)."""
    x = p.get("pct")
    if x is None or pd.isna(x):
        return (f'<div class="kpi"><div class="kpi-label">{escape(label)} · {escape(ket)}</div><div class="kpi-nilai">–</div>'
                f'<div class="kpi-cat">Data pembanding tidak tersedia</div></div>')
    arah = "naik" if x > 0 else "turun" if x < 0 else ""
    simbol = "▲ " if x > 0 else "▼ " if x < 0 else "● "
    return (f'<div class="kpi"><div class="kpi-label">{escape(label)} · {escape(ket)}</div>'
            f'<div class="kpi-nilai {arah}">{simbol}{escape(pct(x))}</div>'
            f'<div class="kpi-cat">{escape(rp(p["now"]))} vs {escape(rp(p["ref"]))}</div>'
            f'<div class="kpi-cat">dibanding {escape(tgl(p["ref_tgl"]))}</div></div>')


def chip_delta(x, teks_tambahan: str = "") -> str:
    if x is None or pd.isna(x):
        return '<span class="chip">–</span>'
    if abs(x) < 0.05:
        return f'<span class="chip">● 0,0%{escape(teks_tambahan)}</span>'
    arah, simbol = ("naik", "▲") if x > 0 else ("turun", "▼")
    return f'<span class="chip {arah}"><b>{simbol}</b> {pct(x)}{escape(teks_tambahan)}</span>'


def sparkline(nilai) -> str:
    v = [float(x) for x in nilai if pd.notna(x)]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    rentang = (hi - lo) or 1.0
    xs = [i * 160 / (len(v) - 1) for i in range(len(v))]
    ys = [40 - (x - lo) / rentang * 34 for x in v]
    titik = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    warna = TEMA["aksen"]
    return (f'<svg class="spark" viewBox="0 0 160 44" preserveAspectRatio="none">'
            f'<polygon points="0,44 {titik} 160,44" fill="{PAL["c2"]}" opacity="0.30"/>'
            f'<polyline points="{titik}" fill="none" stroke="{warna}" stroke-width="2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3" fill="{PAL["c5"]}"/></svg>')


def kartu_komoditas(kelompok, nama, satuan, harga, delta, nilai_spark, murah=None, penanda=None) -> str:
    """murah = (pasar, harga) atau None; penanda = (teks, 'naik'|'turun') atau None."""
    tanda = ""
    if penanda:
        teks, arah = penanda
        tanda = f'<span class="chip {arah}">{escape(teks)}</span>'
    baris_murah = f"Termurah: {escape(murah[0])} · {escape(rp(murah[1]))}" if murah else ""
    return (f'<div class="kom"><div class="kom-kel">{escape(str(kelompok))}</div><div class="kom-nama">{escape(str(nama))}</div>'
            f'<div class="kom-harga">{rp(harga)} <span class="kom-sat">/ {escape(str(satuan))}</span></div>'
            f'<div class="kom-baris">{chip_delta(delta, " · minggu ini")}</div><div class="kom-tanda">{tanda}</div>{sparkline(nilai_spark)}'
            f'<div class="kom-murah">{baris_murah}</div></div>')


def daftar_perubahan(baris, kosong: str) -> str:
    """baris = iterable (komoditas, harga, satuan, persen)."""
    isi = [f'<div class="baris-ubah"><span class="no">{i}.</span><span>{escape(str(k))}</span>'
           f'<span class="hrg">{escape(rp(h))} / {escape(str(s))}</span>{chip_delta(p)}</div>'
           for i, (k, h, s, p) in enumerate(baris, start=1)]
    return "".join(isi) if isi else f'<div class="kosong">{escape(kosong)}</div>'


def sorotan_html(kalimat: list[str]) -> str:
    if not kalimat:
        return '<div class="kosong">Belum ada sorotan untuk tanggal ini.</div>'
    return '<ul class="sorotan">' + "".join(f"<li>{escape(k)}</li>" for k in kalimat) + "</ul>"


def tabel_html(df: pd.DataFrame, format: dict | None = None, tinggi_maks: int = 420) -> str:
    """Tabel HTML bertema."""
    format = format or {}
    num = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    kepala = "".join(f'<th class="{"num" if c in num else ""}">{escape(str(c))}</th>' for c in df.columns)
    baris = []
    for _, r in df.iterrows():
        sel = []
        for c in df.columns:
            v = r[c]
            teks = format[c](v) if c in format else ("–" if pd.isna(v) else str(v))
            sel.append(f'<td class="{"num" if c in num else ""}">{escape(teks)}</td>')
        baris.append("<tr>" + "".join(sel) + "</tr>")
    return (f'<div class="tbl-wrap" style="max-height:{tinggi_maks}px"><table class="tbl"><thead><tr>{kepala}</tr></thead>'
            f'<tbody>{"".join(baris)}</tbody></table></div>')
