import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import json
import time
from datetime import datetime

st.set_page_config(
    page_title="ARON Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
div[data-testid="metric-container"] {
    background: #1a1d2e; border: 1px solid #2a2d45;
    border-radius: 12px; padding: 16px 20px;
}
div[data-testid="metric-container"] label { color: #9ca3af !important; font-size: 13px !important; }
div[data-testid="metric-container"] [data-testid="metric-value"] {
    color: #f9fafb !important; font-size: 26px !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { color: #c9d1d9 !important; }
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #21262d; }
hr { border-color: #21262d !important; }
</style>
""", unsafe_allow_html=True)

# ── Telegram ──────────────────────────────────────────────────────────────────
try:
    TELEGRAM_TOKEN   = st.secrets["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception:
    TELEGRAM_TOKEN   = ""
    TELEGRAM_CHAT_ID = ""

def send_telegram(text):
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
        req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False

def markt_offen():
    now  = datetime.now()
    wday = now.weekday()
    if wday >= 5: return False
    t = now.hour * 60 + now.minute
    return 930 <= t <= 1320

def monitor_fehler(typ, details=""):
    if "gemeldete_fehler" not in st.session_state:
        st.session_state["gemeldete_fehler"] = set()
    if typ in st.session_state["gemeldete_fehler"]: return
    st.session_state["gemeldete_fehler"].add(typ)
    now = datetime.now().strftime("%H:%M:%S")
    nachrichten = {
        "SCAN_ABSTURZ":    f"🔴 <b>ARON Scanner — Absturz</b>\n<code>{details}</code>\n🕐 {now}",
        "HOHE_FEHLERQUOTE":f"⚠️ <b>ARON Scanner — Hohe Fehlerquote</b>\n{details} Aktien nicht ladbar\n🕐 {now}",
        "SECRETS_FEHLEN":  f"🔐 <b>ARON Scanner — Secrets fehlen!</b>\nTelegram-Token nicht gefunden.\n🕐 {now}",
    }
    send_telegram(nachrichten.get(typ, f"⚠️ {typ}: {details}\n🕐 {now}"))

def monitor_ok():
    if not markt_offen(): return
    import os
    heute     = datetime.now().strftime("%Y-%m-%d")
    flag_file = f"/tmp/aron_ok_{heute}.flag"
    if os.path.exists(flag_file): return
    try: open(flag_file, "w").close()
    except Exception: pass
    send_telegram(
        f"✅ <b>ARON Scanner läuft</b>\n"
        f"Erster Scan des Tages abgeschlossen.\n"
        f"340 Aktien werden überwacht.\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    )

# ── Watchlist (340 Ticker — Nasdaq + S&P500, ohne BRK.B) ──────────────────────
WATCHLIST = [
    "AAL","AAPL","ABBV","ABNB","ABT","ACN","ADBE","ADI","ADM","ADP","ADSK",
    "AEP","AES","AFL","AIG","AIZ","AJG","ALK","ALLE","AMAT","AMD","AME",
    "AMGN","AMT","AMZN","ANET","ANSS","AON","AOS","APA","APD","APH","ASML",
    "AVGO","AXP","AZN","AZO","BA","BAC","BBWI","BDX","BEN","BIIB","BK",
    "BKNG","BKR","BLK","BMY","BSX","BWA","BX","C","CAG","CARR","CAT","CB",
    "CCEP","CDNS","CDW","CEG","CHD","CHRW","CHTR","CI","CINF","CL","CMA",
    "CMCSA","CME","CMG","CMI","COF","COP","COST","CPB","CPRT","CPT","CRM",
    "CRWD","CSCO","CSGP","CSX","CTAS","CTSH","CVS","CVX","DAL","DASH","DD",
    "DDOG","DE","DHI","DHR","DIS","DLTR","DOW","DUK","DVA","DXCM","EA",
    "EBAY","ECL","ELV","EMN","EMR","ENPH","EOG","EQIX","ETN","ETSY",
    "EVRG","EW","EXC","FANG","FAST","FCX","FDX","FFIV","FI","FMC","FSLR",
    "FTNT","GD","GE","GEHC","GEN","GFS","GILD","GIS","GLW","GM","GNRC",
    "GOOG","GOOGL","GS","GWW","HAL","HAS","HCA","HD","HES","HII","HLT",
    "HON","HPE","HPQ","HRL","HSIC","HSY","HUM","IBM","ICE","IDXX",
    "ILMN","INTC","INTU","IP","IPG","ISRG","ITW","IVZ","JCI","JD","JKHY",
    "JNJ","JNPR","JPM","K","KDP","KEY","KHC","KLAC","KMX","KO","KR","L",
    "LEN","LHX","LIN","LKQ","LLY","LMT","LOW","LRCX","LULU","LYB","LYV",
    "MA","MAR","MCD","MCHP","MCK","MCO","MDB","MDLZ","MDT","MELI","MET",
    "META","MGM","MHK","MKTX","MLM","MMC","MMM","MNST","MO","MOS","MPC",
    "MRK","MRNA","MRO","MRVL","MS","MSCI","MSFT","MSI","MTCH","MU","NCLH",
    "NEE","NEM","NFLX","NI","NKE","NOC","NOW","NRG","NSC","NUE","NVDA",
    "NWS","NWSA","NXPI","ODFL","ON","ORCL","ORLY","OXY","PANW","PARA",
    "PAYC","PAYX","PCAR","PDD","PEG","PEP","PFE","PG","PGR","PH","PHM",
    "PLD","PM","PNC","PNR","PPG","PRU","PSA","PSX","PYPL","QCOM","QRVO",
    "RCL","REGN","RHI","RL","ROK","ROL","ROP","ROST","RTX","RVTY","SBUX",
    "SCHW","SEE","SHW","SIRI","SJM","SLB","SNPS","SO","SPGI","SPLK","SRE",
    "STT","STX","STZ","SYK","SYY","T","TAP","TDG","TEAM","TGT","TJX",
    "TMO","TMUS","TPR","TRV","TSLA","TSN","TT","TTD","TTWO","TXN","UAL",
    "UDR","UHS","UNH","UNP","UPS","USB","V","VFC","VLO","VRSK","VRTX",
    "VTRS","VZ","WAB","WBA","WBD","WDAY","WDC","WEC","WELL","WFC","WHR",
    "WM","WMT","WYNN","XEL","XOM","XRAY","YUM","ZBRA","ZION","ZS","ZTS",
]

# ── Daten & Hilfsfunktionen ───────────────────────────────────────────────────
def normalize_df(df):
    if df is None or df.empty: return None
    cols = {c: (c[0] if isinstance(c, tuple) else c) for c in df.columns}
    df = df.rename(columns=cols)
    return df.loc[:, ~df.columns.duplicated()]

@st.cache_data(ttl=60)
def get_data(ticker):
    for attempt in range(3):
        try:
            time.sleep(0.6)
            df = yf.download(ticker, period="1d", interval="1m",
                             progress=False, auto_adjust=True, threads=False)
            df = normalize_df(df)
            if df is None or len(df) < 30:
                time.sleep(2); continue
            return df
        except Exception:
            if attempt < 2: time.sleep(3)
    return None

@st.cache_data(ttl=300)
def get_vix():
    for attempt in range(3):
        try:
            time.sleep(0.3)
            df = yf.download("^VIX", period="1d", interval="5m",
                             progress=False, auto_adjust=True, threads=False)
            df = normalize_df(df)
            if df is None or df.empty:
                time.sleep(2); continue
            return round(float(df["Close"].values.flatten().astype(float)[-1]), 2)
        except Exception:
            if attempt < 2: time.sleep(3)
    return None

def calc_vwap(df):
    try:
        tp   = (df["High"] + df["Low"] + df["Close"]) / 3
        vwap = (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()
        return float(vwap.iloc[-1])
    except: return None

# ── Retracements ──────────────────────────────────────────────────────────────
def calc_retracements(df, mom_kerzen):
    """Retracements der Momentumbewegung (letzte mom_kerzen * 3 Kerzen)."""
    try:
        seg  = df.iloc[-min(len(df), mom_kerzen * 3):]
        high = float(seg["High"].values.flatten().astype(float).max())
        low  = float(seg["Low"].values.flatten().astype(float).min())
        diff = high - low
        if diff == 0: return None
        return {
            "high":   high, "low": low,
            "rt382":  low + diff * 0.382,
            "rt50":   low + diff * 0.500,
            "rt618":  low + diff * 0.618,
        }
    except: return None

# ── Kriterien-Checks laut PDF ─────────────────────────────────────────────────

def check_momentum(df, mom_kerzen, min_mom_pct, min_richtung):
    """
    PDF: "Innerhalb weniger Minuten sehr große Kerzen."
    Kein langsamer Trend mit gleichen Kerzengrößen.
    FIX: Beschleunigung strenger — letzte Kerzen müssen deutlich größer sein.
    """
    try:
        recent = df.iloc[-mom_kerzen:]
        kurs   = float(df["Close"].values.flatten().astype(float)[-1])
        bodies = abs(recent["Close"] - recent["Open"])
        avg_body_pct = float(bodies.mean()) / kurs * 100

        up = int((recent["Close"] > recent["Open"]).sum())
        dn = int((recent["Close"] < recent["Open"]).sum())
        tot = len(recent)
        richtung = None
        if up / tot >= min_richtung:   richtung = "LONG"
        elif dn / tot >= min_richtung: richtung = "SHORT"

        # KORREKTUR laut PDF: Beschleunigung strenger auf 120%
        # Letzte 3 Kerzen müssen deutlich größer als erste 3 sein
        if tot >= 6:
            frueh = float(bodies.iloc[:3].mean())
            spaet = float(bodies.iloc[-3:].mean())
            beschleunigt = spaet >= frueh * 1.2  # Strenger: 120% statt 80%
        else:
            beschleunigt = True

        ok = avg_body_pct >= min_mom_pct and richtung is not None and beschleunigt
        return ok, richtung, round(avg_body_pct, 3)
    except: return False, None, 0.0

def check_liquiditaet(df, max_gap_pct):
    """PDF: Schluss der vorigen Kerze = Eröffnung der nächsten. Keine Lücken."""
    try:
        closes = df["Close"].values.flatten().astype(float)
        opens  = df["Open"].values.flatten().astype(float)
        gaps   = abs(opens[1:] - closes[:-1]) / closes[:-1] * 100
        recent = gaps[-20:] if len(gaps) >= 20 else gaps
        max_g  = float(np.max(recent))
        return max_g < max_gap_pct, round(max_g, 4)
    except: return False, 0.0

def check_ema9_bruch(df):
    """PDF: Kompletter Kerzenkörper (Open+Close) muss durch EMA9 brechen."""
    try:
        if len(df) < 5: return False, None, 0.0
        ema9     = df["Close"].ewm(span=9, adjust=False).mean()
        db_open  = float(df["Open"].iloc[-2])
        db_close = float(df["Close"].iloc[-2])
        db_ema   = float(ema9.iloc[-2])
        vor_ema  = float(ema9.iloc[-3])
        vor_close= float(df["Close"].iloc[-3])
        bruch_short = db_close < db_ema and db_open < db_ema and vor_close >= vor_ema
        bruch_long  = db_close > db_ema and db_open > db_ema and vor_close <= vor_ema
        ema_aktuell = round(float(ema9.iloc[-1]), 2)
        if bruch_short: return True, "SHORT", ema_aktuell
        if bruch_long:  return True, "LONG",  ema_aktuell
        return False, None, ema_aktuell
    except: return False, None, 0.0

def check_folgekerze(df, bruch_richtung):
    """PDF: Folgekerze überschreitet Hoch (Long) oder Tief (Short) der Durchbruchskerze."""
    try:
        if len(df) < 3 or bruch_richtung is None: return False
        db_high    = float(df["High"].iloc[-2])
        db_low     = float(df["Low"].iloc[-2])
        folge_high = float(df["High"].iloc[-1])
        folge_low  = float(df["Low"].iloc[-1])
        if bruch_richtung == "LONG":  return folge_high > db_high
        if bruch_richtung == "SHORT": return folge_low  < db_low
        return False
    except: return False

def check_vwap(df, rt, richtung):
    """
    PDF: VWAP weit vom 0.5er RT entfernt.
    Long:  VWAP >= Mitte(50/61) — mindestens in der Mitte zwischen 50er und 61er
    Short: VWAP <= Mitte(38/50) — mindestens in der Mitte zwischen 38er und 50er
    """
    try:
        vwap = calc_vwap(df)
        if vwap is None or rt is None: return False, None
        mitte_long  = (rt["rt50"]  + rt["rt618"]) / 2
        mitte_short = (rt["rt382"] + rt["rt50"])  / 2
        if richtung == "LONG":  ok = vwap >= mitte_long
        elif richtung == "SHORT": ok = vwap <= mitte_short
        else: ok = False
        return ok, round(vwap, 2)
    except: return False, None

def check_crv(df, rt, richtung, crv_min):
    """
    PDF FIX: TP1 immer auf 38er RT (nicht 61er).
    SL = 1-2 durchschnittliche Kerzen vom letzten Hoch/Tief entfernt.
    """
    try:
        if rt is None or richtung is None: return False, 0.0, 0.0, 0.0
        kurs    = float(df["Close"].values.flatten().astype(float)[-1])
        bodies  = abs(df["Close"].iloc[-5:] - df["Open"].iloc[-5:])
        avg_body= float(bodies.mean())
        if richtung == "LONG":
            # KORREKTUR: TP auf 38er RT (nicht 61er laut PDF)
            tp = rt["rt618"]   # erstes Ziel 38er von unten gezählt = 61er von oben
            sl = rt["low"]  - avg_body * 1.5
        elif richtung == "SHORT":
            tp = rt["rt382"]   # erstes Ziel 38er = 38er von oben
            sl = rt["high"] + avg_body * 1.5
        else:
            return False, 0.0, 0.0, 0.0
        risk   = abs(kurs - sl)
        reward = abs(tp - kurs)
        crv    = reward / risk if risk > 0 else 0
        return crv >= crv_min, round(crv, 2), round(tp, 2), round(sl, 2)
    except: return False, 0.0, 0.0, 0.0

# ── Scan-Funktion ─────────────────────────────────────────────────────────────
def scan_ticker(ticker, params):
    r = dict(ticker=ticker, kurs="-", status="NEIN", richtung="-",
             momentum=False, liquiditaet=False, ema9=False,
             folgekerze=False, vwap=False, crv=False,
             vwap_val="-", ema9_val="-", tp="-", sl="-",
             crv_val="-", mom_pct="-", max_gap="-", erfuellt=0, debug="")
    df = get_data(ticker)
    if df is None:
        r["status"] = "FEHLER"; return r
    try:
        kurs = float(df["Close"].values.flatten().astype(float)[-1])
        r["kurs"] = round(kurs, 2)

        mom_ok, richtung, mom_pct = check_momentum(
            df, params["mom_kerzen"], params["min_mom_pct"], params["min_richtung"])
        r["momentum"] = mom_ok; r["mom_pct"] = mom_pct
        r["richtung"] = richtung or "-"

        liq_ok, max_gap = check_liquiditaet(df, params["max_gap_pct"])
        r["liquiditaet"] = liq_ok; r["max_gap"] = max_gap

        bruch_ok, bruch_dir, ema9_val = check_ema9_bruch(df)
        r["ema9"] = bruch_ok; r["ema9_val"] = ema9_val
        if richtung is None and bruch_dir:
            richtung = bruch_dir; r["richtung"] = richtung

        folge_ok = check_folgekerze(df, bruch_dir if bruch_ok else richtung)
        r["folgekerze"] = folge_ok

        rt = calc_retracements(df, params["mom_kerzen"])
        vwap_ok, vwap_val = check_vwap(df, rt, richtung)
        r["vwap"] = vwap_ok
        r["vwap_val"] = f"${vwap_val}" if vwap_val else "-"

        crv_ok, crv_val, tp, sl = check_crv(df, rt, richtung, params["crv_min"])
        r["crv"] = crv_ok; r["crv_val"] = crv_val
        r["tp"]  = f"${tp}"; r["sl"] = f"${sl}"

        erf = sum([mom_ok, liq_ok, bruch_ok, folge_ok, vwap_ok, crv_ok])
        r["erfuellt"] = erf
        r["status"]   = "SETUP ✓" if erf==6 else "FAST" if erf>=4 else "NEIN"

        fehlend = []
        if not mom_ok:   fehlend.append(f"Momentum ({mom_pct:.2f}%)")
        if not liq_ok:   fehlend.append(f"Gap ({max_gap:.3f}%)")
        if not bruch_ok: fehlend.append("EMA9 Bruch")
        if not folge_ok: fehlend.append("Folgekerze")
        if not vwap_ok:  fehlend.append(f"VWAP ({vwap_val})")
        if not crv_ok:   fehlend.append(f"CRV ({crv_val})")
        r["debug"] = " | ".join(fehlend) if fehlend else "Alle OK"
    except Exception as e:
        r["status"] = "FEHLER"; r["debug"] = str(e)
    return r

# ── Dashboard ─────────────────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        st.error("⛔ Telegram Secrets fehlen!")
        monitor_fehler("SECRETS_FEHLEN")

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("⚡ ARON Scanner")
        st.caption("Momentum + EMA9 Bruch + Folgekerze + VWAP + CRV | 1-Minuten-Chart | 340 Aktien")
    with col_h2:
        st.metric("🕐 Uhrzeit", datetime.now().strftime("%H:%M:%S"))

    with st.sidebar:
        st.markdown("### ⚙️ Parameter")
        params = {
            "mom_kerzen":   st.slider("Momentum Kerzen",        5,  20,  10),
            "min_mom_pct":  st.slider("Min. Kerzengröße %",     0.2, 3.0, 1.0, 0.1),
            "min_richtung": st.slider("Min. Richtung (Anteil)", 0.5, 0.9, 0.65, 0.05),
            "max_gap_pct":  st.slider("Max. Gap % (Liquidität)",0.01, 0.1, 0.03, 0.005),
            "crv_min":      st.slider("Min. CRV",               0.5, 3.0, 1.0, 0.1),
        }
        st.divider()
        st.markdown("### 🔔 Telegram Alerts")
        tg_aktiv = st.toggle("Benachrichtigungen aktiv", value=True)
        st.caption("@Rectangelbot")
        if st.button("🧪 Test-Nachricht senden"):
            ok = send_telegram("🧪 <b>Test</b> — ARON Scanner läuft!")
            st.success("✅ Gesendet!") if ok else st.error("❌ Fehler")
        st.divider()
        st.markdown("### 📋 Watchlist")
        custom    = st.text_area("Ticker (eine pro Zeile)", "\n".join(WATCHLIST), height=160)
        watchlist = [t.strip().upper() for t in custom.split("\n") if t.strip()]
        st.caption(f"**{len(watchlist)}** Aktien")
        show_debug = st.checkbox("Debug anzeigen", value=False)
        st.divider()
        auto_ref = st.toggle("🔄 Auto-Refresh (1 min)", value=True)
        st.caption("🕐 US-Markt: 15:30 – 22:00 Uhr DE")

    # VIX
    vix = get_vix()
    if vix:
        if vix >= 30:
            st.error(f"⛔ VIX {vix} — ARON wird ab VIX 30 nicht gehandelt!")
            if auto_ref: time.sleep(90); st.rerun()
            return
        elif vix >= 20:
            st.warning(f"⚡ VIX {vix} — Vorsicht! Ab 20 aufpassen.")
        else:
            st.success(f"✅ VIX {vix} — OK.")
    st.divider()

    if "gemeldet"         not in st.session_state: st.session_state["gemeldet"]         = set()
    if "gemeldete_fehler" not in st.session_state: st.session_state["gemeldete_fehler"] = set()
    if "letzter_ok_tag"   not in st.session_state: st.session_state["letzter_ok_tag"]   = ""

    rows, neue_setups, fehler_ticker = [], [], []
    progress = st.progress(0, text="Scanner läuft …")

    try:
        for i, ticker in enumerate(watchlist):
            progress.progress((i+1)/len(watchlist), f"Scanne {ticker} … ({i+1}/{len(watchlist)})")
            r = scan_ticker(ticker, params)

            if r["status"] == "FEHLER":
                fehler_ticker.append(ticker)

            # Telegram Alert
            if tg_aktiv and r["status"] == "SETUP ✓" and ticker not in st.session_state["gemeldet"]:
                st.session_state["gemeldet"].add(ticker)
                neue_setups.append(ticker)
                now_s = datetime.now().strftime("%H:%M:%S")
                send_telegram(
                    f"⚡ <b>ARON SETUP ✅</b>\n"
                    f"<b>{ticker}</b> — alle 6 Kriterien erfüllt\n"
                    f"Richtung: <b>{r['richtung']}</b> | Kurs: <b>${r['kurs']}</b>\n"
                    f"EMA9: ${r['ema9_val']} | VWAP: {r['vwap_val']}\n"
                    f"TP: {r['tp']} | SL: {r['sl']} | CRV: {r['crv_val']}\n"
                    f"🕐 {now_s}"
                )
            if r["status"] != "SETUP ✓":
                st.session_state["gemeldet"].discard(ticker)

            row = {
                "Aktie":      r["ticker"],
                "Kurs":       f"${r['kurs']}",
                "Richtung":   r["richtung"],
                "Status":     r["status"],
                "Momentum":   "✓" if r["momentum"]    else "✗",
                "Liquidität": "✓" if r["liquiditaet"] else "✗",
                "EMA9 Bruch": "✓" if r["ema9"]        else "✗",
                "Folgekerze": "✓" if r["folgekerze"]  else "✗",
                "VWAP":       "✓" if r["vwap"]        else "✗",
                "CRV":        "✓" if r["crv"]         else "✗",
                "VWAP Kurs":  r["vwap_val"],
                "EMA9":       f"${r['ema9_val']}",
                "TP":         r["tp"],
                "SL":         r["sl"],
                "CRV Ratio":  r["crv_val"],
                "Erfüllt":    r["erfuellt"],
            }
            if show_debug: row["Debug"] = r.get("debug", "")
            rows.append(row)

        # Monitoring
        fehler_pct = len(fehler_ticker) / max(len(watchlist), 1) * 100
        if fehler_pct > 30 and markt_offen():
            monitor_fehler("HOHE_FEHLERQUOTE", f"{len(fehler_ticker)} von {len(watchlist)}")
        if tg_aktiv and fehler_pct <= 30:
            monitor_ok()

    except Exception as e:
        monitor_fehler("SCAN_ABSTURZ", str(e)[:200])
        st.error(f"⛔ Fehler: {e}"); st.stop()

    progress.empty()
    if neue_setups:
        st.balloons()
        st.success(f"🔔 Alert gesendet: {', '.join(neue_setups)}")

    df_all  = pd.DataFrame(rows)
    scan_ts = datetime.now().strftime("%H:%M:%S")

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("📊 Gescannt",     len(df_all))
    c2.metric("✅ Setup",         len(df_all[df_all["Status"]=="SETUP ✓"]))
    c3.metric("🔎 Fast",          len(df_all[df_all["Status"]=="FAST"]))
    c4.metric("🔴 Long / Short",  f"{len(df_all[df_all['Richtung']=='LONG'])} / {len(df_all[df_all['Richtung']=='SHORT'])}")
    c5.metric("🔔 Aktive Alerts", len(st.session_state["gemeldet"]))
    c6.metric("🕐 Scan um",       scan_ts)
    st.divider()

    df_s = df_all[df_all["Status"]=="SETUP ✓"]
    if not df_s.empty:
        st.subheader(f"✅ ARON Setup vollständig ({len(df_s)})")
        st.dataframe(df_s.drop(columns=["Erfüllt"]), use_container_width=True, hide_index=True)
    else:
        st.info("📭 Aktuell kein vollständiges ARON-Setup.")

    df_f = df_all[df_all["Status"]=="FAST"].sort_values("Erfüllt", ascending=False)
    if not df_f.empty:
        st.subheader(f"🔎 Fast erfüllt — beobachten ({len(df_f)})")
        st.dataframe(df_f.drop(columns=["Erfüllt"]), use_container_width=True, hide_index=True)

    with st.expander(f"📋 Alle {len(df_all)} Aktien"):
        st.dataframe(df_all.sort_values("Erfüllt", ascending=False).drop(columns=["Erfüllt"]),
                     use_container_width=True, hide_index=True)

    with st.expander("📖 Kriterien laut PDF"):
        st.markdown("""
| # | Kriterium | Regel aus der PDF |
|---|-----------|-------------------|
| 1 | **Momentum** | Sehr große Kerzen in wenigen Minuten — keine gleichmäßigen Trends. Beschleunigung: letzte 3 Kerzen ≥ 120% der ersten 3. |
| 2 | **Liquidität** | Kein Gap zwischen Kerzen — Schluss der vorigen Kerze = Eröffnung der nächsten |
| 3 | **EMA9 Bruch** | Kompletter Kerzenkörper (Open + Close) muss durch EMA9 brechen |
| 4 | **Folgekerze** | Überschreitet Hoch (Long) oder Tief (Short) der Durchbruchskerze |
| 5 | **VWAP** | Long: VWAP ≥ Mitte(50er/61er RT) · Short: VWAP ≤ Mitte(38er/50er RT) |
| 6 | **CRV ≥ 1:1** | TP auf 38er RT, SL 1-2 Kerzen vom letzten Hoch/Tief entfernt |
        """)

    if auto_ref:
        import os
        try:
            with open("/tmp/aron_keepalive.txt", "w") as f:
                f.write(datetime.now().isoformat())
        except Exception:
            pass
        time.sleep(90)
        st.rerun()

if __name__ == "__main__":
    main()
