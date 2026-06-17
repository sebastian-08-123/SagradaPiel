from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
import sqlite3, hashlib, os, json

app = Flask(__name__)
app.secret_key = "sagradapiel_secret_2024"

DB = "tienda.db"

# ── Helpers ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            es_admin INTEGER DEFAULT 0,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            liga TEXT NOT NULL,
            precio REAL NOT NULL,
            descripcion TEXT,
            imagen TEXT,
            stock INTEGER DEFAULT 10
        );
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            total REAL,
            estado TEXT DEFAULT 'pendiente',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nombre_cliente TEXT,
            email_cliente TEXT,
            direccion TEXT
        );
        CREATE TABLE IF NOT EXISTS pedido_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            precio REAL
        );
        """)
        # Agregar columna es_admin si no existe (migracion segura)
        try:
            db.execute("ALTER TABLE usuarios ADD COLUMN es_admin INTEGER DEFAULT 0")
            db.commit()
        except:
            pass

        # Insertar productos de ejemplo si la tabla está vacía
        cur = db.execute("SELECT COUNT(*) as c FROM productos")
        if cur.fetchone()["c"] == 0:
            productos = [
                ("Real Madrid - Local 24/25",    "La Liga",          89.99, "Camiseta oficial temporada 2024/25 con tecnología Dri-Fit",    "real_madrid.jpeg"),
                ("FC Barcelona - Local 24/25",   "La Liga",          89.99, "Camiseta oficial blaugrana temporada 2024/25",                 "barcelona.jpeg"),
                ("Manchester City - Local 24/25","Premier League",   94.99, "Camiseta oficial azul celeste temporada 2024/25",              "man_city.jpeg"),
                ("Liverpool - Local 24/25",      "Premier League",   94.99, "Camiseta oficial roja con tecnología AeroSwift",               "liverpool.jpeg"),
                ("PSG - Local 24/25",            "Ligue 1",          92.99, "Camiseta oficial parisina con detalles dorados",               "psg.jpeg"),
                ("Bayern Munich - Local 24/25",  "Bundesliga",       91.99, "Camiseta oficial roja temporada 2024/25",                      "bayern.jpeg"),
                ("Juventus - Local 24/25",       "Serie A",          88.99, "Camiseta oficial bianconera temporada 2024/25",                "juventus.jpeg"),
                ("Argentina - Mundial",          "Selecciones",      99.99, "Camiseta albiceleste campeón del mundo Qatar 2022",            "argentina.jpeg"),
                ("Brasil - Copa América",        "Selecciones",      97.99, "Camiseta canarinha Copa América 2024",                        "brasil.jpeg"),
                ("Atlético de Madrid - Local",   "La Liga",          87.99, "Camiseta rojiblanca temporada 2024/25",                       "atletico.jpeg"),
                ("Chelsea - Local 24/25",        "Premier League",   93.99, "Camiseta azul oficial Stamford Bridge",                       "chelsea.jpeg"),
                ("Inter Milan - Local 24/25",    "Serie A",          90.99, "Camiseta nerazzurra temporada 2024/25",                       "inter.jpeg"),
            ]
            db.executemany(
                "INSERT INTO productos (nombre,liga,precio,descripcion,imagen) VALUES (?,?,?,?,?)",
                productos
            )
            db.commit()

        # Crear usuario admin por defecto si no existe
        cur = db.execute("SELECT COUNT(*) as c FROM usuarios WHERE email='sebas123@gmail.com'")
        if cur.fetchone()["c"] == 0:
            db.execute(
                "INSERT INTO usuarios (nombre, email, password, es_admin) VALUES (?, ?, ?, 1)",
                ("Admin", "sebas123@gmail.com", hash_pw("sebastian123"))
            )
            db.commit()

init_db()

# ── Decoradores ───────────────────────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("es_admin"):
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

# ── Leer HTML/CSS desde archivos ──────────────────────────────────────────────
def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# ── Rutas principales ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    with get_db() as db:
        liga_filter = request.args.get("liga", "")
        buscar = request.args.get("q", "")
        query = "SELECT * FROM productos WHERE 1=1"
        params = []
        if liga_filter:
            query += " AND liga=?"
            params.append(liga_filter)
        if buscar:
            query += " AND nombre LIKE ?"
            params.append(f"%{buscar}%")
        productos = db.execute(query, params).fetchall()
        ligas = db.execute("SELECT DISTINCT liga FROM productos ORDER BY liga").fetchall()
    carrito = session.get("carrito", {})
    total_items = sum(v["cantidad"] for v in carrito.values())
    html = read_file("index.html")
    prod_html = ""
    for p in productos:
        prod_html += f"""
        <div class="card-producto" data-id="{p['id']}">
            <div class="card-img-wrap">
                <img src="/imagen/{p['imagen']}" alt="{p['nombre']}" onerror="this.src='/imagen/placeholder.jpeg'">
                <span class="badge-liga">{p['liga']}</span>
            </div>
            <div class="card-info">
                <h3>{p['nombre']}</h3>
                <p class="desc">{p['descripcion']}</p>
                <div class="card-footer">
                    <span class="precio">S/. {p['precio']:.2f}</span>
                    <button class="btn-agregar" onclick="agregarCarrito({p['id']}, '{p['nombre']}', {p['precio']})">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                        Agregar
                    </button>
                </div>
            </div>
        </div>"""
    liga_opts = '<option value="">Todas las ligas</option>'
    for l in ligas:
        sel = 'selected' if l['liga'] == liga_filter else ''
        liga_opts += f'<option value="{l["liga"]}" {sel}>{l["liga"]}</option>'
    usuario = session.get("usuario_nombre", "")
    es_admin = session.get("es_admin", False)
    html = html.replace("{{PRODUCTOS}}", prod_html)
    html = html.replace("{{LIGA_OPTIONS}}", liga_opts)
    html = html.replace("{{TOTAL_ITEMS}}", str(total_items))
    html = html.replace("{{USUARIO}}", usuario)
    html = html.replace("{{BUSCAR}}", buscar)
    html = html.replace("{{ES_ADMIN}}", "true" if es_admin else "false")
    return html

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pw    = request.form.get("password","")
        with get_db() as db:
            u = db.execute("SELECT * FROM usuarios WHERE email=? AND password=?",
                           (email, hash_pw(pw))).fetchone()
        if u:
            session["usuario_id"]     = u["id"]
            session["usuario_nombre"] = u["nombre"]
            session["es_admin"]       = bool(u["es_admin"])
            if u["es_admin"]:
                return redirect(url_for("admin"))
            return redirect(url_for("index"))
        error = "Correo o contraseña incorrectos."
    html = read_file("login.html")
    html = html.replace("{{ERROR}}", f'<p class="error-msg">{error}</p>' if error else "")
    html = html.replace("{{REG_ERROR}}", "")
    html = html.replace("{{REG_OK}}", "")
    return html

@app.route("/registro", methods=["POST"])
def registro():
    nombre = request.form.get("nombre","").strip()
    email  = request.form.get("reg_email","").strip()
    pw     = request.form.get("reg_password","")
    pw2    = request.form.get("reg_password2","")
    reg_error = ""
    reg_ok    = ""
    if not nombre or not email or not pw:
        reg_error = "Completa todos los campos."
    elif pw != pw2:
        reg_error = "Las contraseñas no coinciden."
    else:
        try:
            with get_db() as db:
                db.execute("INSERT INTO usuarios (nombre,email,password) VALUES (?,?,?)",
                           (nombre, email, hash_pw(pw)))
                db.commit()
            reg_ok = "¡Cuenta creada! Ya puedes iniciar sesión."
        except sqlite3.IntegrityError:
            reg_error = "Ese correo ya está registrado."
    html = read_file("login.html")
    html = html.replace("{{ERROR}}", "")
    html = html.replace("{{REG_ERROR}}", f'<p class="error-msg">{reg_error}</p>' if reg_error else "")
    html = html.replace("{{REG_OK}}", f'<p class="success-msg">{reg_ok}</p>' if reg_ok else "")
    return html

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ── Panel Admin ───────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin():
    from datetime import datetime, timedelta
    with get_db() as db:
        productos   = db.execute("SELECT * FROM productos ORDER BY id").fetchall()
        total_productos = len(productos)
        total_pedidos   = db.execute("SELECT COUNT(*) as c FROM pedidos").fetchone()["c"]
        total_usuarios  = db.execute("SELECT COUNT(*) as c FROM usuarios WHERE es_admin=0").fetchone()["c"]
        ingresos_total  = db.execute("SELECT COALESCE(SUM(total),0) as s FROM pedidos").fetchone()["s"]
        precio_prom     = db.execute("SELECT COALESCE(AVG(precio),0) as a FROM productos").fetchone()["a"]

        # Ventas últimos 7 días
        ventas_7 = []
        for i in range(6, -1, -1):
            dia = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            label = (datetime.now() - timedelta(days=i)).strftime("%d/%m")
            total_dia = db.execute(
                "SELECT COALESCE(SUM(total),0) as s FROM pedidos WHERE DATE(fecha)=?", (dia,)
            ).fetchone()["s"]
            ventas_7.append({"label": label, "valor": float(total_dia)})

        # Pedidos últimos 7 días
        pedidos_7 = []
        for i in range(6, -1, -1):
            dia = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            label = (datetime.now() - timedelta(days=i)).strftime("%d/%m")
            cnt = db.execute(
                "SELECT COUNT(*) as c FROM pedidos WHERE DATE(fecha)=?", (dia,)
            ).fetchone()["c"]
            pedidos_7.append({"label": label, "valor": cnt})

        # Clientes nuevos últimos 7 días
        clientes_7 = []
        for i in range(6, -1, -1):
            dia = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            label = (datetime.now() - timedelta(days=i)).strftime("%d/%m")
            cnt = db.execute(
                "SELECT COUNT(*) as c FROM usuarios WHERE DATE(fecha_registro)=? AND es_admin=0", (dia,)
            ).fetchone()["c"]
            clientes_7.append({"label": label, "valor": cnt})

        # Top productos más vendidos
        top_productos = db.execute("""
            SELECT p.nombre, SUM(pi.cantidad) as total_vendido, SUM(pi.cantidad * pi.precio) as ingresos
            FROM pedido_items pi
            JOIN productos p ON p.id = pi.producto_id
            GROUP BY pi.producto_id
            ORDER BY total_vendido DESC
            LIMIT 5
        """).fetchall()

        # Pedidos recientes
        pedidos_recientes = db.execute("""
            SELECT id, nombre_cliente, total, estado, fecha
            FROM pedidos ORDER BY fecha DESC LIMIT 8
        """).fetchall()

        # Ventas por liga
        ventas_liga = db.execute("""
            SELECT p.liga, SUM(pi.cantidad) as unidades
            FROM pedido_items pi
            JOIN productos p ON p.id = pi.producto_id
            GROUP BY p.liga ORDER BY unidades DESC
        """).fetchall()

    import json as _json

    ventas_labels  = _json.dumps([v["label"] for v in ventas_7])
    ventas_vals    = _json.dumps([v["valor"] for v in ventas_7])
    pedidos_labels = _json.dumps([p["label"] for p in pedidos_7])
    pedidos_vals   = _json.dumps([p["valor"] for p in pedidos_7])
    clientes_vals  = _json.dumps([c["valor"] for c in clientes_7])

    liga_labels = _json.dumps([r["liga"] for r in ventas_liga])
    liga_vals   = _json.dumps([r["unidades"] for r in ventas_liga])

    top_rows = ""
    for i, p in enumerate(top_productos):
        top_rows += f"""
        <tr>
            <td style="color:var(--muted);font-weight:700;">#{i+1}</td>
            <td>{p['nombre']}</td>
            <td style="text-align:center;">{int(p['total_vendido'])}</td>
            <td style="color:var(--accent);font-weight:700;">S/. {p['ingresos']:.2f}</td>
        </tr>"""
    if not top_rows:
        top_rows = '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:20px;">Sin ventas aún</td></tr>'

    estado_color = {"pendiente": "#d97706", "enviado": "#3b82f6", "entregado": "#10b981", "cancelado": "#ef4444"}
    ped_rows = ""
    for p in pedidos_recientes:
        color = estado_color.get(p["estado"], "#888")
        fecha_fmt = p["fecha"][:10] if p["fecha"] else "-"
        ped_rows += f"""
        <tr>
            <td style="color:var(--muted);">#{str(p['id']).zfill(4)}</td>
            <td>{p['nombre_cliente']}</td>
            <td style="color:var(--accent);font-weight:600;">S/. {p['total']:.2f}</td>
            <td><span style="background:{color}22;color:{color};padding:3px 10px;border-radius:20px;font-size:.78rem;font-weight:700;">{p['estado'].upper()}</span></td>
            <td style="color:var(--muted);font-size:.85rem;">{fecha_fmt}</td>
        </tr>"""
    if not ped_rows:
        ped_rows = '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:20px;">Sin pedidos aún</td></tr>'

    prod_rows = ""
    for p in productos:
        prod_rows += f"""
        <tr>
            <td>{p['id']}</td>
            <td><img src="/imagen/{p['imagen']}" style="width:44px;height:44px;object-fit:cover;border-radius:6px;" onerror="this.style.display='none'"></td>
            <td>{p['nombre']}</td>
            <td>{p['liga']}</td>
            <td>S/. {p['precio']:.2f}</td>
            <td>{p['stock']}</td>
            <td>
                <button class="admin-btn edit-btn" onclick="abrirEditar({p['id']}, '{p['nombre'].replace("'","\\'")}', '{p['liga']}', {p['precio']}, '{p['descripcion'] or ''}', '{p['imagen']}', {p['stock']})">Editar</button>
                <button class="admin-btn del-btn" onclick="eliminarProducto({p['id']}, '{p['nombre'].replace("'","\\'")}')">Eliminar</button>
            </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Panel Admin · Sagrada Piel</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0a0a1a;
    --card: #12122a;
    --card2: #0f0f24;
    --border: #1e1e40;
    --accent: #00d4aa;
    --accent2: #7c3aed;
    --accent3: #3b82f6;
    --text: #e0e0e0;
    --muted: #666;
    --danger: #e53e3e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; min-height: 100vh; }}

  /* Topbar */
  .admin-topbar {{
    background: var(--card);
    border-bottom: 1px solid var(--border);
    padding: 14px 32px;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 100;
  }}
  .admin-logo {{ font-size: 1.2rem; font-weight: 800; color: #fff; text-decoration: none; letter-spacing: 1px; }}
  .admin-logo span {{ color: var(--accent); }}
  .topbar-nav {{ display: flex; gap: 6px; }}
  .tab-nav {{ background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 7px 18px; border-radius: 8px; cursor: pointer; font-size: .85rem; font-weight: 600; transition: .2s; }}
  .tab-nav:hover {{ border-color: var(--accent); color: var(--accent); }}
  .tab-nav.active {{ background: var(--accent); color: #0a0a1a; border-color: var(--accent); }}
  .topbar-right {{ display: flex; gap: 10px; align-items: center; }}
  .topbar-right a {{ color: var(--muted); text-decoration: none; font-size: .85rem; padding: 7px 14px; border: 1px solid var(--border); border-radius: 8px; }}
  .topbar-right a:hover {{ border-color: var(--danger); color: var(--danger); }}

  /* Layout */
  .admin-body {{ padding: 28px 32px; max-width: 1280px; margin: 0 auto; }}
  .page-title {{ font-size: 1.5rem; font-weight: 800; margin-bottom: 4px; }}
  .page-sub {{ color: var(--muted); font-size: .85rem; margin-bottom: 24px; }}

  /* Tabs content */
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}

  /* Stat cards */
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .stat-card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    padding: 20px 22px; position: relative; overflow: hidden;
  }}
  .stat-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px; background: var(--accent-line, var(--accent)); }}
  .stat-card.c2::before {{ --accent-line: var(--accent2); }}
  .stat-card.c3::before {{ --accent-line: var(--accent3); }}
  .stat-card.c4::before {{ --accent-line: #f59e0b; }}
  .stat-lbl {{ color: var(--muted); font-size: .75rem; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; margin-bottom: 8px; }}
  .stat-val {{ font-size: 2rem; font-weight: 800; color: #fff; line-height: 1; }}
  .stat-sub {{ color: var(--muted); font-size: .78rem; margin-top: 6px; }}
  .stat-sub .up {{ color: #10b981; }}
  .stat-sub .down {{ color: #ef4444; }}

  /* Charts grid */
  .charts-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px; }}
  .charts-grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
  @media (max-width: 900px) {{ .charts-grid, .charts-grid2 {{ grid-template-columns: 1fr; }} }}

  /* Cards */
  .panel-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }}
  .card-title {{ font-size: .9rem; font-weight: 700; margin-bottom: 16px; color: var(--text); }}
  .chart-wrap {{ position: relative; height: 220px; }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; color: var(--muted); font-size: .73rem; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; padding: 0 12px 10px; border-bottom: 1px solid var(--border); }}
  td {{ padding: 12px; border-bottom: 1px solid var(--border); font-size: .87rem; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(255,255,255,.02); }}

  /* Productos section */
  .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }}
  .btn-add {{ background: var(--accent); color: #0a0a1a; border: none; padding: 9px 20px; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: .88rem; }}
  .btn-add:hover {{ opacity: .85; }}
  .admin-btn {{ border: none; padding: 5px 12px; border-radius: 6px; cursor: pointer; font-size: .8rem; font-weight: 600; margin-right: 4px; }}
  .edit-btn {{ background: rgba(124,58,237,.15); color: #a78bfa; border: 1px solid rgba(124,58,237,.3); }}
  .edit-btn:hover {{ background: rgba(124,58,237,.3); }}
  .del-btn {{ background: rgba(229,62,62,.1); color: #fc8181; border: 1px solid rgba(229,62,62,.3); }}
  .del-btn:hover {{ background: rgba(229,62,62,.25); }}

  /* Modal */
  .modal-overlay {{ display:none; position:fixed; inset:0; background:rgba(0,0,0,.75); z-index:1000; align-items:center; justify-content:center; }}
  .modal-overlay.show {{ display:flex; }}
  .modal-box {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 30px; width: 500px; max-width: 95vw; max-height: 90vh; overflow-y: auto; }}
  .modal-title {{ font-size: 1.1rem; font-weight: 800; margin-bottom: 18px; }}
  .field {{ margin-bottom: 13px; }}
  .field label {{ display:block; color:var(--muted); font-size:.75rem; margin-bottom:5px; font-weight:700; text-transform:uppercase; letter-spacing:.4px; }}
  .field input, .field textarea {{
    width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text);
    padding: 10px 14px; border-radius: 8px; font-size: .9rem; outline: none;
  }}
  .field input:focus, .field textarea:focus {{ border-color: var(--accent); }}
  .field textarea {{ resize: vertical; min-height: 60px; }}
  .modal-btns {{ display:flex; gap:10px; margin-top:18px; }}
  .btn-save {{ flex:1; background:var(--accent); color:#0a0a1a; border:none; padding:11px; border-radius:8px; font-weight:700; font-size:.92rem; cursor:pointer; }}
  .btn-cancel {{ flex:1; background:transparent; color:var(--muted); border:1px solid var(--border); padding:11px; border-radius:8px; font-weight:600; font-size:.92rem; cursor:pointer; }}

  /* Toast */
  .toast-admin {{ position:fixed; bottom:24px; right:24px; background:var(--accent); color:#0a0a1a; padding:12px 22px; border-radius:10px; font-weight:700; font-size:.9rem; transform:translateY(80px); opacity:0; transition:.3s; z-index:9999; }}
  .toast-admin.show {{ transform:translateY(0); opacity:1; }}
  .toast-admin.error {{ background:var(--danger); color:#fff; }}

  /* Confirm */
  .confirm-overlay {{ display:none; position:fixed; inset:0; background:rgba(0,0,0,.75); z-index:1100; align-items:center; justify-content:center; }}
  .confirm-overlay.show {{ display:flex; }}
  .confirm-box {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:28px; max-width:360px; text-align:center; }}
  .confirm-box h3 {{ font-size:1rem; margin-bottom:8px; }}
  .confirm-box p {{ color:var(--muted); font-size:.87rem; margin-bottom:18px; }}
  .confirm-btns {{ display:flex; gap:10px; justify-content:center; }}
  .btn-confirm-del {{ background:var(--danger); color:#fff; border:none; padding:9px 22px; border-radius:8px; font-weight:700; cursor:pointer; }}
  .btn-confirm-cancel {{ background:transparent; color:var(--muted); border:1px solid var(--border); padding:9px 22px; border-radius:8px; font-weight:600; cursor:pointer; }}
</style>
</head>
<body>

<div class="admin-topbar">
  <a href="/" class="admin-logo">SAGRADA<span>PIEL</span></a>
  <div class="topbar-nav">
    <button class="tab-nav active" onclick="switchTab('dashboard')">Dashboard</button>
    <button class="tab-nav" onclick="switchTab('productos')">Productos</button>
  </div>
  <div class="topbar-right">
    <a href="/">Ver tienda</a>
    <a href="/logout">Salir</a>
  </div>
</div>

<div class="admin-body">

  <!-- ═══ DASHBOARD ═══════════════════════════════════════════ -->
  <div class="tab-content active" id="tab-dashboard">
    <div class="page-title">Panel de Administración</div>
    <div class="page-sub">Sagrada Piel · Resumen general de la tienda</div>

    <!-- KPIs -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-lbl">Productos</div>
        <div class="stat-val">{total_productos}</div>
        <div class="stat-sub">En catálogo activo</div>
      </div>
      <div class="stat-card c2">
        <div class="stat-lbl">Precio promedio</div>
        <div class="stat-val">S/. {precio_prom:.2f}</div>
        <div class="stat-sub">Sobre todos los productos</div>
      </div>
      <div class="stat-card c3">
        <div class="stat-lbl">Clientes</div>
        <div class="stat-val">{total_usuarios}</div>
        <div class="stat-sub">Usuarios registrados</div>
      </div>
      <div class="stat-card c4">
        <div class="stat-lbl">Ingresos totales</div>
        <div class="stat-val">S/. {ingresos_total:.2f}</div>
        <div class="stat-sub">{total_pedidos} pedido{"s" if total_pedidos != 1 else ""} en total</div>
      </div>
    </div>

    <!-- Gráficas fila 1 -->
    <div class="charts-grid">
      <div class="panel-card">
        <div class="card-title">Ventas últimos 7 días (S/.)</div>
        <div class="chart-wrap"><canvas id="chartVentas"></canvas></div>
      </div>
      <div class="panel-card">
        <div class="card-title">Ventas por Liga</div>
        <div class="chart-wrap"><canvas id="chartLiga"></canvas></div>
      </div>
    </div>

    <!-- Gráficas fila 2 -->
    <div class="charts-grid2">
      <div class="panel-card">
        <div class="card-title">Pedidos por día (últimos 7 días)</div>
        <div class="chart-wrap"><canvas id="chartPedidos"></canvas></div>
      </div>
      <div class="panel-card">
        <div class="card-title">Clientes nuevos por día</div>
        <div class="chart-wrap"><canvas id="chartClientes"></canvas></div>
      </div>
    </div>

    <!-- Tablas fila 3 -->
    <div class="charts-grid2">
      <div class="panel-card">
        <div class="card-title">Top 5 productos más vendidos</div>
        <table>
          <thead><tr><th>#</th><th>Producto</th><th style="text-align:center">Uds.</th><th>Ingresos</th></tr></thead>
          <tbody>{top_rows}</tbody>
        </table>
      </div>
      <div class="panel-card">
        <div class="card-title">Pedidos recientes</div>
        <table>
          <thead><tr><th>ID</th><th>Cliente</th><th>Total</th><th>Estado</th><th>Fecha</th></tr></thead>
          <tbody>{ped_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ═══ PRODUCTOS ════════════════════════════════════════════ -->
  <div class="tab-content" id="tab-productos">
    <div class="page-title">Gestión de Productos</div>
    <div class="page-sub">Agrega, edita o elimina camisetas del catálogo</div>

    <div class="panel-card">
      <div class="section-header">
        <span style="font-weight:700;">{total_productos} camisetas en catálogo</span>
        <button class="btn-add" onclick="abrirNuevo()">+ Agregar camiseta</button>
      </div>
      <table>
        <thead>
          <tr><th>ID</th><th>Img</th><th>Nombre</th><th>Liga</th><th>Precio</th><th>Stock</th><th>Acciones</th></tr>
        </thead>
        <tbody id="tabla-productos">{prod_rows}</tbody>
      </table>
    </div>
  </div>

</div><!-- /admin-body -->

<!-- Modal producto -->
<div class="modal-overlay" id="modal-producto">
  <div class="modal-box">
    <div class="modal-title" id="modal-titulo">Agregar camiseta</div>
    <input type="hidden" id="prod-id">
    <div class="field"><label>Nombre</label><input type="text" id="prod-nombre" placeholder="Ej: Real Madrid - Local 24/25"></div>
    <div class="field"><label>Liga / Categoría</label><input type="text" id="prod-liga" placeholder="La Liga, Premier League, Selecciones..."></div>
    <div class="field"><label>Precio (S/.)</label><input type="number" id="prod-precio" placeholder="89.99" step="0.01" min="0"></div>
    <div class="field"><label>Descripción</label><textarea id="prod-desc" placeholder="Descripción de la camiseta..."></textarea></div>
    <div class="field"><label>Imagen (nombre de archivo en /imagenes/)</label><input type="text" id="prod-imagen" placeholder="real_madrid.jpeg"></div>
    <div class="field"><label>Stock</label><input type="number" id="prod-stock" placeholder="10" min="0"></div>
    <div class="modal-btns">
      <button class="btn-cancel" onclick="cerrarModal()">Cancelar</button>
      <button class="btn-save" onclick="guardarProducto()">Guardar</button>
    </div>
  </div>
</div>

<!-- Confirm delete -->
<div class="confirm-overlay" id="modal-confirm">
  <div class="confirm-box">
    <h3>Eliminar producto</h3>
    <p id="confirm-msg"></p>
    <div class="confirm-btns">
      <button class="btn-confirm-cancel" onclick="document.getElementById('modal-confirm').classList.remove('show')">Cancelar</button>
      <button class="btn-confirm-del" id="btn-confirm-del">Eliminar</button>
    </div>
  </div>
</div>

<div class="toast-admin" id="toast-admin"></div>

<script>
// ── Navegación de tabs ─────────────────────────────────────────
function switchTab(tab) {{
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-nav').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  event.currentTarget.classList.add('active');
}}

// ── Helpers chart ──────────────────────────────────────────────
const gridColor = 'rgba(255,255,255,0.05)';
const textColor = '#666';
const baseOpts = {{
  responsive: true, maintainAspectRatio: false,
  plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{}} }} }},
  scales: {{
    x: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor, font: {{ size: 11 }} }} }},
    y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor, font: {{ size: 11 }} }} }}
  }}
}};

