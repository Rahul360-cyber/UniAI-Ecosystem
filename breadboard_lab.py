"""
Interactive IoT breadboard lab (drop-in replacement for render_breadboard_lab).

- Python: real netlist analysis (which column each leg is in -> actual current path)
- Browser JS: 60 fps animated breadboard, LED glow, live node voltages, oscilloscope

Usage in interactive_labs.py:
    from breadboard_lab import render_breadboard_lab
"""

import json

import streamlit as st
import streamlit.components.v1 as components

NCOLS = 30
BOARDS = {
    "Arduino Uno (5V)": {"vcc": 5.0, "rpin": 25.0, "limit_ma": 20.0,
                         "pins": ["D13", "D12", "D8", "D7"]},
    "ESP32 (3.3V)": {"vcc": 3.3, "rpin": 30.0, "limit_ma": 12.0,
                     "pins": ["GPIO2", "GPIO4", "GPIO16", "GPIO17"]},
}
LEDS = {"Red": (1.8, "#ef4444"), "Yellow": (2.0, "#facc15"), "Green": (2.1, "#22c55e"),
        "Blue": (3.0, "#3b82f6"), "White": (3.0, "#f8fafc")}
RESISTORS = [10, 100, 150, 220, 330, 470, 1000, 2200, 10000]
MODES = ["Static HIGH", "Static LOW", "Blink", "PWM dimming", "Fade (breathing)"]
BAND_COLORS = ["#111827", "#7c3f00", "#ef4444", "#f97316", "#facc15",
               "#22c55e", "#3b82f6", "#a855f7", "#9ca3af", "#f8fafc"]
OUTCOMES = {
    "on": "LED lights normally",
    "dim": "LED is dim / barely lit",
    "off": "LED stays off",
    "burn": "LED burns out",
    "short": "Short circuit (board at risk)",
}

DEFAULT = {
    "bb_board": "Arduino Uno (5V)", "bb_pin": "D13", "bb_pin_col": 5, "bb_gnd_col": 18,
    "bb_use_r": True, "bb_r_a": 5, "bb_r_b": 12, "bb_r_val": 220,
    "bb_led_a": 12, "bb_led_c": 18, "bb_led_color": "Red",
    "bb_mode": "Blink", "bb_period": 1.0, "bb_duty": 50,
}
PRESETS = {
    "✅ Working circuit": {},
    "💥 No resistor": {"bb_use_r": False, "bb_led_a": 5, "bb_led_c": 18},
    "🔄 Reversed LED": {"bb_led_a": 18, "bb_led_c": 12},
    "🔌 Broken ground wire": {"bb_gnd_col": 22},
    "⚡ Pin shorted to GND": {"bb_gnd_col": 5},
    "🔵 Blue LED on 3.3 V": {"bb_board": "ESP32 (3.3V)", "bb_pin": "GPIO2", "bb_led_color": "Blue"},
    "🧩 Resistor not in series": {"bb_r_a": 25, "bb_r_b": 27, "bb_led_a": 5, "bb_led_c": 18},
}


# ----------------------------------------------------------------------
# Circuit analysis (real connectivity, not checkboxes)
# ----------------------------------------------------------------------
def _find_paths(elems, start, goal):
    paths = []

    def dfs(node, used, path, seen):
        if node == goal:
            paths.append(list(path))
            return
        for k, e in enumerate(elems):
            if k in used:
                continue
            for fwd, (u, v) in ((True, (e["a"], e["b"])), (False, (e["b"], e["a"]))):
                if u == node and v not in seen:
                    dfs(v, used | {k}, path + [(k, fwd)], seen | {v})

    dfs(start, frozenset(), [], {start})
    return paths


