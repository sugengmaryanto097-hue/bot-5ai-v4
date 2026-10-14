from flask import Flask, render_template_string, redirect
import threading, time, requests
from datetime import datetime, timedelta
import pytz

BOT_TOKEN = "8848320770:AAG3Stf9zXlD5VliR1A5zXDpo_5YOxQxRKs"
CHAT_ID = "@Aibot_signal_bot"

app = Flask(__name__)
logs = []
WIB = pytz.timezone('Asia/Jakarta')

config = {
    "bot_on": True,
    "jeda_otomatis_on": True,
    "jeda_manual_on": False,
    "jam_tidur": (0, 7),
    "jam_siang": (12, 13),
}

HTML = """
<!DOCTYPE html><html><head><title>BOT 5AI V4</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:sans-serif;background:#0f172a;color:#fff;padding:12px}
.card{background:#1e293b;padding:16px;border-radius:16px;margin-bottom:12px}
.btn{display:block;padding:14px;border-radius:12px;text-align:center;font-weight:bold;text-decoration:none;margin-top:8px}
.btn-green{background:#22c55e;color:#fff}.btn-red{background:#ef4444;color:#fff}
.btn-yellow{background:#f59e0b;color:#000}.btn-gray{background:#334155;color:#fff}
.badge{padding:5px 10px;border-radius:20px;font-weight:bold;font-size:12px}
.green{background:#22c55e}.red{background:#ef4444}.yellow{background:#f59e0b;color:#000}
.log{background:#000;padding:10px;border-radius:10px;height:350px;overflow:auto;font-size:11px}
.row{display:flex;gap:8px}.row a{flex:1}small{color:#94a3b8}
</style></head><body>
<div class="card"><h2>🤖 BOT 5AI V4 WEB</h2>Jam: <b>{{jam}} WIB</b><br>
Bot: <span class="badge {{c1}}">{{s1}}</span> | Jeda: <span class="badge {{c2}}">{{s2}}</span><br>
<small>@Aibot_signal_bot | 4/5 AI</small></div>
<div class="card"><h3>🎮 Kontrol</h3>
<div class="row"><a class="btn {{btn_bot}}" href="/toggle/bot">{{txt_bot}}</a>
<a class="btn {{btn_jeda}}" href="/toggle/jeda_manual">{{txt_jeda}}</a></div>
<a class="btn {{btn_auto}}" href="/toggle/auto">{{txt_auto}}</a></div>
<div class="card"><h3>⏰ Status</h3>{{alasan}}</div>
<div class="card"><h3>📜 Live Log</h3><div class="log">{{logs}}</div></div>
</body></html>
"""

def cek_istirahat():
    now=datetime.now(WIB); jam=now.hour
    if not config["bot_on"]: return True, "🔴 BOT OFF MANUAL"
    if config["jeda_manual_on"]: return True, "😴 JEDA MANUAL"
    if config["jeda_otomatis_on"]:
        s,e=config["jam_tidur"]
        if s <= jam < e: return True, f"😴 Jeda {s:02d}-{e:02d} WIB"
        s2,e2=config["jam_siang"]
        if s2 <= jam < e2: return True, f"😴 Jeda siang {s2:02d}-{e2:02d} WIB"
    return False, "🟢 RUNNING 5 AI"

def get_price(sym):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=1d"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        return [c for c in r.json()['chart']['result'][0]['indicators']['quote'][0]['close'] if c]
    except: return []

def analisa(closes):
    if len(closes)<30: return None,"Data kurang"
    ema9=sum(closes[-9:])/9; ema21=sum(closes[-21:])/21
    trend_up=ema9>ema21; trend_down=ema9<ema21
    atr=sum([abs(closes[i]-closes[i-1]) for i in range(-14,0)])/14
    vol=atr>(sum(closes[-20:])/20*0.0005)
    high=max(closes[-20:]); low=min(closes[-20:])
    near=closes[-1]>high*0.998 or closes[-1]<low*1.002
    roc=(closes[-1]-closes[-4])/closes[-4]*100
    mom=abs(roc)>0.15
    gains=[max(0,closes[i]-closes[i-1]) for i in range(-14,0)]
    losses=[max(0,closes[i-1]-closes[i]) for i in range(-14,0)]
    rs=(sum(gains)/14)/(sum(losses)/14 if sum(losses)>0 else 0.001)
    rsi=100-(100/(1+rs))
    total=int(trend_up or trend_down)+int(vol)+int(not near)+int(mom)+int(30<rsi<70)
    if total<4: return None,f"WAIT {total}/5 ROC {roc:.2f}% RSI {rsi:.0f}"
    if trend_up and roc>0.15: return "CALL",f"OK {total}/5 CALL ROC {roc:.2f}% RSI {rsi:.0f}"
    if trend_down and roc<-0.15: return "PUT",f"OK {total}/5 PUT ROC {roc:.2f}% RSI {rsi:.0f}"
    return None,"Arah beda"

def send_tg(t):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":t},timeout=10)
    except: pass

def loop():
    global logs
    last={}
    assets={"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","BTC-USD":"CRYPTO","GC=F":"GOLD"}
    logs.append(f"STARTED {datetime.now(WIB).strftime('%H:%M:%S')}")
    while True:
        rest,reason=cek_istirahat()
        if rest:
            time.sleep(20); continue
        for sym,nama in assets.items():
            closes=get_price(sym)
            if not closes: continue
            arah,det=analisa(closes)
            now=datetime.now(WIB)
            if not arah: continue
            if nama in last and (now-last[nama]).total_seconds()<300: continue
            entry=(now+timedelta(minutes=1)).replace(second=0,microsecond=0)
            msg=f"🚦 {nama} {arah}\n{det}\nENTRY: {entry.strftime('%H:%M:%S')} WIB\n5AI V4"
            send_tg(msg); logs.append(f"[{now.strftime('%H:%M:%S')}] ✅ {nama} {arah}"); last[nama]=now
            if len(logs)>80: logs=logs[-80:]
        time.sleep(12)

@app.route("/")
def home():
    rest,reason=cek_istirahat()
    now=datetime.now(WIB)
    s1="ON" if config["bot_on"] else "OFF"; c1="green" if config["bot_on"] else "red"
    s2="ISTIRAHAT" if rest else "AKTIF"; c2="yellow" if rest else "green"
    return render_template_string(HTML, jam=now.strftime('%H:%M:%S'), s1=s1,c1=c1,s2=s2,c2=c2,
        btn_bot="btn-red" if config["bot_on"] else "btn-green",
        txt_bot="🔴 MATIKAN BOT" if config["bot_on"] else "🟢 HIDUPKAN BOT",
        btn_jeda="btn-red" if config["jeda_manual_on"] else "btn-yellow",
        txt_jeda="▶️ BATAL JEDA" if config["jeda_manual_on"] else "😴 JEDA MANUAL",
        btn_auto="btn-gray" if config["jeda_otomatis_on"] else "btn-yellow",
        txt_auto="⏰ OTOMATIS ON" if config["jeda_otomatis_on"] else "⏰ OTOMATIS OFF",
        alasan=reason, logs="<br>".join(logs[::-1]))

@app.route("/toggle/<n>")
def toggle(n):
    if n=="bot": config["bot_on"]=not config["bot_on"]
    elif n=="jeda_manual": config["jeda_manual_on"]=not config["jeda_manual_on"]
    elif n=="auto": config["jeda_otomatis_on"]=not config["jeda_otomatis_on"]
    return redirect("/")

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=10000)