// ── Gráfica: Ventas últimos 7 días ────────────────────────────
const ventas7Labels = {ventas_labels};
const ventas7Vals   = {ventas_vals};
new Chart(document.getElementById('chartVentas'), {{
  type: 'line',
  data: {{
    labels: ventas7Labels,
    datasets: [{{
      label: 'Ventas (S/.)',
      data: ventas7Vals,
      borderColor: '#00d4aa',
      backgroundColor: 'rgba(0,212,170,0.08)',
      borderWidth: 2.5,
      pointBackgroundColor: '#00d4aa',
      pointRadius: 4,
      tension: 0.35,
      fill: true
    }}]
  }},
  options: {{
    ...baseOpts,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ' S/. ' + ctx.parsed.y.toFixed(2) }} }}
    }},
    scales: {{
      x: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }} }},
      y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor, callback: v => 'S/.' + v }} }}
    }}
  }}
}});

// ── Gráfica: Ventas por Liga ──────────────────────────────────
const ligaLabels = {liga_labels};
const ligaVals   = {liga_vals};
const ligaColors = ['#00d4aa','#7c3aed','#3b82f6','#f59e0b','#ef4444','#10b981'];
new Chart(document.getElementById('chartLiga'), {{
  type: 'doughnut',
  data: {{
    labels: ligaLabels.length ? ligaLabels : ['Sin datos'],
    datasets: [{{
      data: ligaVals.length ? ligaVals : [1],
      backgroundColor: ligaColors,
      borderColor: '#12122a',
      borderWidth: 3
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'right', labels: {{ color: '#aaa', font: {{ size: 11 }}, boxWidth: 12, padding: 12 }} }},
      tooltip: {{ callbacks: {{ label: ctx => ' ' + ctx.label + ': ' + ctx.parsed + ' uds.' }} }}
    }}
  }}
}});

