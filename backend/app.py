# -*- coding: utf-8 -*-
"""
TWS - Tool Warehouse System
============================
RESTful API backend with SQLite persistence.
Includes warehouse robot/conveyor belt simulation.
"""

import os
import sys
import sqlite3
import datetime
import hashlib
import time
import random
import threading
from queue import Queue
from functools import wraps
from flask import Flask, request, jsonify, g

# ============================================================
# Database path (relative to this file)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'tws_data.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tws-system-secret'

# ============================================================
# CORS support (allow frontend at localhost:8080 to call API)
# ============================================================
@app.after_request
def cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response


@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        return resp

# ============================================================
# TWS Warehouse Simulation
# ============================================================

class Product:
    """Tool product in the warehouse."""
    def __init__(self, name, tool_id='', expensive=False):
        self.id = tool_id
        self.name = name
        self.expensive = expensive
        self.weight = random.random() * 100

    def __str__(self):
        return self.name


class Converger:
    """Conveyor belt with weight sensor."""
    def __init__(self, name=''):
        self.name = name
        self.weight = 0
        self.prod_queue = Queue(maxsize=10)

    def put(self, product):
        if isinstance(product, Product):
            self.prod_queue.put(product)
            self.weight += product.weight
            print(f"[WMS] Converger: {product} placed on belt")
        else:
            print("[WMS] Converger: Invalid product")

    def get(self):
        prod = self.prod_queue.get()
        self.weight -= prod.weight
        return prod

    def output(self, product):
        print(f"[WMS] Converger outlet: {product} delivered")

    def move(self, waketime=1, movetime=4):
        while True:
            time.sleep(waketime)
            if self.weight > 0:
                product = self.get()
                print(f"[WMS] Belt transporting: {product}")
                time.sleep(movetime)
                self.output(product)

    def get_weight(self):
        return self.weight


class Robot:
    """Warehouse robot that fetches tools from shelves."""
    def __init__(self, name='', con=None):
        self.name = name
        self.converger = con or Converger()
        self.state = 'Fine'
        self.use = False
        self.request_queue = Queue(maxsize=10)

    def self_check(self):
        return self.state == 'Fine'

    def is_in_use(self):
        return self.use

    def set_in_use(self):
        if self.is_in_use():
            print(f"[WMS] {self.name} is already in use!")
        else:
            self.use = True

    def set_not_in_use(self):
        if not self.is_in_use():
            print(f"[WMS] {self.name} is not in use!")
        else:
            self.use = False

    def move(self, product):
        self.request_queue.put(product)
        print(f"[WMS] {self.name}: received fetch command for {product}")

    def work(self, waketime=2, movetime=5):
        while True:
            time.sleep(waketime)
            print(f"[WMS] {self.name}: waiting for command...")
            if not self.self_check():
                print(f"[WMS] {self.name}: malfunction, stopping")
                break
            if self.request_queue.qsize() > 0 and not self.is_in_use():
                print(f"[WMS] {self.name}: fetching tool...")
                product = self.request_queue.get()
                self.set_in_use()
                time.sleep(movetime)
                self.converger.put(product)
                self.set_not_in_use()
        return True


class Computer:
    """Warehouse control computer that dispatches robots."""
    def __init__(self, name=None, robots=None):
        self.name = name
        self.robots = robots or []

    def check(self, name):
        """Verify user exists in database."""
        return True  # Simplified - already verified by API layer

    def fetch_product(self, product):
        for robot in self.robots:
            if robot.self_check() and not robot.is_in_use():
                robot.move(product)
                break

    def add_robot(self, robot):
        self.robots.append(robot)

    def remove_robot(self, robot):
        if robot in self.robots:
            self.robots.remove(robot)


class User:
    """Employee who borrows tools."""
    def __init__(self, name):
        self.name = name

    def borrow(self, admin, product):
        admin.inform(self.name, product)


class Admin:
    """Warehouse administrator who manages requests."""
    def __init__(self, name, computer=None):
        self.name = name
        self.computer = computer or Computer()
        self.request_queue = Queue(maxsize=10)

    def manage(self, waketime=1):
        while True:
            time.sleep(waketime)
            if not self.request_queue.empty():
                lis = self.request_queue.get()
                user_name = lis[0]
                product = lis[1]
                self.computer.fetch_product(product)
                print(f"[WMS] Admin: {user_name}'s request for {product} is being processed...")

    def inform(self, user, product):
        if self.computer.check(user):
            self.request_queue.put([user, product])
            return True
        return False


