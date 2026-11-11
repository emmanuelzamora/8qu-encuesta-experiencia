import os, re, hmac, hashlib, secrets
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
import psycopg
from psycopg.rows import dict_row

app=Flask(__name__)
BRANCHES=['UPIICSA','ESIA Zacatenco','ESIA Tecamachalco','Otra sede']
QUESTIONS=['atencion','sabor','porcion','rapidez','general']

def db():
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row)

def setup():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS feedback (id BIGSERIAL PRIMARY KEY,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),branch TEXT NOT NULL,phone_hash CHAR(64) NOT NULL,atencion SMALLINT NOT NULL CHECK(atencion BETWEEN 1 AND 5),sabor SMALLINT NOT NULL CHECK(sabor BETWEEN 1 AND 5),porcion SMALLINT NOT NULL CHECK(porcion BETWEEN 1 AND 5),rapidez SMALLINT NOT NULL CHECK(rapidez BETWEEN 1 AND 5),general SMALLINT NOT NULL CHECK(general BETWEEN 1 AND 5),comment VARCHAR(700) NOT NULL DEFAULT '',consent BOOLEAN NOT NULL CHECK(consent))''')
        con.execute('CREATE INDEX IF NOT EXISTS feedback_dedupe ON feedback(phone_hash,branch,created_at DESC)')
        con.execute('CREATE INDEX IF NOT EXISTS feedback_branch_date ON feedback(branch,created_at DESC)')

@app.get('/')
def index(): return render_template('index.html')

@app.get('/privacidad')
def privacy(): return render_template('privacidad.html')

@app.get('/health')
def health(): return {'status':'ok'}

@app.post('/api/feedback')
def feedback():
    d=request.get_json(silent=True) or {}
    if d.get('website'): return jsonify(ok=True)
    phone=re.sub(r'\D','',str(d.get('phone','')))
    if phone.startswith('52') and len(phone)==12: phone=phone[2:]
    if not re.fullmatch(r'\d{10}',phone): return jsonify(error='Ingresa un celular de 10 dígitos.'),400
    branch=d.get('branch')
    if branch not in BRANCHES: return jsonify(error='Selecciona una sucursal.'),400
    ratings=d.get('ratings') or {}
    if any(type(ratings.get(q)) is not int or not 1<=ratings[q]<=5 for q in QUESTIONS): return jsonify(error='Completa las cinco calificaciones.'),400
    comment=str(d.get('comment','')).strip()
    if len(comment)>700: return jsonify(error='El comentario supera 700 caracteres.'),400
    if d.get('consent') is not True: return jsonify(error='Debes aceptar el aviso de privacidad.'),400
    secret=os.environ.get('PHONE_HASH_SECRET','')
    if len(secret)<32: return jsonify(error='Configuración del servidor pendiente.'),503
    hashed=hmac.new(secret.encode(),phone.encode(),hashlib.sha256).hexdigest()
    try:
        with db() as con:
            # Advisory lock prevents simultaneous duplicate submissions for a phone+branch.
            con.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(hashed+branch,))
            existing=con.execute('SELECT 1 FROM feedback WHERE phone_hash=%s AND branch=%s AND created_at > now() - interval \'7 days\' LIMIT 1',(hashed,branch)).fetchone()
            if existing: return jsonify(error='Ya recibimos una evaluación de este celular para esta sucursal en los últimos 7 días.'),409
            con.execute('''INSERT INTO feedback(branch,phone_hash,atencion,sabor,porcion,rapidez,general,comment,consent) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,TRUE)''',(branch,hashed,*(ratings[q] for q in QUESTIONS),comment))
    except psycopg.Error:
        app.logger.exception('Database failure')
        return jsonify(error='No se pudo guardar. Intenta más tarde.'),503
    return jsonify(ok=True),201

def admin_auth(fn):
    @wraps(fn)
    def inner(*a,**kw):
        auth=request.authorization
        user=os.environ.get('ADMIN_USER',''); password=os.environ.get('ADMIN_PASSWORD','')
        if not user or not password or not auth or not (secrets.compare_digest(auth.username or '',user) and secrets.compare_digest(auth.password or '',password)):
            return Response('Acceso restringido',401,{'WWW-Authenticate':'Basic realm="8Qu Administracion"'})
        return fn(*a,**kw)
    return inner

@app.get('/admin')
@admin_auth
def admin():
    with db() as con:
        summary=con.execute('''SELECT branch,count(*) n,round(avg(atencion)::numeric,2) atencion,round(avg(sabor)::numeric,2) sabor,round(avg(porcion)::numeric,2) porcion,round(avg(rapidez)::numeric,2) rapidez,round(avg(general)::numeric,2) general FROM feedback GROUP BY branch ORDER BY branch''').fetchall()
        recent=con.execute('SELECT created_at,branch,atencion,sabor,porcion,rapidez,general,comment FROM feedback ORDER BY created_at DESC LIMIT 100').fetchall()
    return render_template('admin.html',summary=summary,recent=recent)

if __name__=='__main__': app.run(debug=False)