// ── Gráfica: Pedidos por día ───────────────────────────────────
const pedidosLabels = {pedidos_labels};
const pedidosVals   = {pedidos_vals};
new Chart(document.getElementById('chartPedidos'), {{
  type: 'bar',
  data: {{
    labels: pedidosLabels,
    datasets: [{{
      label: 'Pedidos',
      data: pedidosVals,
      backgroundColor: 'rgba(124,58,237,0.7)',
      borderColor: '#7c3aed',
      borderWidth: 1,
      borderRadius: 6
    }}]
  }},
  options: {{
    ...baseOpts,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ' ' + ctx.parsed.y + ' pedido(s)' }} }}
    }},
    scales: {{
      x: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }} }},
      y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor, stepSize: 1 }}, beginAtZero: true }}
    }}
  }}
}});

// ── Gráfica: Clientes nuevos ──────────────────────────────────
const clientesVals = {clientes_vals};
new Chart(document.getElementById('chartClientes'), {{
  type: 'bar',
  data: {{
    labels: pedidosLabels,
    datasets: [{{
      label: 'Clientes',
      data: clientesVals,
      backgroundColor: 'rgba(59,130,246,0.7)',
      borderColor: '#3b82f6',
      borderWidth: 1,
      borderRadius: 6
    }}]
  }},
  options: {{
    ...baseOpts,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ' ' + ctx.parsed.y + ' cliente(s)' }} }}
    }},
    scales: {{
      x: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor }} }},
      y: {{ grid: {{ color: gridColor }}, ticks: {{ color: textColor, stepSize: 1 }}, beginAtZero: true }}
    }}
  }}
}});

