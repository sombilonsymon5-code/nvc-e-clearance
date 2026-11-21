from flask import Flask, request, redirect, session, g
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nvc-secret-2026"
DB = "nvc_clearance.db"

# --- NVC DEPARTMENTS ---
CLEARANCE_TYPES = [
    "Library Clearance",
    "Guidance Clearance",
    "Registrar Clearance",
    "Registrar - Good Moral Certificate",
    "Department Clearance",
    "Accounting Clearance"
]

DEPARTMENTS = ["Library", "Guidance", "Registrar", "Department", "Accounting"]
STATUSES = ["Pending", "Approved", "Rejected", "For Compliance"]

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB)
    db.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, student_id TEXT UNIQUE, password TEXT, course TEXT, role TEXT DEFAULT 'student'
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, clearance_type TEXT, purpose TEXT, status TEXT DEFAULT 'Pending',
        created_at TEXT
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS remarks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER, department TEXT, status TEXT DEFAULT 'Pending',
        remark TEXT DEFAULT 'Waiting for review', updated_at TEXT
    )""")
    # Default Admin
    try:
        db.execute("INSERT INTO users(name, student_id, password, course, role) VALUES(?,?,?,?,?)",
                   ("Admin NVC", "admin", "admin123", "Admin", "admin"))
    except: pass
    db.commit(); db.close()

init_db()

HEAD = """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Northwestern Visayan Colleges - E-Clearance</title>
<style>
body{font-family:Arial;background:#f0f4f8;margin:0;padding:15px}
.header{background:#0B3D91;color:white;padding:20px;border-radius:12px;text-align:center}
.header h1{margin:0;font-size:22px}.header p{margin:5px 0 0;opacity:.9}
.card{background:white;padding:18px;border-radius:12px;margin-top:15px;box-shadow:0 2px 8px #0001}
input,select,textarea{width:100%;padding:11px;margin:7px 0;border:1px solid #ccc;border-radius:8px;box-sizing:border-box}
button,.btn{background:#0B3D91;color:white;padding:11px 16px;border:none;border-radius:8px;display:inline-block;text-decoration:none;cursor:pointer}
.btn-green{background:#1a9e4b}.btn-red{background:#d32f2f}.btn-gray{background:#666}
table{width:100%;border-collapse:collapse;margin-top:10px}th,td{border:1px solid #ddd;padding:8px;text-align:left;font-size:13px}th{background:#0B3D91;color:white}
.badge{padding:4px 8px;border-radius:20px;font-size:12px;color:white}
.Pending{background:#ff9800}.Approved{background:#1a9e4b}.Rejected{background:#d32f2f}.For\\ Compliance{background:#7b1fa2}
</style></head><body>
<div class='header'><h1>🎓 NORTHWESTERN VISAYAN COLLEGES</h1><p>E-Clearance System - Bacolod City</p></div>
"""

FOOT = "</body></html>"

@app.route("/")
def index():
    if 'user_id' in session: return redirect("/dashboard")
    return HEAD + """
    <div class='card'><h2>Login - NVC E-Clearance</h2>
    <form method='post' action='/login'>
    Student ID / Username<br><input name='student_id' placeholder='ex: 2026-001 or admin' required>
    Password<br><input type='password' name='password' placeholder='Password' required>
    <button>Login</button></form>
    <p>New student? <a href='/register'>Register here</a></p>
    <p><b>Admin:</b> admin / admin123</p></div>""" + FOOT

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        db=get_db()
        try:
            db.execute("INSERT INTO users(name,student_id,password,course) VALUES(?,?,?,?)",
                       (request.form['name'],request.form['student_id'],request.form['password'],request.form['course']))
            db.commit(); return redirect("/")
        except: return HEAD+"<div class='card'>Student ID already exists! <a href='/register'>Try again</a></div>"+FOOT
    return HEAD+"""
    <div class='card'><h2>Student Registration</h2>
    <form method='post'>Full Name<input name='name' required>
    Student ID<input name='student_id' required>
    Course<input name='course' placeholder='ex: BSIT' required>
    Password<input type='password' name='password' required>
    <button>Register</button></form><a href='/'>Back to Login</a></div>"""+FOOT

@app.route("/login", methods=["POST"])
def login():
    db=get_db()
    u=db.execute("SELECT * FROM users WHERE student_id=? AND password=?",
                 (request.form['student_id'],request.form['password'])).fetchone()
    if u:
        session['user_id']=u['id']; session['role']=u['role']; session['name']=u['name']
        return redirect("/dashboard")
    return HEAD+"<div class='card'>Wrong ID or Password! <a href='/'>Back</a></div>"+FOOT

@app.route("/logout")
def logout():
    session.clear(); return redirect("/")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session: return redirect("/")
    db=get_db()
    if session['role']=='admin':
        reqs=db.execute("SELECT r.*, u.name, u.student_id, u.course FROM requests r JOIN users u ON r.user_id=u.id ORDER BY r.id DESC").fetchall()
        html=HEAD+f"<div class='card'><h2>Admin Dashboard - Hi {session['name']}!</h2><a href='/logout' class='btn btn-gray'>Logout</a></div><div class='card'><h3>All Clearance Requests</h3><table><tr><th>Student</th><th>Clearance</th><th>Purpose</th><th>Action</th></tr>"
        for r in reqs:
            html+=f"<tr><td>{r['name']}<br>{r['student_id']} - {r['course']}</td><td>{r['clearance_type']}</td><td>{r['purpose']}</td><td><a href='/view/{r['id']}' class='btn'>View & Remarks</a></td></tr>"
        return html+"</table></div>"+FOOT
    else:
        reqs=db.execute("SELECT * FROM requests WHERE user_id=? ORDER BY id DESC",(session['user_id'],)).fetchall()
        opts="".join([f"<option>{c}</option>" for c in CLEARANCE_TYPES])
        html=HEAD+f"<div class='card'><h2>Hi {session['name']}!</h2><p>Welcome to NVC E-Clearance</p><a href='/logout' class='btn btn-gray'>Logout</a></div>"
        html+="<div class='card'><h3>Request New Clearance</h3><form method='post' action='/request'>Clearance Type<select name='clearance_type'>"+opts+"</select>Purpose<textarea name='purpose' placeholder='ex: For graduation, for enrollment' required></textarea><button>Submit Request</button></form></div>"
        html+="<div class='card'><h3>My Requests</h3><table><tr><th>Type</th><th>Purpose</th><th>Status</th><th>Action</th></tr>"
        for r in reqs:
            html+=f"<tr><td>{r['clearance_type']}</td><td>{r['purpose']}</td><td><span class='badge {r['status']}'>{r['status']}</span></td><td><a href='/view/{r['id']}' class='btn'>View Remarks</a></td></tr>"
        return html+"</table></div>"+FOOT

@app.route("/request", methods=["POST"])
def new_request():
    if 'user_id' not in session: return redirect("/")
    db=get_db()
    cur=db.execute("INSERT INTO requests(user_id,clearance_type,purpose,status,created_at) VALUES(?,?,?,?,?)",
                   (session['user_id'],request.form['clearance_type'],request.form['purpose'],"Pending",datetime.now().strftime("%Y-%m-%d %H:%M")))
    rid=cur.lastrowid
    for d in DEPARTMENTS:
        db.execute("INSERT INTO remarks(request_id,department,status,remark,updated_at) VALUES(?,?,?,?,?)",
                   (rid,d,"Pending","Waiting for review",datetime.now().strftime("%Y-%m-%d %H:%M")))
    db.commit(); return redirect("/dashboard")

@app.route("/view/<int:rid>", methods=["GET","POST"])
def view(rid):
    db=get_db()
    r=db.execute("SELECT r.*, u.name, u.student_id, u.course FROM requests r JOIN users u ON r.user_id=u.id WHERE r.id=?",(rid,)).fetchone()
    if not r: return redirect("/dashboard")
    if request.method=="POST" and session.get('role')=='admin':
        db.execute("UPDATE remarks SET status=?, remark=?, updated_at=? WHERE id=?",
                   (request.form['status'],request.form['remark'],datetime.now().strftime("%Y-%m-%d %H:%M"),request.form['remark_id']))
        # Update overall status: if all approved -> Approved
        all_rem=db.execute("SELECT status FROM remarks WHERE request_id=?",(rid,)).fetchall()
        sts=[x['status'] for x in all_rem]
        if all(s=="Approved" for s in sts): overall="Approved"
        elif "Rejected" in sts: overall="Rejected"
        elif "For Compliance" in sts: overall="For Compliance"
        else: overall="Pending"
        db.execute("UPDATE requests SET status=? WHERE id=?",(overall,rid))
        db.commit(); return redirect(f"/view/{rid}")
    remarks=db.execute("SELECT * FROM remarks WHERE request_id=?",(rid,)).fetchall()
    html=HEAD+f"<div class='card'><h2>{r['clearance_type']}</h2><p><b>Student:</b> {r['name']} ({r['student_id']} - {r['course']})<br><b>Purpose:</b> {r['purpose']}<br><b>Overall:</b> <span class='badge {r['status']}'>{r['status']}</span></p><a href='/dashboard'>Back to Dashboard</a></div>"
    html+="<div class='card'><h3>Department Remarks - Library / Guidance / Registrar / Department / Accounting</h3><table><tr><th>Department</th><th>Status</th><th>Remarks</th>"
    if session.get('role')=='admin': html+="<th>Update</th>"
    html+="</tr>"
    for m in remarks:
        html+=f"<tr><td><b>{m['department']}</b></td><td><span class='badge {m['status']}'>{m['status']}</span></td><td>{m['remark']}<br><small>{m['updated_at']}</small></td>"
        if session.get('role')=='admin':
            html+=f"""<td><form method='post'>
            <input type='hidden' name='remark_id' value='{m['id']}'>
            <select name='status'><option>Pending</option><option>Approved</option><option>Rejected</option><option>For Compliance</option></select>
            <input name='remark' placeholder='ex: No unpaid books, Cleared, Need Good Moral' required>
            <button class='btn-green'>Save</button></form></td>"""
        html+="</tr>"
    return html+"</table></div>"+FOOT

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)