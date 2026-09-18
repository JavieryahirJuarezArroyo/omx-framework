"""Agente reactivo estilo LangGraph (sin dependencia externa).
Grafo: parse -> validate -> execute -> observe -> verify.
- parse: intenta LLM (OPENAI_API_KEY) y si no hay, reglas locales
  que YA entienden ordenes vagas y relativas ("gira un poco").
- execute: mueve por control directo y luego lee estado real.
- verify/observe: compara pedido vs real (reactivo). Si un joint
  no se movio (como tu joint4/ID14 atorado) lo reporta en vez de
  decir "ok".

Casos (cualquiera deberia funcionar):
  "estado", "home", "init", "abre/cierra gripper",
  "mueve j1 a 0.5", "joints [..5..]",
  "gira un poco / gira a la derecha / rota mucho",
  "sube / baja un poco", "secuencia: home, abre, cierra"
"""
import os
import re
from dataclasses import dataclass, field
from . import tools

HOME = [0.0, -1.57, 1.57, 1.57, 0.0]
INIT = [0.0, 0.0, 0.0, 0.0, 0.0]
TOL = 0.15  # tolerancia para verificar que si se movio


@dataclass
class State:
    text: str
    plan: list = field(default_factory=list)   # [(tool, args)]
    results: list = field(default_factory=list)
    before: list = field(default_factory=list)
    reply: str = ''


# ---------- LLM opcional: OpenAI y/o Gemini (REST, sin dependencias) ----------
SYS_PROMPT = ('Eres parser de robot OMX-F de 5 joints. '
              'Responde SOLO JSON: {"plan":[{"tool":"move_joints","args":{"joints":[j1..j5]}},'
              '{"tool":"gripper","args":{"open":0..1}},{"tool":"home","args":{}},'
              '{"tool":"init","args":{}},{"tool":"get_state","args":{}}]}. '
              '"gira un poco"=j1+0.3 desde actual. "mucho"=0.8. '
              'Responde solo el JSON.')


def _plan_from_json(txt):
    import json
    txt = txt.strip()
    txt = txt[txt.find('{'):txt.rfind('}') + 1]
    plan = json.loads(txt).get('plan', [])
    return [(p.get('tool', 'help'), p.get('args', {})) for p in plan] or None


def openai_parse(text, cur):
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        return None
    try:
        from openai import OpenAI
        c = OpenAI(timeout=20)
        r = c.chat.completions.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[{'role': 'system', 'content': SYS_PROMPT + f' Estado actual arm={cur}.'},
                      {'role': 'user', 'content': text}],
            temperature=0, max_tokens=300)
        return _plan_from_json(r.choices[0].message.content)
    except Exception:
        return None


def gemini_parse(text, cur):
    """Gemini vía REST directo (sin pip). Key de aistudio.google.com."""
    import json
    import urllib.request
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        return None
    try:
        model = os.environ.get('GEMINI_MODEL', 'gemini-flash-latest')
        url = (f'https://generativelanguage.googleapis.com/v1beta/models/{model}'
               f':generateContent?key={key}')
        body = json.dumps({
            'system_instruction': {'parts': [{'text': SYS_PROMPT + f' Estado actual arm={cur}.'}]},
            'contents': [{'parts': [{'text': text}]}],
            'generationConfig': {'temperature': 0, 'maxOutputTokens': 300},
        }).encode()
        req = urllib.request.Request(url, data=body, method='POST',
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=25) as f:
            resp = json.loads(f.read().decode())
        txt = resp['candidates'][0]['content']['parts'][0]['text']
        return _plan_from_json(txt)
    except Exception:
        return None


def llm_parse(text, cur):
    """Cadena: OpenAI -> Gemini -> None (reglas)."""
    return openai_parse(text, cur) or gemini_parse(text, cur)


# ---------- Reglas locales (funcionan offline) ----------
TYPO_MAP = {'akza': 'alza', 'muebelo': 'muevelo', 'muebelo ': 'muevelo ',
            'izkierda': 'izquierda', 'derexha': 'derecha', 'gipper': 'gripper',
            'grippe': 'gripper', 'pinsa': 'pinza', 'pinsas': 'pinza'}


def normalize(t):
    for k, v in TYPO_MAP.items():
        t = t.replace(k, v)
    return t


MOTION_VERBS = ('mueve', 'mover', 'muevelo', 'muévelo', 'gira', 'rota', 'girar',
                'rotar', 'sube', 'baja', 'alza', 'levanta', 'vuelta', 'moverlo')
DIRS = ('izquierda', 'izq', 'derecha', 'der', 'arriba', 'abajo', 'adelante',
        'atras', 'atrás', 'hacia')


