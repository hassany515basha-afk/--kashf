from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime
import sqlite3, os, uuid, io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

DB = "kashf.db"
SECRET = os.getenv("JWT_SECRET", "change_this_secret_in_production")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="KASHF - كاشف")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT DEFAULT 'user');
    CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY AUTOINCREMENT,ref TEXT UNIQUE,category TEXT,governorate TEXT,area TEXT,target TEXT,subject TEXT,details TEXT,status TEXT DEFAULT 'prepared',created_at TEXT);
    CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,category TEXT,governorate TEXT,description TEXT,url TEXT,phone TEXT,status TEXT DEFAULT 'official');
    """)
    if conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0:
        items = [
            ("بوابة الحكومة المصرية","government","القاهرة","بوابة الخدمات الحكومية الإلكترونية الرسمية في مصر.","https://www.egypt.gov.eg",""),
            ("وزارة الصحة والسكان","health","القاهرة","الموقع الرسمي لوزارة الصحة والسكان في مصر.","https://www.moh.gov.eg",""),
            ("وزارة التربية والتعليم","education","القاهرة","الموقع الرسمي لوزارة التربية والتعليم في مصر.","https://moe.gov.eg",""),
            ("وزارة النقل","transport","القاهرة","الموقع الرسمي لوزارة النقل في مصر.","https://www.mot.gov.eg",""),
            ("السكة الحديد المصرية","transport","القاهرة","الموقع الرسمي للسكة الحديد المصرية.","https://enr.gov.eg",""),
            ("مصلحة الضرائب المصرية","government","القاهرة","مصلحة الضرائب المصرية.","https://www.eta.gov.eg",""),
            ("التأمينات الاجتماعية","government","القاهرة","الهيئة القومية للتأمين الاجتماعي في مصر.","https://www.social-insurance.gov.eg",""),
            ("هيئة الأمن الغذائي","government","القاهرة","هيئة الأمن الغذائي في مصر.","https://www.nfa.gov.eg",""),
            ("وزارة الداخلية","safety","القاهرة","الموقع الرسمي لوزارة الداخلية المصرية.","https://www.moi.gov.eg",""),
            ("وزارة العدل","legal","القاهرة","الموقع الرسمي لوزارة العدل المصرية.","https://www.moj.gov.eg",""),
            ("وزارة الخارجية","government","القاهرة","الموقع الرسمي لوزارة الخارجية المصرية.","https://www.mfa.gov.eg",""),
            ("وزارة الاتصالات وتكنولوجيا المعلومات","government","القاهرة","الموقع الرسمي لوزارة الاتصالات وتكنولوجيا المعلومات.","https://www.mcit.gov.eg",""),
            ("الهيئة العامة للمعلومات المدنية","government","القاهرة","الهيئة العامة للمعلومات المدنية في مصر.","https://www.cr.gov.eg",""),
            ("الشهر العقاري والتوثيق","government","القاهرة","المصلحة العامة للشهر العقاري والتوثيق في مصر.","https://www.mpd.gov.eg",""),
            ("البريد المصري","finance","القاهرة","الهيئة العامة للبريد في مصر.","https://www.egyptpost.org",""),
            ("البنك المركزي المصري","finance","القاهرة","الموقع الرسمي للبنك المركزي المصري.","https://www.cbe.org.eg",""),
            ("هيئة الرقابة المالية","finance","القاهرة","هيئة الرقابة المالية في مصر.","https://fra.gov.eg",""),
            ("وزارة البيئة","government","القاهرة","الموقع الرسمي لوزارة البيئة المصرية.","https://www.eeaa.gov.eg",""),
            ("وزارة السياحة والآثار","tourism","القاهرة","الموقع الرسمي لوزارة السياحة والآثار المصرية.","https://www.mota.gov.eg",""),
            ("وزارة العمل","jobs","القاهرة","الموقع الرسمي لوزارة العمل المصرية.","https://www.manpower.gov.eg",""),
            ("خدمة الطوارئ 123","safety","القاهرة","الاتصال بالطوارئ والإسعاف في مصر.","https://www.egypt.gov.eg","123"),
            ("شرطة السياحة 126","safety","القاهرة","رقم شرطة السياحة والآثار في مصر.","https://www.egypt.gov.eg","126"),
            ("شرطة المرور 128","safety","القاهرة","رقم شرطة المرور في مصر.","https://www.egypt.gov.eg","128")
        ]
        conn.executemany("INSERT INTO listings(title,category,governorate,description,url,phone) VALUES(?,?,?,?,?,?)", items)
    conn.commit(); conn.close()

init()

class UserIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class ComplaintIn(BaseModel):
    category: str
    governorate: str
    area: str = ""
    target: str = ""
    subject: str
    details: str

@app.get("/api/listings")
def listings(q: str = "", category: str = ""):
    conn = db()
    sql = "SELECT * FROM listings WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND category=?"
        params.append(category)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/complaints")
def create_complaint(data: ComplaintIn):
    ref = "KSHF-" + uuid.uuid4().hex[:10].upper()
    conn = db()
    conn.execute("INSERT INTO complaints(ref,category,governorate,area,target,subject,details,created_at) VALUES(?,?,?,?,?,?,?,?)",
                 (ref, data.category, data.governorate, data.area, data.target, data.subject, data.details, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return {"reference": ref, "message": "تم إنشاء الشكوى وتجهيزها. لم يتم إرسالها تلقائيًا إلى جهة حكومية."}

@app.get("/api/complaints/{ref}")
def get_complaint(ref: str):
    conn = db()
    row = conn.execute("SELECT * FROM complaints WHERE ref=?", (ref,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "رقم الشكوى غير موجود")
    return dict(row)

@app.get("/api/complaints/{ref}/pdf")
def complaint_pdf(ref: str):
    conn = db()
    row = conn.execute("SELECT * FROM complaints WHERE ref=?", (ref,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "رقم الشكوى غير موجود")
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(105*mm, 280*mm, "KASHF - KASHF Complaint")
    y = 260*mm
    for k, v in [("Reference", row["ref"]), ("Category", row["category"]), ("Governorate", row["governorate"]),
                 ("Area", row["area"] or "-"), ("Target", row["target"] or "-"), ("Subject", row["subject"]), ("Status", row["status"])]:
        pdf.setFont("Helvetica-Bold", 11); pdf.drawString(20*mm, y, f"{k}:")
        pdf.setFont("Helvetica", 11); pdf.drawString(60*mm, y, str(v)[:80]); y -= 8*mm
    y -= 6*mm
    pdf.setFont("Helvetica-Bold", 12); pdf.drawString(20*mm, y, "Details:"); y -= 8*mm
    pdf.setFont("Helvetica", 11)
    for i in range(0, len(row["details"]), 90):
        pdf.drawString(20*mm, y, row["details"][i:i+90]); y -= 7*mm
    pdf.setFont("Helvetica", 9)
    pdf.drawString(20*mm, 20*mm, "Prepared via KASHF. Not automatically submitted to any government entity.")
    pdf.showPage(); pdf.save(); buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{ref}.pdf"'})

@app.post("/api/register")
def register(data: UserIn):
    conn = db()
    if conn.execute("SELECT id FROM users WHERE email=?", (data.email,)).fetchone():
        conn.close(); raise HTTPException(400, "البريد مستخدم بالفعل")
    conn.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)", (data.name, data.email, pwd.hash(data.password)))
    conn.commit(); conn.close()
    return {"message": "تم إنشاء الحساب"}

@app.post("/api/login")
def login(data: UserIn):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE email=?", (data.email,)).fetchone()
    conn.close()
    if not row or not pwd.verify(data.password, row["password"]):
        raise HTTPException(401, "بيانات الدخول غير صحيحة")
    token = jwt.encode({"sub": str(row["id"]), "role": row["role"]}, SECRET, algorithm="HS256")
    return {"token": token, "name": row["name"], "role": row["role"]}

@app.get("/")
def home():
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static", html=True), name="static")