def analyze(c: dict) -> dict:
    b = BOARDS[c["board"]]
    vcc, rpin = b["vcc"], b["rpin"]
    vf = LEDS[c["led_color"]][0]
    out = {"i_ma": 0.0, "vr": 0.0, "vled": 0.0, "node_v": {c["pin_col"]: vcc, c["gnd_col"]: 0.0},
           "outcome": "off", "level": "error", "headline": "", "detail": "",
           "notes": [], "maths": "", "lit": False, "burnt": False, "short": False}

    elems = []
    if c["use_r"]:
        if c["r_a"] == c["r_b"]:
            out["notes"].append("Both resistor legs are in the same column, so it is bypassed.")
        else:
            elems.append({"t": "R", "a": c["r_a"], "b": c["r_b"], "ohms": c["r_val"]})
    if c["led_a"] == c["led_c"]:
        out["notes"].append("Both LED legs are in the same column, so the LED is shorted out.")
    else:
        elems.append({"t": "LED", "a": c["led_a"], "b": c["led_c"]})

    if c["pin_col"] == c["gnd_col"]:
        i = vcc / rpin * 1000
        out.update(outcome="short", short=True, i_ma=i, level="error",
                   headline="Short circuit: the output pin is wired straight to GND",
                   detail=f"Only the pin's own ~{rpin:.0f} Ω output resistance limits the current "
                          f"(≈{i:.0f} mA when HIGH). This can permanently damage the microcontroller.")
        return out

    paths = _find_paths(elems, c["pin_col"], c["gnd_col"])
    if not paths:
        out.update(outcome="off", level="error",
                   headline="Open circuit: there is no complete path from the pin to GND",
                   detail=f"Column {c['pin_col']} (pin) and column {c['gnd_col']} (GND) are not joined "
                          "by any chain of components. Current needs a closed loop.")
        return out

    with_led = [p for p in paths if any(elems[k]["t"] == "LED" for k, _ in p)]
    path = (with_led or paths)[0]
    if len(paths) > 1:
        out["notes"].append("Two parallel paths exist; the analysis follows the one through the LED.")
    in_path = {elems[k]["t"] for k, _ in path}
    if c["use_r"] and "R" not in in_path and c["r_a"] != c["r_b"]:
        out["notes"].append("The resistor is not in series with the LED, so it is not limiting the current.")

    r_total = sum(elems[k]["ohms"] for k, _ in path if elems[k]["t"] == "R")

    if "LED" not in in_path:
        i = vcc / (r_total + rpin)
        out.update(i_ma=i * 1000, outcome="off", level="warning",
                   headline="The LED is not in the current path",
                   detail="Current flows through the resistor to GND, but never through the LED.")
        return out

    led_fwd = next(f for k, f in path if elems[k]["t"] == "LED")
    if not led_fwd:
        out.update(outcome="off", level="error",
                   headline="LED is reversed",
                   detail="An LED conducts only from anode (+, longer leg) to cathode (−). "
                          "Swap its two legs so the anode faces the pin side.")
        return out

    i = (vcc - vf) / (r_total + rpin)
    if i <= 0:
        out.update(outcome="off", level="warning", headline="Supply is below the LED's forward voltage",
                   detail=f"{vcc:.1f} V cannot overcome the {vf:.1f} V needed to turn this LED on.")
        return out

    i_ma = i * 1000
    v = vcc - i * rpin
    node_v = {c["pin_col"]: v}
    for k, _ in path:
        e = elems[k]
        v -= i * e["ohms"] if e["t"] == "R" else vf
        node_v[e["b"] if e["a"] in node_v else e["a"]] = max(v, 0.0)
    node_v[c["gnd_col"]] = 0.0
    out.update(i_ma=i_ma, vr=i * r_total, vled=vf, node_v=node_v, lit=True)
    out["maths"] = (
        f"I = (Vcc − Vf) / (R + R_pin)\n"
        f"  = ({vcc:.1f} − {vf:.1f}) / ({r_total:.0f} + {rpin:.0f})\n"
        f"  = {i_ma:.1f} mA\n"
        f"V_resistor = I × R = {i * r_total:.2f} V"
    )

    limit = b["limit_ma"]
    if i_ma > 30:
        out.update(outcome="burn", burnt=True, level="error",
                   headline="LED over-current: it will burn out",
                   detail=f"{i_ma:.0f} mA flows, but a standard LED tolerates ~20 mA. "
                          "A series resistor is needed to limit the current.")
    elif i_ma < 4:
        out.update(outcome="dim", level="warning", headline="LED is barely lit",
                   detail=f"Only {i_ma:.1f} mA flows. Use a smaller resistor or an LED with lower forward voltage.")
    else:
        out.update(outcome="on", level="success", headline="Circuit complete: the LED is working",
                   detail=f"{i_ma:.1f} mA flows, a safe level for this LED.")
        if i_ma > limit:
            out.update(level="warning")
            out["notes"].append(f"{i_ma:.0f} mA is above the recommended {limit:.0f} mA per pin for this board.")
    return out


