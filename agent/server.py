"""Chat UI sin dependencias: http.server stdlib + HTML.
Uso:  python3 -m agent.server  (puerto 8501)
LangGraph agent (LLM obligatorio) + bridge HTTP al robot.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from .env_config import load_agent_dotenv

load_agent_dotenv()

from . import context, runner, tools

HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ROS Agent Chat</title>
<style>body{font-family:system-ui;margin:0;background:#111;color:#eee}
#wrap{max-width:720px;margin:0 auto;padding:16px}
#log{border:1px solid #333;border-radius:8px;padding:12px;height:55vh;overflow:auto;background:#181818}
.msg{margin:8px 0;padding:8px 10px;border-radius:8px;white-space:pre-wrap}
.me{background:#0b5fa5}.bot{background:#222}.sys{background:#3a2b00}
#row{display:flex;gap:8px;margin-top:10px}
#inp{flex:1;padding:10px;border-radius:8px;border:1px solid #444;background:#222;color:#eee}
button{padding:10px 14px;border-radius:8px;border:0;background:#0b5fa5;color:#fff;cursor:pointer}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.chips button{background:#333;font-size:13px;padding:6px 10px}
#state{font-size:13px;color:#9fd08a;margin-top:8px}
#mode{font-size:12px;color:#888;margin-top:4px}
#vizbox{display:none;margin-top:12px}
#vizbox h3{margin:0 0 8px;font-size:14px;color:#aaa}
#turtleCanvas{display:block;width:100%;max-width:440px;border:1px solid #333;border-radius:8px;background:#005f99}
#vizhint{font-size:12px;color:#888;margin-top:6px}</style></head>
<body><div id="wrap">
<h2 id="title">ROS Agent · chat</h2>
<div id="vizbox"><h3>Vista turtlesim (posición en vivo)</h3>
<canvas id="turtleCanvas" width="440" height="440"></canvas>
<p id="vizhint">Mapa 11×11 m (como turtlesim). Se actualiza al mover con el agente.</p></div>
<div id="log"></div>
<div class="chips" id="chips">
<button data-t="estado">estado</button>
<button data-t="home">home</button>
<button data-t="init">init</button>
<button data-t="abre gripper">abre gripper</button>
<button data-t="cierra gripper">cierra gripper</button>
<button data-t="secuencia: home, abre, cierra">secuencia demo</button>
</div>
<div id="row"><input id="inp" placeholder='ej: "mueve j1 a 0.5" o "joints [0,-1.57,1.57,1.57,0]"'>
<button onclick="send()">Enviar</button></div>
<div id="state"></div>
<div id="mode"></div>
<script>
const log=document.getElementById('log'), inp=document.getElementById('inp'), st=document.getElementById('state'), md=document.getElementById('mode');
const vizbox=document.getElementById('vizbox'), tcanvas=document.getElementById('turtleCanvas'), tctx=tcanvas.getContext('2d');
let robotId='', vizTimer=null, W=11;
function add(cls,t){const d=document.createElement('div');d.className='msg '+cls;d.textContent=t;log.appendChild(d);log.scrollTop=1e9}
async function send(t){
  const text=t||inp.value.trim(); if(!text)return; inp.value='';
  add('me',text);
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  const j=await r.json(); add('bot',j.reply||JSON.stringify(j)); refresh();
}
function drawTurtle(x,y,theta){
  const cw=tcanvas.width, ch=tcanvas.height, s=cw/W;
  tctx.fillStyle='#005f99'; tctx.fillRect(0,0,cw,ch);
  tctx.strokeStyle='rgba(255,255,255,.15)'; tctx.lineWidth=1;
  for(let i=0;i<=W;i++){tctx.beginPath();tctx.moveTo(i*s,0);tctx.lineTo(i*s,ch);tctx.stroke();tctx.beginPath();tctx.moveTo(0,i*s);tctx.lineTo(cw,i*s);tctx.stroke();}
  const px=x*s, py=ch-y*s, L=14;
  tctx.save(); tctx.translate(px,py); tctx.rotate(-theta);
  tctx.fillStyle='#2ecc71'; tctx.beginPath(); tctx.moveTo(L,0); tctx.lineTo(-L*.6,L*.5); tctx.lineTo(-L*.6,-L*.5); tctx.closePath(); tctx.fill();
  tctx.restore();
  tctx.fillStyle='#eee'; tctx.font='12px system-ui'; tctx.fillText('x='+x.toFixed(2)+' y='+y.toFixed(2)+' θ='+theta.toFixed(2),8,ch-10);
}
function setupChips(id){
  const el=document.getElementById('chips');
  const arm=[['dime la posición de los joints','estado'],['ve a home','home'],['abre la pinza','abre gripper'],['cierra la pinza','cierra gripper'],['secuencia: home, abre pinza, cierra pinza','secuencia demo']];
  const tur=[['¿cuál es tu posición?','estado'],['vuelve al centro (reset)','home'],['avanza un poco en línea recta','avanza'],['gira un poco a la izquierda','gira izq'],['gira un poco a la derecha','gira der']];
  const rows=id==='turtlesim'?tur:arm;
  el.innerHTML=rows.map(r=>'<button data-t="'+r[0]+'">'+r[1]+'</button>').join('');
  el.querySelectorAll('button').forEach(b=>b.onclick=()=>send(b.dataset.t));
}
async function refresh(){
  try{const r=await fetch('/api/state');const j=await r.json();
    const arm=j.arm||j.joints||[]; const g=j.gripper!=null?j.gripper:'—';
    st.textContent='joints: '+JSON.stringify(arm)+' gripper: '+g;
    if(robotId==='turtlesim'&&arm.length>=3) drawTurtle(arm[0],arm[1],arm[2]);
  }catch(e){st.textContent='bridge no disponible (revisa ROS_AGENT_BRIDGE)'}
}
inp.addEventListener('keydown',e=>{if(e.key==='Enter')send()});
fetch('/api/mode').then(r=>r.json()).then(j=>{md.textContent='Modo: '+j.mode+' · LLM: '+(j.provider||'?')+(j.model?' · '+j.model:'');}).catch(()=>{});
fetch('/api/robot').then(r=>r.json()).then(j=>{
  document.getElementById('title').textContent=j.display_name+' · chat';
  md.textContent+=' · '+j.id+' · '+j.bridge;
  robotId=j.id||'';
  setupChips(robotId);
  if(robotId==='turtlesim'){vizbox.style.display='block'; if(vizTimer)clearInterval(vizTimer); vizTimer=setInterval(refresh,400);}
}).catch(()=>{});
add('sys','Agente LLM + bridge HTTP. Escribe en lenguaje natural o usa los botones. OJO: el robot SE MUEVE.');
refresh();
</script></div></body></html>"""


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == '/' or self.path.startswith('/?'):
            b = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif self.path == '/api/state':
            try:
                self._json(tools.get_state())
            except Exception as e:
                self._json({'error': str(e)[:200]}, 503)
        elif self.path == '/api/mode':
            self._json(runner.llm_status())
        elif self.path == '/api/robot':
            try:
                self._json(context.robot_public_info())
            except Exception as e:
                self._json({'error': str(e)[:200]}, 503)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != '/api/chat':
            return self.send_response(404)
        n = int(self.headers.get('Content-Length', 0))
        try:
            text = json.loads(self.rfile.read(n).decode()).get('text', '')
        except Exception:
            return self._json({'reply': 'mensaje inválido'}, 400)
        try:
            reply = runner.run(text)
        except Exception as e:
            reply = f'error agente: {e}'
        self._json({'reply': reply})


def main(port=8501):
    try:
        info = context.robot_public_info()
        bridge = info.get('bridge', '?')
    except Exception:
        bridge = '(config no cargada)'
    print(f'chat UI en http://localhost:{port}  bridge: {bridge}', flush=True)
    _ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()


if __name__ == '__main__':
    main()
