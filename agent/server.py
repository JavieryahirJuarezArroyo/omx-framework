"""Chat UI sin dependencias: http.server stdlib + HTML.
Uso:  python3 -m agent.server  (puerto 8501)
Habla con el bridge en localhost:8000 a través de graph_mini.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# carga .env local (sin dependencias) para OPENAI_API_KEY
try:
    _env = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(_env):
        for line in open(_env):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
except Exception:
    pass

from .graph_mini import run as agent_run
from . import tools

HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OMX Chat</title>
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
#state{font-size:13px;color:#9fd08a;margin-top:8px}</style></head>
<body><div id="wrap">
<h2>OMX-F · chat de tareas</h2>
<div id="log"></div>
<div class="chips">
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
<script>
const log=document.getElementById('log'), inp=document.getElementById('inp'), st=document.getElementById('state');
function add(cls,t){const d=document.createElement('div');d.className='msg '+cls;d.textContent=t;log.appendChild(d);log.scrollTop=1e9}
async function send(t){
  const text=t||inp.value.trim(); if(!text)return; inp.value='';
  add('me',text);
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  const j=await r.json(); add('bot',j.reply||JSON.stringify(j)); refresh();
}
async function refresh(){
  try{const r=await fetch('/api/state');const j=await r.json();
    st.textContent='joints: '+JSON.stringify(j.arm)+' gripper: '+j.gripper;}catch(e){st.textContent='bridge no disponible (¿corre en :8000?)'}
}
document.querySelectorAll('.chips button').forEach(b=>b.onclick=()=>send(b.dataset.t));
inp.addEventListener('keydown',e=>{if(e.key==='Enter')send()});
add('sys','Bridge: localhost:8000 · escribe "estado" para empezar. OJO: el robot SE MUEVE.');
refresh();
</script></div></body></html>"""


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
            reply = agent_run(text)
        except Exception as e:
            reply = f'error agente: {e}'
        self._json({'reply': reply})


def main(port=8501):
    print(f'chat UI en http://localhost:{port}  (bridge en localhost:8000)', flush=True)
    HTTPServer(('0.0.0.0', port), H).serve_forever()


if __name__ == '__main__':
    main()