// ── Modal producto ────────────────────────────────────────────
let modoEdicion = false;

function mostrarToast(msg, error=false) {{
  const t = document.getElementById('toast-admin');
  t.textContent = msg;
  t.className = 'toast-admin' + (error ? ' error' : '') + ' show';
  setTimeout(() => t.classList.remove('show'), 2800);
}}

function abrirNuevo() {{
  modoEdicion = false;
  document.getElementById('modal-titulo').textContent = 'Agregar camiseta';
  ['prod-id','prod-nombre','prod-liga','prod-precio','prod-desc','prod-imagen'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('prod-stock').value = '10';
  document.getElementById('modal-producto').classList.add('show');
}}

function abrirEditar(id, nombre, liga, precio, desc, imagen, stock) {{
  modoEdicion = true;
  document.getElementById('modal-titulo').textContent = 'Editar camiseta';
  document.getElementById('prod-id').value     = id;
  document.getElementById('prod-nombre').value = nombre;
  document.getElementById('prod-liga').value   = liga;
  document.getElementById('prod-precio').value = precio;
  document.getElementById('prod-desc').value   = desc;
  document.getElementById('prod-imagen').value = imagen;
  document.getElementById('prod-stock').value  = stock;
  document.getElementById('modal-producto').classList.add('show');
}}

function cerrarModal() {{ document.getElementById('modal-producto').classList.remove('show'); }}

async function guardarProducto() {{
  const id     = document.getElementById('prod-id').value;
  const nombre = document.getElementById('prod-nombre').value.trim();
  const liga   = document.getElementById('prod-liga').value.trim();
  const precio = parseFloat(document.getElementById('prod-precio').value);
  const desc   = document.getElementById('prod-desc').value.trim();
  const imagen = document.getElementById('prod-imagen').value.trim();
  const stock  = parseInt(document.getElementById('prod-stock').value) || 0;
  if (!nombre || !liga || isNaN(precio)) {{ mostrarToast('Completa nombre, liga y precio.', true); return; }}
  const url  = modoEdicion ? '/admin/api/productos/editar' : '/admin/api/productos/crear';
  try {{
    const res  = await fetch(url, {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{id, nombre, liga, precio, descripcion: desc, imagen, stock}}) }});
    const data = await res.json();
    if (data.ok) {{ mostrarToast(modoEdicion ? 'Camiseta actualizada' : 'Camiseta agregada'); cerrarModal(); setTimeout(() => location.reload(), 900); }}
    else mostrarToast('Error: ' + (data.error || 'desconocido'), true);
  }} catch(e) {{ mostrarToast('Error de conexión', true); }}
}}