def clamp_joints(q):
    """Recorta a límites seguros y reporta qué se ajustó."""
    out, noted = [], []
    for n, v in zip(tools.NAMES, q):
        lo, hi = tools.LIMITS[n]
        c = min(hi, max(lo, v))
        if abs(c - v) > 1e-9:
            noted.append(f'{n} ajustado a {round(c, 3)} (límite)')
        out.append(c)
    return out, noted


def relative_move(t, cur):
    """Ordenes vagas/relativas -> objetivo. Funciona con verbo o dirección sola."""
    q = list(cur)
    has_verb = any(w in t for w in MOTION_VERBS)
    has_dir = any(w in t for w in DIRS)
    if not (has_verb or has_dir):
        return None
    poco = 0.3 if ('poco' in t or 'poquito' in t or 'poquit' in t) else 0.8 if 'mucho' in t else 0.3
    moved = False
    if any(w in t for w in ('izquierda', 'izq')) or 'izquierda' in t:
        q[0] = cur[0] - poco
        moved = True
    elif 'derecha' in t or re.search(r'\bder\b', t):
        q[0] = cur[0] + poco
        moved = True
    if any(w in t for w in ('arriba',)) or ('hacia arriba' in t):
        q[1] = cur[1] - poco * 0.5
        q[2] = cur[2] + poco * 0.5
        moved = True
    elif 'abajo' in t or 'hacia abajo' in t:
        q[1] = cur[1] + poco * 0.5
        q[2] = cur[2] - poco * 0.5
        moved = True
    if 'adelante' in t:
        q[2] = cur[2] + poco * 0.5
        moved = True
    elif 'atras' in t or 'atrás' in t:
        q[2] = cur[2] - poco * 0.5
        moved = True
    if any(w in t for w in ('alza', 'levanta', 'sube')) and not moved:
        q[1] = cur[1] - poco * 0.5
        q[2] = cur[2] + poco * 0.5
        moved = True
    if any(w in t for w in ('gira', 'rota', 'girar', 'rotar', 'vuelta')) and not moved:
        q[0] = cur[0] + poco
        moved = True
    if has_verb and not moved:
        # verbo de movimiento sin dirección clara: giro leve por defecto
        q[0] = cur[0] + poco
        moved = True
    return q if moved else None


def _log_llm(text, plan):
    try:
        with open(os.path.join(os.path.dirname(__file__), 'llm.log'), 'a') as f:
            f.write(f'IN: {text[:120]}\nOUT: {str(plan)[:300]}\n---\n')
    except Exception:
        pass


def _llm_sane(plan, text, cur):
    """Antialucinación: si el usuario no dio números absolutos y el plan
    del LLM salta >1.0 rad en algún joint, se descarta (usa reglas)."""
    if not plan:
        return None
    if re.search(r'\[([^\]]+)\]', text) or re.search(r'j(?:oint)?\s*[1-5]\s*(?:a|=|:)?\s*-?\d', text):
        return plan  # el usuario sí pidió valores: respeta al LLM
    for tool, args in plan:
        if tool == 'move_joints':
            dq = [abs(a - b) for a, b in zip(args.get('joints', cur), cur)]
            if max(dq) > 1.0:
                return None
    return plan


def parse(state: State) -> State:
    t = normalize(state.text.lower().strip())
    try:
        state.before = tools.get_state()['arm']
    except Exception:
        state.before = list(HOME)
    cur = list(state.before)

    # 1) LLM si hay key (con guardrail + log)
    llm = _llm_sane(llm_parse(state.text, [round(x, 3) for x in cur]),
                     state.text, cur)
    _log_llm(state.text, llm)
    if llm:
        state.plan = llm
        return state

    # 2) secuencia
    if t.startswith('secuencia'):
        rest = t.split(':', 1)[1] if ':' in t else t
        plan = []
        for chunk in re.split(r'[,;]\s*|\s+luego\s+', rest):
            if chunk.strip():
                plan.extend(parse(State(chunk)).plan)
        state.plan = plan or [('help', {})]
        return state

    plan = []
    if 'estado' in t or 'donde esta' in t or 'posicion actual' in t or 'posición actual' in t:
        plan = [('get_state', {})]
    elif t.strip() == 'home' or ' a home' in t or 've a home' in t:
        plan = [('home', {})]
    elif 'init' in t or 'inicial' in t:
        plan = [('init', {})]
    elif ('abre' in t or t.strip() in ('abre', 'abrir')) and ('gripper' in t or 'pinza' in t) or t.strip() in ('abre', 'abrir'):
        plan = [('gripper', {'open': 1.0})]
    elif 'cierr' in t or 'cerrar' in t:
        plan = [('gripper', {'open': 0.0})]
    elif 'torque' in t:
        plan = [('torque', {'on': 'off' not in t and 'apaga' not in t})]
    else:
        m = re.search(r'\[([^\]]+)\]', t)
        if m:
            try:
                q = [float(x) for x in re.split(r'[, ]+', m.group(1).strip()) if x]
                if len(q) == 5:
                    plan = [('move_joints', {'joints': q})]
            except ValueError:
                pass
        if not plan:
            pairs = re.findall(r'j(?:oint)?\s*([1-5])\s*(?:a|=|:)?\s*(-?\d+\.?\d*)', t)
            if pairs:
                q = list(cur)
                for j, v in pairs:
                    q[int(j) - 1] = float(v)
                plan = [('move_joints', {'joints': q})]
        if not plan:
            rel = relative_move(t, cur)
            if rel is not None:
                plan = [('move_joints', {'joints': rel})]
    state.plan = plan or [('help', {})]
    return state


