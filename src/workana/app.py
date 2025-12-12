"""Small Flask dashboard to visualize Workana projects and OpenAI analysis."""
from __future__ import annotations

import json
import os
from typing import List

from flask import Flask, render_template_string, request

from .db import DEFAULT_DB, connect, init_db

APP = Flask(__name__)

INDEX_TEMPLATE = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Workana Radar</title>
  <style>
    body{font-family:system-ui, -apple-system, "Segoe UI", sans-serif; margin:0; padding:0; background:#070c16; color:#e9eefc;}
    .wrap{max-width:1200px; margin:0 auto; padding:20px;}
    .card{background:#0e172a; border:1px solid #1c2944; border-radius:12px; box-shadow:0 12px 40px rgba(0,0,0,.3); overflow:hidden;}
    h1{margin:0 0 8px 0; font-size:22px;}
    .muted{color:rgba(233,238,252,.75); font-size:14px; margin:0;}
    form{display:flex; gap:10px; flex-wrap:wrap; padding:16px; border-bottom:1px solid #1c2944;}
    label{font-size:12px; color:rgba(233,238,252,.6);}
    input, select{background:#0b1424; border:1px solid #1c2944; color:#e9eefc; border-radius:10px; padding:10px 12px; min-width:180px;}
    button, a.btn{border:1px solid #1c2944; background:#163059; color:#e9eefc; padding:10px 14px; border-radius:10px; text-decoration:none; cursor:pointer;}
    button:hover, a.btn:hover{border-color:#62e6c5;}
    table{width:100%; border-collapse:collapse;}
    th, td{padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; vertical-align:top;}
    th{font-size:12px; color:rgba(233,238,252,.65); position:sticky; top:0; background:#0e172a;}
    .pill{display:inline-flex; gap:8px; align-items:center; padding:6px 8px; border-radius:999px; border:1px solid #1c2944; font-size:12px;}
    .pill.ok{border-color:#62e6c5; color:#62e6c5;}
    .pill.maybe{border-color:#ffd166; color:#ffd166;}
    .pill.no{border-color:#ff7b72; color:#ff7b72;}
    .proposal{white-space:pre-wrap; font-size:13px; line-height:1.4;}
    .desc{color:rgba(233,238,252,.8); font-size:13px; line-height:1.45; max-width:580px;}
    .badge{display:inline-flex; gap:6px; align-items:center; padding:6px 8px; background:#0b1424; border:1px solid #1c2944; border-radius:999px; font-size:12px; color:rgba(233,238,252,.75);}
    .grid{display:grid; gap:12px; grid-template-columns:1fr 1fr;}
    .small{font-size:12px; color:rgba(233,238,252,.7);}
  </style>
</head>
<body>
  <div class="wrap">
    <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:10px;">
      <div>
        <h1>Workana Radar</h1>
        <p class="muted">Filtre projetos, veja notas e propostas geradas pela OpenAI.</p>
      </div>
      <div>
        <a class="btn" href="/health">Health</a>
      </div>
    </div>

    <div class="card">
      <form method="get" action="/">
        <div>
          <label>Busca</label><br>
          <input type="text" name="q" value="{{ q }}" placeholder="ex: django, tradução" />
        </div>
        <div>
          <label>Score mínimo</label><br>
          <input type="number" name="min_score" min="0" max="10" value="{{ min_score }}" />
        </div>
        <div>
          <label>Status</label><br>
          <select name="status">
            {% for opt in ['any','pending','complete','error'] %}
              <option value="{{opt}}" {% if status==opt %}selected{% endif %}>{{opt}}</option>
            {% endfor %}
          </select>
        </div>
        <div>
          <label>Limite</label><br>
          <select name="limit">
            {% for n in [50,100,200,400] %}
              <option value="{{n}}" {% if limit==n %}selected{% endif %}>{{n}}</option>
            {% endfor %}
          </select>
        </div>
        <div style="align-self:flex-end;">
          <button type="submit">Filtrar</button>
          <a class="btn" href="/">Limpar</a>
        </div>
      </form>

      <div style="padding:12px; display:flex; gap:10px; flex-wrap:wrap;">
        <span class="badge">Total: <strong>{{ total }}</strong></span>
        <span class="badge">Mostrando: <strong>{{ shown }}</strong></span>
        <span class="badge">Score ≥ {{ min_score }}</span>
        <span class="badge">Status: {{ status }}</span>
      </div>

      <div style="overflow:auto; max-height:70vh;">
        <table>
          <thead>
            <tr>
              <th style="width:70px;">Score</th>
              <th>Título</th>
              <th style="width:140px;">Budget</th>
              <th style="width:140px;">Publicado</th>
              <th style="width:120px;">País</th>
              <th style="width:200px;">Skills</th>
              <th style="width:240px;">Escopo & Valor</th>
              <th>Proposta</th>
            </tr>
          </thead>
          <tbody>
            {% for p in projetos %}
              <tr>
                <td><span class="pill ok">{{ p['score'] or 0 }}</span></td>
                <td>
                  <div><strong>{{ p['titulo'] }}</strong></div>
                  <div class="small">{{ p['slug'] }}</div>
                  <div class="desc">{{ p['descricao'][:240] }}...</div>
                  <div class="small"><a href="{{ p['url'] }}" target="_blank" rel="noopener">Ver no Workana</a></div>
                </td>
                <td>{{ p['budget'] }}</td>
                <td>{{ p['postedDate'] }}</td>
                <td>{{ p['country'] }}</td>
                <td class="small">{{ p['skills'] }}</td>
                <td>
                  <div class="pill {{ p['scope_class'] }}">Escopo: {{ p['scope_fit'] or 'pendente' }}</div>
                  <div class="small">Valor: {{ p['worthiness'] or '-' }}/5</div>
                  <div class="small">Motivo: {{ p['worthiness_reason'] }}</div>
                  <div class="small">Modelo: {{ p['analysis_model'] or 'n/a' }}</div>
                </td>
                <td class="proposal">{{ p['proposal'] or 'Sem proposta ainda.' }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</body>
</html>
"""


@APP.get("/health")
def health():
    try:
        conn = connect()
        total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE analysis_status='pending'"
        ).fetchone()[0]
        conn.close()
        return {"status": "ok", "db": DEFAULT_DB, "total": total, "pending": pending}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error", "error": str(exc)}, 500


@APP.get("/")
def index():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "any").strip()
    min_score = int(request.args.get("min_score") or 0)
    limit = max(10, min(int(request.args.get("limit") or 200), 400))

    conn = connect()
    init_db()
    total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

    sql = """
    SELECT * FROM projects
    WHERE COALESCE(score, 0) >= ?
    """
    params: List = [min_score]

    if q:
        sql += " AND (lower(titulo) LIKE ? OR lower(descricao) LIKE ? OR lower(skills) LIKE ?)"
        like = f"%{q.lower()}%"
        params.extend([like, like, like])

    if status != "any":
        sql += " AND analysis_status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    projetos = []
    for r in rows:
        scope = (r["scope_fit"] or "").lower()
        cls = "ok" if scope.startswith("yes") else "maybe" if scope.startswith("maybe") else "no"
        item = dict(r)
        item["scope_class"] = cls
        projetos.append(item)

    return render_template_string(
        INDEX_TEMPLATE,
        projetos=projetos,
        total=total,
        shown=len(projetos),
        q=q,
        min_score=min_score,
        status=status,
        limit=limit,
    )


if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=True)