function eliminarProducto(id, nombre) {{
  document.getElementById('confirm-msg').textContent = `¿Eliminar "${{nombre}}"? Esta acción no se puede deshacer.`;
  document.getElementById('modal-confirm').classList.add('show');
  document.getElementById('btn-confirm-del').onclick = async () => {{
    document.getElementById('modal-confirm').classList.remove('show');
    try {{
      const res  = await fetch('/admin/api/productos/eliminar', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{id}}) }});
      const data = await res.json();
      if (data.ok) {{ mostrarToast('Camiseta eliminada'); setTimeout(() => location.reload(), 900); }}
      else mostrarToast('Error al eliminar', true);
    }} catch(e) {{ mostrarToast('Error de conexión', true); }}
  }};
}}

document.getElementById('modal-producto').addEventListener('click', function(e) {{
  if (e.target === this) cerrarModal();
}});
</script>
</body>
</html>"""
    return html

# ── API Admin ─────────────────────────────────────────────────────────────────

@app.route("/admin/api/productos/crear", methods=["POST"])
@admin_required
def admin_crear_producto():
    data = request.get_json()
    nombre = data.get("nombre","").strip()
    liga   = data.get("liga","").strip()
    precio = float(data.get("precio", 0))
    desc   = data.get("descripcion","").strip()
    imagen = data.get("imagen","").strip()
    stock  = int(data.get("stock", 10))
    if not nombre or not liga or precio <= 0:
        return jsonify({"ok": False, "error": "Datos incompletos"})
    with get_db() as db:
        db.execute(
            "INSERT INTO productos (nombre, liga, precio, descripcion, imagen, stock) VALUES (?,?,?,?,?,?)",
            (nombre, liga, precio, desc, imagen, stock)
        )
        db.commit()
    return jsonify({"ok": True})

@app.route("/admin/api/productos/editar", methods=["POST"])
@admin_required
def admin_editar_producto():
    data = request.get_json()
    pid    = int(data.get("id"))
    nombre = data.get("nombre","").strip()
    liga   = data.get("liga","").strip()
    precio = float(data.get("precio", 0))
    desc   = data.get("descripcion","").strip()
    imagen = data.get("imagen","").strip()
    stock  = int(data.get("stock", 10))
    if not nombre or not liga or precio <= 0:
        return jsonify({"ok": False, "error": "Datos incompletos"})
    with get_db() as db:
        db.execute(
            "UPDATE productos SET nombre=?, liga=?, precio=?, descripcion=?, imagen=?, stock=? WHERE id=?",
            (nombre, liga, precio, desc, imagen, stock, pid)
        )
        db.commit()
    return jsonify({"ok": True})

@app.route("/admin/api/productos/eliminar", methods=["POST"])
@admin_required
def admin_eliminar_producto():
    data = request.get_json()
    pid  = int(data.get("id"))
    with get_db() as db:
        db.execute("DELETE FROM productos WHERE id=?", (pid,))
        db.commit()
    return jsonify({"ok": True})

# ── Carrito ────────────────────────────────────────────────────────────────────

@app.route("/api/carrito/agregar", methods=["POST"])
def api_agregar():
    data = request.get_json()
    pid  = str(data.get("id"))
    carrito = session.get("carrito", {})
    if pid in carrito:
        carrito[pid]["cantidad"] += 1
    else:
        carrito[pid] = {"nombre": data["nombre"], "precio": data["precio"], "cantidad": 1}
    session["carrito"] = carrito
    session.modified = True
    total = sum(v["cantidad"] for v in carrito.values())
    return jsonify({"ok": True, "total_items": total})

@app.route("/api/carrito/actualizar", methods=["POST"])
def api_actualizar():
    data    = request.get_json()
    pid     = str(data.get("id"))
    cant    = int(data.get("cantidad", 1))
    carrito = session.get("carrito", {})
    if pid in carrito:
        if cant <= 0:
            del carrito[pid]
        else:
            carrito[pid]["cantidad"] = cant
    session["carrito"] = carrito
    session.modified = True
    subtotal = (carrito[pid]["precio"] * cant) if pid in carrito else 0
    gran_total = sum(v["precio"]*v["cantidad"] for v in carrito.values())
    total_items = sum(v["cantidad"] for v in carrito.values())
    return jsonify({"ok": True, "subtotal": subtotal, "gran_total": gran_total, "total_items": total_items})

@app.route("/api/carrito/vaciar", methods=["POST"])
def api_vaciar():
    session["carrito"] = {}
    session.modified = True
    return jsonify({"ok": True})

@app.route("/carrito")
def carrito():
    carrito = session.get("carrito", {})
    items_html = ""
    gran_total = 0.0
    for pid, v in carrito.items():
        sub = v["precio"] * v["cantidad"]
        gran_total += sub
        items_html += f"""
        <tr class="fila-item" id="fila-{pid}">
            <td class="td-producto">
                <div class="prod-mini">
                    <span class="prod-nombre">{v['nombre']}</span>
                </div>
            </td>
            <td class="td-precio">S/. {v['precio']:.2f}</td>
            <td class="td-cant">
                <div class="qty-ctrl">
                    <button class="qty-btn" onclick="cambiarCant('{pid}', {v['cantidad']-1})">−</button>
                    <span id="qty-{pid}" class="qty-val">{v['cantidad']}</span>
                    <button class="qty-btn" onclick="cambiarCant('{pid}', {v['cantidad']+1})">+</button>
                </div>
            </td>
            <td class="td-sub" id="sub-{pid}">S/. {sub:.2f}</td>
            <td class="td-del">
                <button class="btn-del" onclick="cambiarCant('{pid}', 0)">✕</button>
            </td>
        </tr>"""
    if not carrito:
        items_html = '<tr><td colspan="5" class="carrito-vacio">Tu carrito está vacío 🛒</td></tr>'
    usuario = session.get("usuario_nombre", "")
    total_items = sum(v["cantidad"] for v in carrito.values())
    html = read_file("carrito.html")
    html = html.replace("{{ITEMS}}", items_html)
    html = html.replace("{{GRAN_TOTAL}}", f"{gran_total:.2f}")
    html = html.replace("{{USUARIO}}", usuario)
    html = html.replace("{{TOTAL_ITEMS}}", str(total_items))
    return html

# ── Checkout ───────────────────────────────────────────────────────────────────

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    carrito = session.get("carrito", {})
    if not carrito:
        return redirect(url_for("carrito"))
    error = ""
    if request.method == "POST":
        nombre  = request.form.get("nombre","").strip()
        email   = request.form.get("email","").strip()
        dir_    = request.form.get("direccion","").strip()
        if not nombre or not email or not dir_:
            error = "Por favor completa todos los campos."
        else:
            total = sum(v["precio"]*v["cantidad"] for v in carrito.values())
            with get_db() as db:
                cur = db.execute(
                    "INSERT INTO pedidos (usuario_id,total,nombre_cliente,email_cliente,direccion) VALUES (?,?,?,?,?)",
                    (session.get("usuario_id"), total, nombre, email, dir_)
                )
                pedido_id = cur.lastrowid
                for pid, v in carrito.items():
                    db.execute(
                        "INSERT INTO pedido_items (pedido_id,producto_id,cantidad,precio) VALUES (?,?,?,?)",
                        (pedido_id, pid, v["cantidad"], v["precio"])
                    )
                db.commit()
            session["carrito"] = {}
            session.modified = True
            return redirect(url_for("confirmacion", pedido_id=pedido_id))
    items   = [(pid, v) for pid, v in carrito.items()]
    total   = sum(v["precio"]*v["cantidad"] for v in carrito.values())
    resumen = "".join(
        f'<div class="resumen-item"><span>{v["nombre"]} x{v["cantidad"]}</span><span>S/. {v["precio"]*v["cantidad"]:.2f}</span></div>'
        for _, v in items
    )
    usuario     = session.get("usuario_nombre", "")
    total_items = sum(v["cantidad"] for v in carrito.values())
    html = read_file("checkout.html")
    html = html.replace("{{RESUMEN}}", resumen)
    html = html.replace("{{TOTAL}}", f"{total:.2f}")
    html = html.replace("{{USUARIO}}", usuario)
    html = html.replace("{{TOTAL_ITEMS}}", str(total_items))
    html = html.replace("{{ERROR}}", f'<p class="error-msg">{error}</p>' if error else "")
    return html

@app.route("/confirmacion/<int:pedido_id>")
def confirmacion(pedido_id):
    with get_db() as db:
        p = db.execute("SELECT * FROM pedidos WHERE id=?", (pedido_id,)).fetchone()
    if not p:
        return redirect(url_for("index"))
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pedido Confirmado - Sagrada Piel</title>
<link rel="stylesheet" href="/css/style_main.css">
<style>
.confirm-box{{max-width:560px;margin:80px auto;background:#1a1a2e;border:2px solid #00d4aa;border-radius:16px;padding:48px;text-align:center}}
.check-icon{{font-size:64px;margin-bottom:16px}}
.confirm-box h1{{color:#00d4aa;font-size:2rem;margin-bottom:8px}}
.confirm-box p{{color:#aaa;margin-bottom:6px}}
.pedido-num{{font-size:1.4rem;color:#fff;font-weight:700;margin:16px 0}}
.confirm-total{{font-size:1.6rem;color:#00d4aa;font-weight:800;margin:12px 0}}
.btn-home{{display:inline-block;margin-top:24px;padding:12px 32px;background:#00d4aa;color:#0a0a1a;border-radius:8px;text-decoration:none;font-weight:700}}
</style>
</head>
<body style="background:#0a0a1a;font-family:'Segoe UI',sans-serif">
<div class="confirm-box">
<div class="check-icon">✅</div>
<h1>¡Pedido Confirmado!</h1>
<p>Gracias, <strong style="color:#fff">{p['nombre_cliente']}</strong></p>
<p>Tu pedido ha sido registrado correctamente.</p>
<div class="pedido-num">Pedido #{"0"*(5-len(str(pedido_id)))}{pedido_id}</div>
<div class="confirm-total">Total: S/. {p['total']:.2f}</div>
<p style="color:#888;font-size:.9rem">Te contactaremos a {p['email_cliente']}</p>
<a href="/" class="btn-home">Seguir comprando</a>
</div>
</body>
</html>"""
    return html

# ── Imágenes ───────────────────────────────────────────────────────────────────

@app.route("/imagen/<nombre>")
def imagen(nombre):
    for ext in ["", ".jpeg", ".jpg", ".png"]:
        path = os.path.join("imagenes", nombre + ext if not nombre.endswith((".jpeg",".jpg",".png")) else nombre)
        if os.path.exists(path):
            return send_file(path)
    svg = """<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 300 300'>
<rect width='300' height='300' fill='#1a1a2e'/>
<text x='50%' y='45%' font-family='Arial' font-size='48' fill='#333' text-anchor='middle'>👕</text>
<text x='50%' y='65%' font-family='Arial' font-size='14' fill='#555' text-anchor='middle'>Sin imagen</text>
</svg>"""
    from flask import Response
    return Response(svg, mimetype="image/svg+xml")

# ── CSS estático ───────────────────────────────────────────────────────────────

@app.route("/css/<filename>")
def css(filename):
    if os.path.exists(filename):
        return send_file(filename, mimetype="text/css")
    return "", 404

@app.route("/api/usuario")
def api_usuario():
    return jsonify({
        "logueado": "usuario_id" in session,
        "nombre": session.get("usuario_nombre",""),
        "es_admin": session.get("es_admin", False)
    })

app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