# ----------------------------------------------------------------------
# State helpers
# ----------------------------------------------------------------------
def _apply_preset(name: str) -> None:
    for k, v in {**DEFAULT, **PRESETS[name]}.items():
        if k in ("bb_mode", "bb_period", "bb_duty") and name != "✅ Working circuit":
            continue
        st.session_state[k] = v


def _load_preset() -> None:
    _apply_preset(st.session_state["bb_preset"])


def _lock_prediction(sig: str, outcome: str) -> None:
    pred = st.session_state.get("bb_pred")
    st.session_state["bb_locked_sig"] = sig
    st.session_state.setdefault("bb_pred_log", []).append(
        {"predicted": pred, "actual": OUTCOMES[outcome], "correct": pred == OUTCOMES[outcome]})


def _bands(ohms: int):
    s = str(ohms)
    if len(s) == 2:
        s += "0"
        d1, d2, mult = int(s[0]), int(s[1]), 0
    else:
        d1, d2, mult = int(s[0]), int(s[1]), len(s) - 2
    return [BAND_COLORS[d1], BAND_COLORS[d2], BAND_COLORS[mult]]


# ----------------------------------------------------------------------
# Browser-side renderer
# ----------------------------------------------------------------------
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:system-ui,sans-serif;background:transparent}
.wrap{background:#f8fafc;border:1px solid #cbd5e1;border-radius:14px;padding:10px;color:#0f172a}
svg{width:100%;height:auto;display:block}
.flow{stroke-dasharray:6 8;animation:dash .45s linear infinite}
@keyframes dash{to{stroke-dashoffset:-14}}
.meters{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:8px}
.m{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:6px 8px;text-align:center}
.m b{display:block;font-size:18px;font-variant-numeric:tabular-nums}
.m span{font-size:11px;color:#64748b}
canvas{width:100%;height:150px;display:block;background:#0b1220;border-radius:10px;margin-top:8px}
</style></head><body><div class="wrap">
<svg id="bb" viewBox="0 0 760 290"></svg>
<div class="meters">
<div class="m"><span>GPIO pin</span><b id="mG">-</b></div>
<div class="m"><span>Current</span><b id="mI">-</b></div>
<div class="m"><span>Resistor drop</span><b id="mR">-</b></div>
<div class="m"><span>LED drop</span><b id="mL">-</b></div></div>
<canvas id="scope" width="1400" height="300"></canvas></div>
<script>
const C = __CFG__;
const NS="http://www.w3.org/2000/svg", svg=document.getElementById('bb');
const X0=75, DX=21, ROW=[150,168,186,204,222];
const cx=c=>X0+(c-1)*DX;
function el(tag,at,par){const e=document.createElementNS(NS,tag);for(const k in at)e.setAttribute(k,at[k]);(par||svg).appendChild(e);return e;}
function txt(s,x,y,at){const t=el('text',Object.assign({x:x,y:y,'text-anchor':'middle'},at||{}));t.textContent=s;return t;}

const defs=el('defs',{});
const rg=el('radialGradient',{id:'glow'},defs);
el('stop',{offset:'0%','stop-color':C.led_hex,'stop-opacity':'0.95'},rg);
el('stop',{offset:'100%','stop-color':C.led_hex,'stop-opacity':'0'},rg);

// microcontroller
el('rect',{x:30,y:6,width:700,height:62,rx:10,fill:C.board.startsWith('Arduino')?'#0f766e':'#1f2937'});
txt(C.board,380,30,{fill:'#fff','font-size':15,'font-weight':700});
txt('virtual microcontroller',380,50,{fill:'#cbd5e1','font-size':11});
const pinX=150, gndX=600;
el('circle',{cx:pinX,cy:68,r:5,fill:'#fbbf24'}); txt(C.pin_label,pinX,60,{fill:'#fff','font-size':11,'font-weight':700});
el('circle',{cx:gndX,cy:68,r:5,fill:'#94a3b8'}); txt('GND',gndX,60,{fill:'#fff','font-size':11,'font-weight':700});

// breadboard + net highlight
el('rect',{x:45,y:108,width:690,height:150,rx:10,fill:'#e2e8f0',stroke:'#94a3b8'});
for(let c=1;c<=C.ncols;c++){
  if(C.node_v[c]!==undefined){
    const col=(c==C.pin_col)?'#f97316':(c==C.gnd_col)?'#3b82f6':'#10b981';
    el('rect',{x:cx(c)-9,y:136,width:18,height:100,rx:4,fill:col,opacity:0.17});
  }
  txt(c,cx(c),125,{'font-size':8,fill:'#64748b'});
  for(let r=0;r<5;r++) el('circle',{cx:cx(c),cy:ROW[r],r:3.2,fill:'#64748b'});
}
['a','b','c','d','e'].forEach((l,r)=>txt(l,56,ROW[r]+3,{'font-size':8,fill:'#64748b'}));
txt('columns are connected vertically (rows a–e)',390,252,{'font-size':10,fill:'#64748b'});

const flows=[];
function wire(x1,y1,x2,y2,color){
  const d=`M${x1} ${y1} C${x1} ${y1+45}, ${x2} ${y2-55}, ${x2} ${y2}`;
  el('path',{d,fill:'none',stroke:color,'stroke-width':4,'stroke-linecap':'round'});
  flows.push(el('path',{d,fill:'none',stroke:'#fef08a','stroke-width':2,'stroke-linecap':'round',style:'display:none',class:'flow'}));
}
wire(pinX,68,cx(C.pin_col),ROW[0],'#f97316');
wire(gndX,68,cx(C.gnd_col),ROW[4],'#1d4ed8');

// resistor (row b)
if(C.r){
  const xa=cx(C.r.a), xb=cx(C.r.b), y=ROW[1], mid=(xa+xb)/2;
  el('line',{x1:xa,y1:y,x2:xb,y2:y,stroke:'#94a3b8','stroke-width':3,'stroke-linecap':'round'});
  flows.push(el('line',{x1:xa,y1:y,x2:xb,y2:y,stroke:'#fef08a','stroke-width':2,style:'display:none',class:'flow'}));
  const w=Math.min(46,Math.max(18,Math.abs(xb-xa)-8));
  el('rect',{x:mid-w/2,y:y-8,width:w,height:16,rx:6,fill:'#e7cfa0',stroke:'#a16207'});
  C.r.bands.forEach((b,i)=>el('rect',{x:mid-w/2+5+i*(w-14)/3,y:y-8,width:3.5,height:16,fill:b}));
  txt(C.r.ohms>=1000?(C.r.ohms/1000)+'kΩ':C.r.ohms+'Ω',mid,y-13,{'font-size':9,fill:'#334155','font-weight':700});
}
// LED (row d)
const xa=cx(C.led.a), xc=cx(C.led.c), yl=ROW[3], xm=(xa+xc)/2;
el('line',{x1:xa,y1:yl,x2:xc,y2:yl,stroke:'#94a3b8','stroke-width':3,'stroke-linecap':'round'});
flows.push(el('line',{x1:xa,y1:yl,x2:xc,y2:yl,stroke:'#fef08a','stroke-width':2,style:'display:none',class:'flow'}));
const glow=el('circle',{cx:xm,cy:yl,r:40,fill:'url(#glow)',opacity:0});
const body=el('circle',{cx:xm,cy:yl,r:13,fill:C.led_hex,stroke:'#475569','stroke-width':1.5,opacity:0.3});
txt('+',xa,yl+16,{'font-size':11,fill:'#b91c1c','font-weight':700});
txt('−',xc,yl+16,{'font-size':11,fill:'#1d4ed8','font-weight':700});
const dead=txt('💥',xm,yl+5,{'font-size':18}); dead.style.display='none';
const banner=txt('⚠ SHORT CIRCUIT',390,100,{'font-size':16,fill:'#dc2626','font-weight':800}); banner.style.display=C.short?'':'none';

// node voltage badges
const badges={};
Object.keys(C.node_v).forEach(c=>{badges[c]=txt('',cx(+c),236,{'font-size':8.5,fill:'#065f46','font-weight':700});});

// firmware model
function level(t){
  const m=C.mode;
  if(m==='Static HIGH') return 1;
  if(m==='Static LOW') return 0;
  if(m==='Blink') return (t%C.period)<C.period/2?1:0;
  if(m==='PWM dimming') return C.duty/100;
  return (1+Math.sin(2*Math.PI*t/C.period-Math.PI/2))/2;
}
const t0=performance.now(); let isDead=false, hist=[], lastMeter=0;
const vp=(C.node_v[C.pin_col]!==undefined)?C.node_v[C.pin_col]:C.vcc;

function drawScope(t){
  const cv=document.getElementById('scope'),g=cv.getContext('2d'),W=cv.width,H=cv.height;
  g.clearRect(0,0,W,H); g.strokeStyle='#1e293b'; g.lineWidth=1;
  for(let k=1;k<10;k++){g.beginPath();g.moveTo(W*k/10,0);g.lineTo(W*k/10,H);g.stroke();}
  g.beginPath();g.moveTo(0,H/2);g.lineTo(W,H/2);g.stroke();
  const vmax=C.vcc*1.1, imax=Math.max(25,C.i_ma*1.15);
  const yV=v=>H*0.46-(v/vmax)*H*0.40, yI=i=>H*0.96-(Math.min(i,imax)/imax)*H*0.40;
  let pv=[],pi=[];
  if(C.mode==='PWM dimming'){
    const d=C.duty/100;
    for(let c=0;c<3;c++){const x0=W*c/3,x1=x0+W*d/3,x2=W*(c+1)/3;
      pv.push([x0,yV(vp)],[x1,yV(vp)],[x1,yV(0)],[x2,yV(0)]);
      pi.push([x0,yI(C.i_ma)],[x1,yI(C.i_ma)],[x1,yI(0)],[x2,yI(0)]);}
  } else {
    hist.forEach(h=>{const x=(h.t-(t-6))/6*W;pv.push([x,yV(h.v)]);pi.push([x,yI(h.i)]);});
  }
  const trace=(pts,col)=>{g.strokeStyle=col;g.lineWidth=3;g.beginPath();pts.forEach((p,k)=>k?g.lineTo(p[0],p[1]):g.moveTo(p[0],p[1]));g.stroke();};
  trace(pv,'#facc15'); trace(pi,'#22d3ee');
  g.font='22px system-ui'; g.fillStyle='#facc15'; g.fillText('GPIO voltage (V)',10,26);
  g.fillStyle='#22d3ee'; g.fillText('LED current (mA)',10,H/2+28);
  g.fillStyle='#94a3b8'; g.textAlign='right';
  g.fillText(C.mode==='PWM dimming'?'zoomed: 3 PWM cycles (~1 kHz)':(C.mode.startsWith('Fade')?'last 6 s (average)':'last 6 s'),W-10,26); g.textAlign='left';
}

function frame(now){
  const t=(now-t0)/1000, L=level(t);
  if(C.burnt && L>0 && t>1.2) isDead=true;
  const i=isDead?0:C.i_ma*L;
  const bright=(C.lit&&!isDead)?Math.pow(Math.min(1,C.i_ma/20),0.6)*L:0;
  glow.setAttribute('opacity',bright.toFixed(2));
  body.setAttribute('opacity',(0.28+0.72*bright).toFixed(2));
  dead.style.display=isDead?'':'none';
  const active=(i>0.05)&&(C.lit||C.short||C.i_ma>0);
  flows.forEach(f=>f.style.display=active?'':'none');
  hist.push({t:t,v:vp*(C.short?L:L),i:i}); while(hist.length&&hist[0].t<t-7)hist.shift();
  if(now-lastMeter>100){
    lastMeter=now;
    document.getElementById('mG').textContent=(vp*L).toFixed(2)+' V';
    document.getElementById('mI').textContent=i.toFixed(1)+' mA';
    document.getElementById('mR').textContent=(isDead?0:C.vr*L).toFixed(2)+' V';
    document.getElementById('mL').textContent=(isDead||!C.lit?0:C.vled*(L>0?1:0)).toFixed(2)+' V';
    Object.keys(badges).forEach(c=>{badges[c].textContent=(C.node_v[c]*L).toFixed(1)+'V';});
  }
  drawScope(t); requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
</script></body></html>"""


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
def _col_input(label: str, key: str) -> None:
    st.number_input(label, min_value=1, max_value=NCOLS, step=1, key=key)


def render_breadboard_lab() -> None:
    st.markdown("### 🔌 Interactive IoT Breadboard")
    st.caption(
        "Wire a virtual circuit by choosing the breadboard column for each leg. The simulator "
        "traces the real current path, so wiring mistakes cause the same failures as real hardware."
    )

    if "bb_init" not in st.session_state:
        _apply_preset("✅ Working circuit")
        st.session_state["bb_init"] = True

    left, right = st.columns([1, 1.7])

    with left:
        p1, p2 = st.columns([3, 1])
        p1.selectbox("Load an example", list(PRESETS), key="bb_preset", label_visibility="collapsed")
        p2.button("Load", on_click=_load_preset, use_container_width=True)

        st.markdown("**Microcontroller**")
        board = st.selectbox("Board", list(BOARDS), key="bb_board")
        pins = BOARDS[board]["pins"]
        if st.session_state.get("bb_pin") not in pins:
            st.session_state["bb_pin"] = pins[0]
        st.selectbox("Output pin", pins, key="bb_pin")
        c1, c2 = st.columns(2)
        with c1:
            _col_input("Pin wire → column", "bb_pin_col")
        with c2:
            _col_input("GND wire → column", "bb_gnd_col")

        st.markdown("**Resistor**")
        st.checkbox("Include a resistor", key="bb_use_r")
        if st.session_state["bb_use_r"]:
            r1, r2, r3 = st.columns(3)
            with r1:
                _col_input("Leg A col", "bb_r_a")
            with r2:
                _col_input("Leg B col", "bb_r_b")
            with r3:
                st.selectbox("Value", RESISTORS, key="bb_r_val", format_func=lambda x: f"{x} Ω")

        st.markdown("**LED**")
        l1, l2, l3 = st.columns(3)
        with l1:
            _col_input("Anode (+) col", "bb_led_a")
        with l2:
            _col_input("Cathode (−) col", "bb_led_c")
        with l3:
            st.selectbox("Colour", list(LEDS), key="bb_led_color")

        st.markdown("**Firmware**")
        st.selectbox("Program running on the pin", MODES, key="bb_mode")
        mode = st.session_state["bb_mode"]
        if mode in ("Blink", "Fade (breathing)"):
            st.slider("Period (s)", 0.2, 4.0, key="bb_period", step=0.1)
        if mode == "PWM dimming":
            st.slider("Duty cycle (%)", 0, 100, key="bb_duty")
        st.toggle("🎯 Predict first", key="bb_predict_mode",
                  help="Predict the outcome before powering on. Wrong guesses are logged as misconceptions.")

    S = st.session_state
    cfg = {
        "board": S["bb_board"], "pin_col": int(S["bb_pin_col"]), "gnd_col": int(S["bb_gnd_col"]),
        "use_r": bool(S["bb_use_r"]), "r_a": int(S["bb_r_a"]), "r_b": int(S["bb_r_b"]),
        "r_val": int(S["bb_r_val"]), "led_a": int(S["bb_led_a"]), "led_c": int(S["bb_led_c"]),
        "led_color": S["bb_led_color"],
    }
    res = analyze(cfg)
    sig = json.dumps(cfg, sort_keys=True)
    predicting = S.get("bb_predict_mode", False)
    revealed = (not predicting) or S.get("bb_locked_sig") == sig

    with right:
        if not revealed:
            st.info("🎯 **Predict first.** Look at the wiring, then predict what happens when the "
                    "pin is driven HIGH. The board powers on after you lock in your answer.")
            st.radio("What will happen?", list(OUTCOMES.values()), key="bb_pred", index=None)
            st.button("🔒 Lock prediction & power on", type="primary",
                      disabled=S.get("bb_pred") is None,
                      on_click=_lock_prediction, args=(sig, res["outcome"]))
            return

        b = BOARDS[cfg["board"]]
        payload = {
            "board": cfg["board"], "vcc": b["vcc"], "ncols": NCOLS, "pin_label": S["bb_pin"],
            "pin_col": cfg["pin_col"], "gnd_col": cfg["gnd_col"],
            "r": ({"a": cfg["r_a"], "b": cfg["r_b"], "ohms": cfg["r_val"], "bands": _bands(cfg["r_val"])}
                  if cfg["use_r"] else None),
            "led": {"a": cfg["led_a"], "c": cfg["led_c"]}, "led_hex": LEDS[cfg["led_color"]][1],
            "mode": S["bb_mode"], "period": float(S["bb_period"]), "duty": int(S["bb_duty"]),
            "i_ma": res["i_ma"], "vr": res["vr"], "vled": res["vled"], "node_v": res["node_v"],
            "lit": res["lit"], "burnt": res["burnt"], "short": res["short"],
        }
        components.html(HTML.replace("__CFG__", json.dumps(payload)), height=640, scrolling=False)

        if predicting and S.get("bb_pred_log"):
            last = S["bb_pred_log"][-1]
            if last["correct"]:
                st.success(f"✅ Correct! You predicted: {last['predicted']}")
            else:
                st.error(f"❌ You predicted **{last['predicted']}**, but the result is **{last['actual']}**.")
            log = S["bb_pred_log"]
            st.caption(f"Predictions correct: {sum(x['correct'] for x in log)}/{len(log)}")

        {"success": st.success, "warning": st.warning, "error": st.error}[res["level"]](
            f"**{res['headline']}**  \n{res['detail']}")
        for note in res["notes"]:
            st.caption(f"ℹ️ {note}")
        if res["maths"]:
            with st.expander("📐 Show the maths (Ohm's law)"):
                st.code(res["maths"], language="text")
        st.caption("Simplified educational model: constant LED forward voltage, ideal wires, "
                   "no breadboard contact resistance or component tolerance.")