class TWS:
    """TWS system coordinating admin, computer, robots, and conveyor."""
    def __init__(self, admin, computer, robots, products, converger):
        self.admin = admin
        self.computer = computer
        self.robots = robots
        self.products = products
        self.converger = converger

    def run(self, user_name, product_name):
        """Start the warehouse simulation for a tool request."""
        user = User(user_name)
        product = Product(product_name, expensive=True)

        print(f"\n[WMS] === TWS Simulation Start ===")
        print(f"[WMS] User: {user_name}, Tool: {product_name}")

        user.borrow(self.admin, product)

        try:
            _thread.start_new_thread(self.admin.manage, (1,))
            for robot in self.robots:
                _thread.start_new_thread(robot.work, (2, 5))
            _thread.start_new_thread(self.converger.move, (1, 4))
        except:
            print("[WMS] Error: Could not start threads")

        time.sleep(15)
        print(f"[WMS] === TWS Simulation Complete ===\n")

import _thread

# Global TWS instance (lazy init)
_tws = None

def get_tws():
    global _tws
    if _tws is None:
        computer = Computer("Warehouse Computer")
        admin = Admin("Warehouse Admin", computer)
        products = [
            Product("Hammer", "14314"),
            Product("Screwdriver", "241432"),
            Product("Scissors", "441413"),
            Product("Pliers", "534134"),
            Product("Excavator", "634134", expensive=True),
        ]
        converger = Converger("Main Conveyor Belt")
        robots = [
            Robot("Robot-1", converger),
            Robot("Robot-2", converger),
            Robot("Robot-3", converger),
        ]
        for r in robots:
            computer.add_robot(r)
        _tws = TWS(admin, computer, robots, products, converger)
        print("[TWS] Warehouse simulation system initialized")
    return _tws


def run_tws_simulation(user_name, product_name):
    """Run the TWS warehouse simulation in a background thread."""
    try:
        tws = get_tws()
        tws.run(user_name, product_name)
        return True
    except Exception as e:
        print(f"[TWS] Simulation error: {e}")
        return False