def validate(state: State) -> State:
    notes = []
    for i, (tool, args) in enumerate(state.plan):
        if tool == 'move_joints':
            q, noted = clamp_joints(args['joints'])
            state.plan[i] = (tool, {**args, 'joints': q})
            notes.extend(noted)
    if notes:
        state.reply = ''
        state.results.append(('clamp', {'note': '; '.join(notes)}))
    return state


def execute(state: State) -> State:
    for tool, args in state.plan:
        try:
            if tool == 'get_state':
                state.results.append(('get_state', tools.get_state()))
            elif tool == 'move_joints':
                r = tools.move_joints(args['joints'], args.get('seconds', 4.0))
                # reactivo: lee estado real despues de mover
                try:
                    after = tools.get_state()['arm']
                except Exception:
                    after = None
                state.results.append(('move_joints', {'cmd': args['joints'], 'res': r, 'after': after}))
            elif tool == 'home':
                r = tools.home()
                try:
                    after = tools.get_state()['arm']
                except Exception:
                    after = None
                state.results.append(('home', {'res': r, 'after': after}))
            elif tool == 'init':
                r = tools.init()
                try:
                    after = tools.get_state()['arm']
                except Exception:
                    after = None
                state.results.append(('init', {'res': r, 'after': after}))
            elif tool == 'gripper':
                state.results.append(('gripper', tools.gripper(args.get('open', 1.0))))
            elif tool == 'torque':
                import urllib.request, json
                req = urllib.request.Request(
                    tools.BRIDGE + '/torque',
                    data=json.dumps({'on': args['on']}).encode(), method='POST',
                    headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as f:
                    state.results.append(('torque', json.loads(f.read())))
            elif tool == 'help':
                state.results.append(('help', {}))
            else:
                state.results.append((tool, {'error': f'herramienta desconocida: {tool}'}))
        except Exception as e:
            state.results.append((tool, {'error': str(e)[:300]}))
            break
    return state


def observe(state: State) -> State:
    if state.reply:
        return state
    parts = []
    for tool, r in state.results:
        if tool == 'clamp':
            parts.append('Nota: ' + r.get('note', ''))
        elif tool == 'get_state' and isinstance(r, dict) and 'arm' in r:
            arm = [round(x, 3) for x in r['arm']]
            parts.append(f'Joints: {arm}, gripper: {round(r.get("gripper", 0), 3)}')
        elif tool in ('move_joints', 'home', 'init'):
            cmd = r.get('cmd') if isinstance(r, dict) else None
            after = r.get('after') if isinstance(r, dict) else None
            want = cmd if cmd is not None else (HOME if tool == 'home' else INIT)
            if after is None:
                parts.append(f'{tool} enviado, no pude leer estado final.')
                continue
            diffs = [abs(a - b) for a, b in zip(after, want)]
            mx = max(diffs)
            arm_r = [round(x, 3) for x in after]
            if mx <= TOL:
                parts.append(f'{tool} ok. Ahora: {arm_r}')
            else:
                j = diffs.index(mx) + 1
                parts.append(f'{tool} enviado pero joint{j} no llego (pedido {round(want[j-1],3)}, '
                             f'real {round(after[j-1],3)}). Ahora: {arm_r}. '
                             f'{"OJO: joint4/ID14 tiene historial de overload 0x20 y se queda pegado; revisa mecanica antes de insistir." if j == 4 else "Revisa torque/obstaculo."}')
        elif tool == 'help':
            parts.append('Prueba: "gira un poco", "gira a la derecha", "sube un poco", '
                         '"mueve j1 a 0.5", "home", "abre gripper", "estado"')
        elif isinstance(r, dict) and 'error' in r:
            parts.append(f'{tool} falló: {r["error"]}')
        else:
            parts.append(f'{tool} ok: {r}')
    state.reply = '\n'.join(parts) or 'listo'
    return state


def run(text: str) -> str:
    """Grafo: parse -> validate -> execute -> observe (reactivo)."""
    s = State(text)
    for node in (parse, validate, execute, observe):
        s = node(s)
        if node is validate and s.reply:
            break
    return s.reply