# ============================================================
# Database
# ============================================================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS EMPLOYEE (
            EID TEXT PRIMARY KEY,
            Name TEXT NOT NULL,
            Depart TEXT,
            Soncmp TEXT,
            Worktype TEXT
        );

        CREATE TABLE IF NOT EXISTS TOOL (
            TID TEXT PRIMARY KEY,
            Name TEXT NOT NULL,
            Tooltype TEXT,
            Soncmp TEXT,
            Price REAL DEFAULT 0,
            Good INTEGER DEFAULT 1,
            Borrow INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS LEND (
            LID TEXT PRIMARY KEY,
            Lendtime TEXT,
            EID TEXT NOT NULL,
            TID TEXT NOT NULL,
            FOREIGN KEY (EID) REFERENCES EMPLOYEE(EID) ON DELETE CASCADE,
            FOREIGN KEY (TID) REFERENCES TOOL(TID) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS LOGIN (
            EID TEXT PRIMARY KEY,
            Password TEXT NOT NULL,
            FOREIGN KEY (EID) REFERENCES EMPLOYEE(EID) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS LENDTMP (
            EID TEXT NOT NULL,
            Lendtime TEXT,
            TID TEXT NOT NULL,
            PRIMARY KEY (EID, TID, Lendtime),
            FOREIGN KEY (EID) REFERENCES EMPLOYEE(EID) ON DELETE CASCADE,
            FOREIGN KEY (TID) REFERENCES TOOL(TID) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS NOTIFICATIONS (
            NID TEXT PRIMARY KEY,
            Type TEXT DEFAULT 'info',
            Title TEXT,
            Detail TEXT,
            Time TEXT,
            Read INTEGER DEFAULT 0
        );
    ''')

    count = c.execute("SELECT COUNT(*) FROM EMPLOYEE").fetchone()[0]
    if count > 0:
        conn.commit()
        conn.close()
        return

    # Employees (Soncmp = company, Worktype = normal/expert)
    employees = [
        ('E001', 'Zhang Wei', 'Technology', 'FastRepair HQ', 'expert'),
        ('E002', 'Li Na', 'Operations', 'FastRepair HQ', 'normal'),
        ('E003', 'Wang Qiang', 'Projects', 'FastRepair East', 'normal'),
        ('E004', 'Liu Fang', 'Quality', 'FastRepair East', 'normal'),
        ('E005', 'Chen Ming', 'Technology', 'FastRepair HQ', 'expert'),
    ]
    c.executemany("INSERT INTO EMPLOYEE VALUES (?,?,?,?,?)", employees)

    logins = [
        ('E001', '123456'), ('E002', '123456'), ('E003', '123456'),
        ('E004', '123456'), ('E005', 'admin123'),
    ]
    c.executemany("INSERT INTO LOGIN VALUES (?,?)", logins)

    # Tools: cheap (<200$) and expensive (>=200$)
    # Borrow: 0=available, -1=pending, 1=borrowed
    tools = [
        ('T001', 'Electric Drill', 'cheap', 'FastRepair HQ', 85, 1, 0),
        ('T002', 'Angle Grinder', 'cheap', 'FastRepair HQ', 120, 1, 0),
        ('T003', 'Multimeter', 'cheap', 'FastRepair East', 95, 1, 1),
        ('T004', 'Hydraulic Jack', 'expensive', 'FastRepair HQ', 4500, 1, 0),
        ('T005', 'Welding Machine', 'expensive', 'FastRepair HQ', 8900, 1, 0),
        ('T006', 'Wrench Set', 'cheap', 'FastRepair East', 75, 1, 0),
        ('T007', 'Laser Rangefinder', 'expensive', 'FastRepair HQ', 2100, 1, 1),
        ('T008', 'Air Compressor', 'expensive', 'FastRepair East', 15600, 1, 0),
        ('T009', 'Safety Helmet', 'cheap', 'FastRepair HQ', 25, 1, 0),
        ('T010', 'Thermal Imager', 'expensive', 'FastRepair HQ', 12800, 1, 1),
        ('T011', 'Electric Screwdriver', 'cheap', 'FastRepair HQ', 65, 1, 0),
        ('T012', 'Fiber Fusion Splicer', 'expensive', 'FastRepair East', 28000, 1, 0),
        ('T013', 'Insulated Gloves', 'cheap', 'FastRepair HQ', 35, 1, 0),
        ('T014', 'Digital Oscilloscope', 'expensive', 'FastRepair HQ', 6500, 1, 0),
        ('T015', 'Cutting Machine', 'cheap', 'FastRepair East', 110, 1, 0),
    ]
    c.executemany("INSERT INTO TOOL VALUES (?,?,?,?,?,?,?)", tools)

    # Lend records
    lends = [
        ('L001', '2024-06-01 10:00:00', 'E002', 'T003'),
        ('L002', '2024-06-03 14:30:00', 'E003', 'T007'),
        ('L003', '2024-05-28 09:15:00', 'E005', 'T010'),
    ]
    c.executemany("INSERT INTO LEND VALUES (?,?,?,?)", lends)

    # Pending requests (LENDTMP)
    pending = [
        ('E001', '2024-06-10 08:00:00', 'T004'),
        ('E003', '2024-06-09 10:30:00', 'T008'),
    ]
    c.executemany("INSERT INTO LENDTMP VALUES (?,?,?)", pending)

    # Notifications
    notifs = [
        ('N001', 'warning', 'Overdue Tool', 'Multimeter borrowed by Li Na is overdue', '10 min ago', 0),
        ('N002', 'info', 'New Request', 'Zhang Wei requests Hydraulic Jack', '30 min ago', 0),
        ('N003', 'success', 'Tool Returned', 'Angle Grinder has been returned', '2 hours ago', 1),
    ]
    c.executemany("INSERT INTO NOTIFICATIONS VALUES (?,?,?,?,?,?)", notifs)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized with seed data at {DB_PATH}")


# ============================================================
# Helpers
# ============================================================

def row_to_dict(row):
    return None if row is None else dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]


def ok(data=None, msg="Success", code=200):
    r = {"success": True, "message": msg}
    if data is not None:
        r["data"] = data
    return jsonify(r), code


def fail(msg="Failed", code=400):
    return jsonify({"success": False, "message": msg}), code


# ============================================================
# Auth (simple token-based)
# ============================================================

_token_store = {}


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if token not in _token_store:
            return fail("Unauthorized", 401)
        g.current_user = _token_store[token]
        return fn(*args, **kwargs)
    return wrapper


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not data:
        return fail("No credentials", 401)

    eid = data.get('username', '').strip()
    pwd = data.get('password', '').strip()

    if not eid or not pwd:
        return fail("Empty fields", 401)

    db = get_db()
    row = db.execute(
        "SELECT e.EID, e.Name, e.Depart, e.Soncmp, e.Worktype "
        "FROM EMPLOYEE e JOIN LOGIN l ON e.EID = l.EID "
        "WHERE l.EID = ? AND l.Password = ?",
        (eid, pwd)
    ).fetchone()

    if not row:
        return fail("Wrong credentials", 401)

    user = row_to_dict(row)
    raw = f"{eid}:{datetime.datetime.now().timestamp()}:tws"
    token = hashlib.md5(raw.encode()).hexdigest()
    _token_store[token] = user

    return ok({"token": token, "user": user}, "Login successful")


@app.route('/api/auth/me', methods=['GET'])
@auth_required
def me():
    return ok(g.current_user)


# ============================================================
# Dashboard
# ============================================================

@app.route('/api/dashboard/stats', methods=['GET'])
@auth_required
def stats():
    db = get_db()
    return ok({
        'total_tools': db.execute("SELECT COUNT(*) as c FROM TOOL").fetchone()['c'],
        'available': db.execute("SELECT COUNT(*) as c FROM TOOL WHERE Borrow = 0").fetchone()['c'],
        'borrowed': db.execute("SELECT COUNT(*) as c FROM TOOL WHERE Borrow = 1").fetchone()['c'],
        'pending': db.execute("SELECT COUNT(*) as c FROM TOOL WHERE Borrow = -1").fetchone()['c'],
        'damaged': db.execute("SELECT COUNT(*) as c FROM TOOL WHERE Good = 0").fetchone()['c'],
        'total_employees': db.execute("SELECT COUNT(*) as c FROM EMPLOYEE").fetchone()['c'],
        'active_lends': db.execute("SELECT COUNT(*) as c FROM LEND").fetchone()['c'],
        'pending_requests': db.execute("SELECT COUNT(*) as c FROM LENDTMP").fetchone()['c'],
    })


# ============================================================
# Tools
# ============================================================

@app.route('/api/tools', methods=['GET'])
@auth_required
def list_tools():
    db = get_db()
    status = request.args.get('status', 'all')
    company = request.args.get('company', '').strip()
    q = request.args.get('q', '').strip()

    sql = "SELECT * FROM TOOL WHERE 1=1"
    params = []

    if status == 'available':
        sql += " AND Borrow = 0"
    elif status == 'borrowed':
        sql += " AND Borrow = 1"
    elif status == 'pending':
        sql += " AND Borrow = -1"

    if company:
        sql += " AND Soncmp = ?"
        params.append(company)

    if q:
        like = f"%{q}%"
        sql += " AND (Name LIKE ? OR TID LIKE ?)"
        params.extend([like, like])

    sql += " ORDER BY TID"
    tools = rows_to_list(db.execute(sql, params).fetchall())

    # Format status for frontend
    for t in tools:
        t['Good'] = 'Normal' if t['Good'] else 'Damaged'
        status_map = {0: 'available', 1: 'borrowed', -1: 'pending'}
        t['Borrow'] = status_map.get(t.get('Borrow', 0), 'available')

    return ok(tools)


@app.route('/api/tools', methods=['POST'])
@auth_required
def create_tool():
    data = request.get_json(silent=True) or {}
    tid = data.get('tid', '') or f"T{random.randint(100, 999)}"
    price = float(data.get('price', 0))
    tooltype = 'expensive' if price >= 200 else 'cheap'

    try:
        db = get_db()
        db.execute(
            "INSERT INTO TOOL (TID, Name, Tooltype, Soncmp, Price, Good, Borrow) VALUES (?,?,?,?,?,?,0)",
            (tid, data.get('name', ''), tooltype,
             data.get('soncmp', ''), price, data.get('good', 1))
        )
        db.commit()
        return ok({"tid": tid}, "Tool created", 201)
    except Exception as e:
        return fail(f"Create failed: {e}")


@app.route('/api/tools/<tid>', methods=['PUT'])
@auth_required
def update_tool(tid):
    data = request.get_json(silent=True)
    if not data:
        return fail("No data")

    allowed = {'name': 'Name', 'tooltype': 'Tooltype', 'soncmp': 'Soncmp',
               'price': 'Price', 'good': 'Good', 'borrow': 'Borrow'}
    sets, params = [], []
    for k, col in allowed.items():
        if k in data and data[k] is not None:
            sets.append(f"{col} = ?")
            params.append(data[k])

    if not sets:
        return fail("No fields to update")

    params.append(tid)
    db = get_db()
    db.execute(f"UPDATE TOOL SET {', '.join(sets)} WHERE TID = ?", params)
    db.commit()

    if db.total_changes == 0:
        return fail("Tool not found", 404)
    return ok(msg="Tool updated")


@app.route('/api/tools/<tid>', methods=['DELETE'])
@auth_required
def delete_tool(tid):
    db = get_db()
    db.execute("DELETE FROM TOOL WHERE TID = ?", (tid,))
    db.commit()
    if db.total_changes == 0:
        return fail("Tool not found", 404)
    return ok(msg="Tool deleted")


# ============================================================
# Employees
# ============================================================

@app.route('/api/employees', methods=['GET'])
@auth_required
def list_employees():
    db = get_db()
    company = request.args.get('company', '').strip()

    sql = "SELECT EID, Name, Depart, Soncmp, Worktype FROM EMPLOYEE WHERE 1=1"
    params = []
    if company:
        sql += " AND Soncmp = ?"
        params.append(company)
    sql += " ORDER BY EID"

    return ok(rows_to_list(db.execute(sql, params).fetchall()))


@app.route('/api/employees', methods=['POST'])
@auth_required
def create_employee():
    data = request.get_json(silent=True) or {}
    eid = data.get('eid', '') or f"E{random.randint(100, 999)}"

    try:
        db = get_db()
        db.execute(
            "INSERT INTO EMPLOYEE (EID, Name, Depart, Soncmp, Worktype) VALUES (?,?,?,?,?)",
            (eid, data.get('name', ''), data.get('depart', ''),
             data.get('soncmp', ''), data.get('worktype', 'normal'))
        )
        db.execute(
            "INSERT INTO LOGIN (EID, Password) VALUES (?,?)",
            (eid, data.get('password', '123456'))
        )
        db.commit()
        return ok({"eid": eid}, "Employee created", 201)
    except Exception as e:
        return fail(f"Create failed: {e}")


@app.route('/api/employees/<eid>', methods=['PUT'])
@auth_required
def update_employee(eid):
    data = request.get_json(silent=True)
    if not data:
        return fail("No data")

    allowed = {'name': 'Name', 'depart': 'Depart', 'soncmp': 'Soncmp', 'worktype': 'Worktype'}
    sets, params = [], []
    for k, col in allowed.items():
        if k in data and data[k] is not None:
            sets.append(f"{col} = ?")
            params.append(data[k])

    if not sets:
        return fail("No fields")

    params.append(eid)
    db = get_db()
    db.execute(f"UPDATE EMPLOYEE SET {', '.join(sets)} WHERE EID = ?", params)
    db.commit()
    if db.total_changes == 0:
        return fail("Not found", 404)
    return ok(msg="Employee updated")


@app.route('/api/employees/<eid>', methods=['DELETE'])
@auth_required
def delete_employee(eid):
    db = get_db()
    db.execute("DELETE FROM EMPLOYEE WHERE EID = ?", (eid,))
    db.commit()
    if db.total_changes == 0:
        return fail("Not found", 404)
    return ok(msg="Employee deleted")


# ============================================================
# Lending
# ============================================================

@app.route('/api/lending', methods=['GET'])
@auth_required
def list_lending():
    db = get_db()
    sql = """
        SELECT l.LID, l.Lendtime, l.EID, l.TID,
               e.Name AS EmployeeName, e.Soncmp, e.Depart,
               t.Name AS ToolName, t.Tooltype, t.Price
        FROM LEND l
        JOIN EMPLOYEE e ON l.EID = e.EID
        JOIN TOOL t ON l.TID = t.TID
        ORDER BY l.Lendtime DESC
    """
    records = rows_to_list(db.execute(sql).fetchall())
    for r in records:
        if r.get('Lendtime') and hasattr(r['Lendtime'], 'strftime'):
            r['Lendtime'] = r['Lendtime'].strftime('%Y-%m-%d %H:%M:%S')
    return ok(records)


@app.route('/api/lending', methods=['POST'])
@auth_required
def create_lending():
    """Direct lending by admin (bypasses approval)."""
    current = g.current_user
    data = request.get_json(silent=True) or {}
    eid = data.get('eid', '')
    tid = data.get('tid', '')

    if not eid or not tid:
        return fail("Missing eid or tid")

    db = get_db()

    # Permission check: normal employees can only borrow from their own company
    user = db.execute("SELECT * FROM EMPLOYEE WHERE EID = ?", (eid,)).fetchone()
    if not user:
        return fail("Employee not found")

    tool = db.execute("SELECT * FROM TOOL WHERE TID = ?", (tid,)).fetchone()
    if not tool:
        return fail("Tool not found")

    # Permission: expert can borrow any, normal only same company
    if user['Worktype'] == 'normal' and user['Soncmp'] != tool['Soncmp']:
        return fail("Normal employees can only borrow tools from their own company")

    if tool['Good'] == 0:
        return fail("Tool is damaged")
    if tool['Borrow'] != 0:
        return fail("Tool is not available")

    lid = f"L{random.randint(1000, 9999)}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    db.execute("INSERT INTO LEND (LID, Lendtime, EID, TID) VALUES (?,?,?,?)", (lid, now, eid, tid))
    db.execute("UPDATE TOOL SET Borrow = 1 WHERE TID = ?", (tid,))
    db.commit()

    # If expensive tool, run warehouse simulation
    if tool['Price'] >= 200:
        threading.Thread(target=run_tws_simulation,
                         args=(user['Name'], tool['Name']), daemon=True).start()

    return ok({"lid": lid, "lendtime": now, "eid": eid, "tid": tid}, "Borrowed", 201)


@app.route('/api/lending/<lid>/return', methods=['PUT'])
@auth_required
def return_tool(lid):
    db = get_db()
    rec = db.execute("SELECT TID FROM LEND WHERE LID = ?", (lid,)).fetchone()
    if not rec:
        return fail("Record not found", 404)

    db.execute("DELETE FROM LEND WHERE LID = ?", (lid,))
    db.execute("UPDATE TOOL SET Borrow = 0 WHERE TID = ?", (rec['TID'],))
    db.commit()
    return ok(msg="Tool returned")


# ============================================================
# Requests (LENDTMP - approval workflow)
# ============================================================

@app.route('/api/requests', methods=['GET'])
@auth_required
def list_requests():
    db = get_db()
    sql = """
        SELECT lt.EID, lt.Lendtime, lt.TID,
               e.Name AS EmployeeName, e.Depart, e.Soncmp,
               t.Name AS ToolName, t.Tooltype, t.Price
        FROM LENDTMP lt
        JOIN EMPLOYEE e ON lt.EID = e.EID
        JOIN TOOL t ON lt.TID = t.TID
        ORDER BY lt.Lendtime DESC
    """
    reqs = rows_to_list(db.execute(sql).fetchall())
    for r in reqs:
        if r.get('Lendtime') and hasattr(r['Lendtime'], 'strftime'):
            r['Lendtime'] = r['Lendtime'].strftime('%Y-%m-%d %H:%M:%S')
    return ok(reqs)


@app.route('/api/requests', methods=['POST'])
@auth_required
def create_request():
    """Employee submits a tool request."""
    current_eid = g.current_user['EID']
    data = request.get_json(silent=True) or {}
    tid = data.get('tid', '')

    if not tid:
        return fail("Missing tid")

    db = get_db()

    # Check tool exists and is available
    tool = db.execute("SELECT * FROM TOOL WHERE TID = ? AND Good = 1 AND Borrow = 0", (tid,)).fetchone()
    if not tool:
        return fail("Tool not available or damaged")

    # Permission check
    user = db.execute("SELECT * FROM EMPLOYEE WHERE EID = ?", (current_eid,)).fetchone()
    if user['Worktype'] == 'normal' and user['Soncmp'] != tool['Soncmp']:
        return fail("You can only request tools from your own company")

    # Mark as pending
    db.execute("UPDATE TOOL SET Borrow = -1 WHERE TID = ?", (tid,))

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    db.execute("INSERT INTO LENDTMP (EID, Lendtime, TID) VALUES (?,?,?)", (current_eid, now, tid))
    db.commit()

    return ok({"eid": current_eid, "tid": tid, "lendtime": now}, "Request submitted", 201)


@app.route('/api/requests/<eid>/<tid>/approve', methods=['PUT'])
@auth_required
def approve_request(eid, tid):
    """Admin approves a tool request."""
    db = get_db()

    req = db.execute("SELECT * FROM LENDTMP WHERE EID = ? AND TID = ?", (eid, tid)).fetchone()
    if not req:
        return fail("Request not found", 404)

    tool = db.execute("SELECT * FROM TOOL WHERE TID = ?", (tid,)).fetchone()
    user = db.execute("SELECT * FROM EMPLOYEE WHERE EID = ?", (eid,)).fetchone()

    lid = f"L{random.randint(1000, 9999)}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    db.execute("INSERT INTO LEND (LID, Lendtime, EID, TID) VALUES (?,?,?,?)", (lid, now, eid, tid))
    db.execute("UPDATE TOOL SET Borrow = 1 WHERE TID = ?", (tid,))
    db.execute("DELETE FROM LENDTMP WHERE EID = ? AND TID = ?", (eid, tid))
    db.commit()

    # For expensive tools, run warehouse simulation (robots + conveyor)
    if tool['Price'] >= 200:
        threading.Thread(target=run_tws_simulation,
                         args=(user['Name'], tool['Name']), daemon=True).start()
        msg = "Request approved, warehouse robots dispatched"
    else:
        msg = "Request approved (cheap tool, direct pickup)"

    return ok({"lid": lid, "eid": eid, "tid": tid, "lendtime": now}, msg)


@app.route('/api/requests/<eid>/<tid>/reject', methods=['PUT'])
@auth_required
def reject_request(eid, tid):
    db = get_db()
    db.execute("UPDATE TOOL SET Borrow = 0 WHERE TID = ?", (tid,))
    db.execute("DELETE FROM LENDTMP WHERE EID = ? AND TID = ?", (eid, tid))
    db.commit()
    return ok(msg="Request rejected")


# ============================================================
# Notifications
# ============================================================

@app.route('/api/notifications', methods=['GET'])
@auth_required
def list_notifications():
    return ok(rows_to_list(get_db().execute("SELECT * FROM NOTIFICATIONS ORDER BY NID DESC").fetchall()))


@app.route('/api/notifications/<nid>/read', methods=['PUT'])
@auth_required
def mark_read(nid):
    get_db().execute("UPDATE NOTIFICATIONS SET Read = 1 WHERE NID = ?", (nid,))
    get_db().commit()
    return ok(msg="Marked as read")


# ============================================================
# Start
# ============================================================

if __name__ == '__main__':
    init_db()
    print(f"[OK] Database: {DB_PATH}")
    print(f"[OK] TWS Warehouse Simulation: {get_tws() is not None}")
    print(f"[START] http://localhost:8900/api/")
    print(f"    Accounts: E001-E005 / 123456 (admin/admin123 for E005)")
    print(f"    Normal employees borrow only their department tools")
    print(f"    Experts can borrow any tool")
    print(f"    Expensive tools (>=200$) trigger warehouse robot simulation")
    app.run(debug=True, port=8900, host='0.0.0.0')
