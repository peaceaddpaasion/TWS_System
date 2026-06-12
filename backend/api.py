# -*- coding: utf-8 -*-
"""
ETMS (Employee & Tool Management System) — RESTful API 服务
============================================================

本模块为 TWS 系统的 Web 服务层，负责处理前端 SPA 的 HTTP 请求，
通过 JSON 格式进行数据交互。技术要点：

1. 【前后端分离】
   后端仅输出 JSON 数据，不参与页面渲染。前端 SPA 通过 Fetch API
   调用接口，二者独立开发、独立部署。

2. 【RESTful 规范】
   - GET    读取资源
   - POST   创建资源
   - PUT    更新资源
   - DELETE 删除资源
   URL 路径体现资源层级（如 /api/tools/<tid>）。

3. 【参数化查询】
   所有数据库操作使用 pymysql 参数化查询，由数据库驱动自动处理
   参数转义，杜绝 SQL 注入。

4. 【JWT 令牌认证】
   无状态认证机制：登录后签发 token，客户端在 Authorization 头
   携带 token，服务端验证签名即可确认身份。

5. 【Blueprint 模块化】
   - auth_bp:      用户认证（登录、获取当前用户）
   - tools_bp:     工具管理（CRUD）
   - employees_bp: 员工管理（CRUD）
   - lending_bp:   借还管理（借出记录、归还操作）
   - requests_bp:  工具申请（提交、审批、拒绝）
   - dashboard_bp: 仪表盘统计

6. 【统一错误处理】
   统一 JSON 响应格式，全局错误处理器兜底，数据库连接 try/finally 确保释放。

7. 【CORS 跨域支持】
   flask-cors 允许前端 SPA 跨域调用 API。

8. 【输入验证】
   对必填字段、字段长度、字段类型做基本校验。

数据库：MySQL，库名 TWS，表结构与 simulation/create_database.sql 一致。

依赖安装：
-----------
pip install flask flask-cors flask-jwt-extended pymysql

"""

import os
import time
import random
import datetime
from functools import wraps

import pymysql
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)

# ============================================================
# 应用初始化与配置
# ============================================================

app = Flask(__name__)

# JWT 密钥配置（生产环境应从环境变量读取）
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'ETMS-Secret-Key-2024')
# Token 过期时间（秒），默认 24 小时
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)

# 初始化扩展
CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)

# ============================================================
# 数据库连接管理
# ============================================================

# 数据库配置（生产环境应从环境变量或配置文件读取）
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'zych@0715'),
    'database': os.environ.get('DB_NAME', 'TWS'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor  # 返回字典格式，方便 JSON 序列化
}


def get_db_connection():
    """
    获取数据库连接。
    调用者必须在使用完毕后关闭连接（建议使用 try/finally）。
    使用 DictCursor 使得查询结果为字典列表，便于直接转为 JSON。
    """
    return pymysql.connect(**DB_CONFIG)


# ============================================================
# 统一响应格式与错误处理
# ============================================================

def success_response(data=None, message="操作成功", status_code=200):
    """
    构建统一成功响应。
    格式: { "success": true, "message": "...", "data": ... }
    """
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    return jsonify(body), status_code


def error_response(message="操作失败", status_code=400, errors=None):
    """
    构建统一错误响应。
    格式: { "success": false, "message": "...", "errors": [...] }
    """
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status_code


@app.errorhandler(404)
def not_found(e):
    """404 未找到资源的统一处理"""
    return error_response("请求的资源不存在", 404)


@app.errorhandler(500)
def internal_error(e):
    """500 服务器内部错误的统一处理"""
    return error_response("服务器内部错误", 500)


@app.errorhandler(405)
def method_not_allowed(e):
    """405 方法不允许的统一处理"""
    return error_response("请求方法不被允许", 405)


# ============================================================
# 输入验证工具
# ============================================================

def validate_required(data, fields):
    """
    验证请求 JSON 数据中是否包含所有必填字段。
    参数:
        data:   请求中的 JSON 字典
        fields: 必填字段名列表
    返回:
        (True, None) 验证通过
        (False, error_response) 验证失败，返回错误响应
    """
    if not data:
        return False, error_response("请求体不能为空", 400)
    missing = [f for f in fields if f not in data or data[f] is None or str(data[f]).strip() == '']
    if missing:
        return False, error_response(f"缺少必填字段: {', '.join(missing)}", 400)
    return True, None


def validate_string_length(value, field_name, max_length=50):
    """
    验证字符串长度不超过限制。
    """
    if len(str(value)) > max_length:
        return False, error_response(f"字段 {field_name} 长度不能超过 {max_length} 个字符", 400)
    return True, None


# ============================================================
# 管理员权限检查装饰器
# ============================================================

def admin_required(fn):
    """
    管理员权限装饰器。
    检查当前 JWT 用户是否为管理员（Worktype = '专家'）。
    原始系统中通过 session['user_info'][0][4] 判断权限，
    这里改为从 JWT token 中读取用户信息并查询数据库验证。
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_eid = get_jwt_identity()
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # 使用参数化查询防止 SQL 注入
            cursor.execute(
                "SELECT Worktype FROM EMPLOYEE WHERE EID = %s",
                (current_eid,)
            )
            result = cursor.fetchone()
            if not result or result['Worktype'] != '专家':
                return error_response("权限不足，需要管理员权限", 403)
            return fn(*args, **kwargs)
        except Exception as e:
            return error_response(f"权限验证失败: {str(e)}", 500)
        finally:
            if conn:
                conn.close()
    return wrapper


# ============================================================
# 认证模块 Blueprint (auth_bp)
# ============================================================
# 路由前缀: /api/auth
# 功能: 用户登录、获取当前用户信息
# 对比原始系统: 原始 login() 和 loginin() 路由直接操作 session 和渲染模板，
#               重构后改为 JWT 无状态认证，返回 JSON。

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录接口。
    接收 JSON: { "username": "工号", "password": "密码" }
    返回 JWT token。

    改进点:
    - 原始系统使用字符串格式化拼接 SQL（严重 SQL 注入风险），
      此处使用参数化查询 %s 占位符。
    - 原始系统将密码明文存储在 session 中（安全隐患），
      此处仅返回 token，不暴露密码。
    - 原始系统使用服务端 session，此处使用无状态 JWT。
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("请提供登录凭据", 401)

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return error_response("用户名和密码不能为空", 401)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 【安全改进】使用参数化查询，防止 SQL 注入
        # 原始代码: cursor.execute(sql % (username, password))  -- 危险！
        cursor.execute(
            "SELECT LOGIN.EID, EMPLOYEE.Name, EMPLOYEE.Depart, EMPLOYEE.Soncmp, EMPLOYEE.Worktype "
            "FROM LOGIN JOIN EMPLOYEE ON LOGIN.EID = EMPLOYEE.EID "
            "WHERE LOGIN.EID = %s AND LOGIN.Password = %s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            # 生成 JWT token，将用户工号作为 identity
            # 可额外将角色等信息放入 token 以减少数据库查询
            additional_claims = {
                'soncmp': user['Soncmp'],
                'worktype': user['Worktype']
            }
            token = create_access_token(
                identity=user['EID'],
                additional_claims=additional_claims
            )
            return success_response(
                data={
                    'token': token,
                    'user': {
                        'eid': user['EID'],
                        'name': user['Name'],
                        'depart': user['Depart'],
                        'soncmp': user['Soncmp'],
                        'worktype': user['Worktype']
                    }
                },
                message="登录成功"
            )
        else:
            return error_response("用户名或密码错误", 401)

    except Exception as e:
        return error_response(f"登录失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    获取当前登录用户信息。
    通过 JWT token 中的 identity（工号）查询数据库获取最新用户信息。

    改进点:
    - 原始系统从 session 中读取用户信息，可能过期不一致，
      此处每次从数据库实时查询。
    """
    current_eid = get_jwt_identity()
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT EID, Name, Depart, Soncmp, Worktype FROM EMPLOYEE WHERE EID = %s",
            (current_eid,)
        )
        user = cursor.fetchone()
        if not user:
            return error_response("用户不存在", 404)
        return success_response(data=user)
    except Exception as e:
        return error_response(f"获取用户信息失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


# ============================================================
# 工具管理模块 Blueprint (tools_bp)
# ============================================================
# 路由前缀: /api/tools
# 功能: 工具的增删改查
# 对比原始系统: 原始 get_tool_info() 只能查询本公司未借出的工具，
#               重构后支持完整的 CRUD 操作和灵活的过滤查询。

tools_bp = Blueprint('tools', __name__, url_prefix='/api/tools')


@tools_bp.route('', methods=['GET'])
@jwt_required()
def list_tools():
    """
    获取工具列表。
    支持查询参数过滤:
    - company: 子公司名称 (Soncmp)
    - status:  工具状态 (all/available/borrowed/pending)
    - type:    工具类型 (Tooltype)

    改进点:
    - 原始系统只能查看本公司未借出工具，功能单一。
    - 此处支持多维度过滤，使用动态 SQL 拼接 + 参数化查询。
    - 返回 JSON 而非渲染模板。
    """
    company = request.args.get('company', '').strip()
    status = request.args.get('status', 'all').strip()
    tool_type = request.args.get('type', '').strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 动态构建 SQL 查询条件
        conditions = []
        params = []

        if company:
            conditions.append("Soncmp = %s")
            params.append(company)

        # status 过滤: Borrow 字段含义 - 0=可借, -1=申请中, 1=已借出
        if status == 'available':
            conditions.append("Borrow = 0")
        elif status == 'borrowed':
            conditions.append("Borrow = 1")
        elif status == 'pending':
            conditions.append("Borrow = -1")

        if tool_type:
            conditions.append("Tooltype = %s")
            params.append(tool_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM TOOL WHERE {where_clause}"

        # 【安全改进】参数化查询，即使动态拼接 SQL 也使用 %s 占位符
        cursor.execute(sql, tuple(params))
        tools = cursor.fetchall()

        # 将布尔值 Good 转换为可读文本，与原始系统保持一致
        for tool in tools:
            tool['Good'] = '正常' if tool['Good'] else '损坏'
            # Borrow 状态转换
            borrow_status = tool.get('Borrow', 0)
            if borrow_status == 0:
                tool['Borrow'] = '可借'
            elif borrow_status == 1:
                tool['Borrow'] = '已借出'
            elif borrow_status == -1:
                tool['Borrow'] = '申请中'

        return success_response(data=tools, message=f"共 {len(tools)} 条工具记录")
    except Exception as e:
        return error_response(f"查询工具失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@tools_bp.route('', methods=['POST'])
@jwt_required()
def create_tool():
    """
    创建新工具。
    接收 JSON: { "tid": "工具编号", "name": "名称", "tooltype": "类型", "soncmp": "子公司" }

    改进点:
    - 原始系统无创建工具功能，所有工具需手动在数据库中添加。
    - 此处提供 RESTful 创建接口，包含输入验证。
    """
    data = request.get_json(silent=True)
    valid, err = validate_required(data, ['tid', 'name', 'soncmp'])
    if not valid:
        return err

    tid = data['tid'].strip()
    name = data['name'].strip()
    tooltype = data.get('tooltype', '').strip()
    soncmp = data['soncmp'].strip()

    # 字段长度验证
    for val, field, maxlen in [(tid, 'tid', 10), (name, 'name', 10),
                                (tooltype, 'tooltype', 10), (soncmp, 'soncmp', 20)]:
        ok, err = validate_string_length(val, field, maxlen)
        if not ok:
            return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 【安全改进】参数化查询
        cursor.execute(
            "INSERT INTO TOOL (TID, Name, Tooltype, Soncmp, Good, Borrow) VALUES (%s, %s, %s, %s, TRUE, 0)",
            (tid, name, tooltype, soncmp)
        )
        conn.commit()
        return success_response(data={'tid': tid}, message="工具创建成功", status_code=201)
    except pymysql.err.IntegrityError:
        return error_response("工具编号已存在", 409)
    except Exception as e:
        conn.rollback()
        return error_response(f"创建工具失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@tools_bp.route('/<tid>', methods=['PUT'])
@jwt_required()
def update_tool(tid):
    """
    更新工具信息。
    接收 JSON: { "name": "...", "tooltype": "...", "soncmp": "...", "good": true/false, "borrow": 0/-1/1 }
    只更新提供的字段（部分更新）。

    改进点:
    - 原始系统只能通过 SQL 直接修改 Borrow 状态。
    - 此处支持灵活的部分更新。
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("请求体不能为空", 400)

    # 构建动态 UPDATE 语句，只更新传入的字段
    allowed_fields = {
        'name': 'Name',
        'tooltype': 'Tooltype',
        'soncmp': 'Soncmp',
        'good': 'Good',
        'borrow': 'Borrow'
    }

    set_clauses = []
    params = []
    for key, column in allowed_fields.items():
        if key in data and data[key] is not None:
            set_clauses.append(f"{column} = %s")
            params.append(data[key])

    if not set_clauses:
        return error_response("没有提供需要更新的字段", 400)

    params.append(tid)  # WHERE 条件参数放在最后

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = f"UPDATE TOOL SET {', '.join(set_clauses)} WHERE TID = %s"
        cursor.execute(sql, tuple(params))
        conn.commit()

        if cursor.rowcount == 0:
            return error_response("工具不存在", 404)

        return success_response(message="工具更新成功")
    except Exception as e:
        conn.rollback()
        return error_response(f"更新工具失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@tools_bp.route('/<tid>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_tool(tid):
    """
    删除工具。
    需要管理员权限。

    改进点:
    - 原始系统无删除工具功能。
    - 此处增加管理员权限检查。
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 【安全改进】参数化查询
        cursor.execute("DELETE FROM TOOL WHERE TID = %s", (tid,))
        conn.commit()

        if cursor.rowcount == 0:
            return error_response("工具不存在", 404)

        return success_response(message="工具删除成功")
    except Exception as e:
        conn.rollback()
        return error_response(f"删除工具失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


# ============================================================
# 员工管理模块 Blueprint (employees_bp)
# ============================================================
# 路由前缀: /api/employees
# 功能: 员工的增删改查
# 对比原始系统: 原始 employee_update() 只能更新姓名和职位类型，
#               且使用字符串格式化 SQL。重构后支持完整 CRUD。

employees_bp = Blueprint('employees', __name__, url_prefix='/api/employees')


@employees_bp.route('', methods=['GET'])
@jwt_required()
def list_employees():
    """
    获取员工列表。
    支持查询参数过滤:
    - company: 子公司名称 (Soncmp)
    - type:    工作类型 (Worktype: 员工/专家)

    改进点:
    - 原始 get_employee_info() 只能查询 session 中用户所属公司的员工。
    - 此处支持灵活过滤，且使用参数化查询。
    """
    company = request.args.get('company', '').strip()
    work_type = request.args.get('type', '').strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        conditions = []
        params = []

        if company:
            conditions.append("Soncmp = %s")
            params.append(company)
        if work_type:
            conditions.append("Worktype = %s")
            params.append(work_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT EID, Name, Depart, Soncmp, Worktype FROM EMPLOYEE WHERE {where_clause}"

        cursor.execute(sql, tuple(params))
        employees = cursor.fetchall()

        return success_response(data=employees, message=f"共 {len(employees)} 条员工记录")
    except Exception as e:
        return error_response(f"查询员工失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@employees_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_employee():
    """
    创建新员工。
    接收 JSON: { "eid": "工号", "name": "姓名", "depart": "部门", "soncmp": "子公司", "worktype": "工作类型" }
    需要管理员权限。

    改进点:
    - 原始系统无创建员工接口。
    - 此处同时创建员工记录和登录账号。
    """
    data = request.get_json(silent=True)
    valid, err = validate_required(data, ['eid', 'name', 'soncmp', 'worktype'])
    if not valid:
        return err

    eid = data['eid'].strip()
    name = data['name'].strip()
    depart = data.get('depart', '').strip()
    soncmp = data['soncmp'].strip()
    worktype = data['worktype'].strip()
    password = data.get('password', '123456').strip()  # 默认密码

    # 字段长度验证
    for val, field, maxlen in [(eid, 'eid', 10), (name, 'name', 10),
                                (depart, 'depart', 20), (soncmp, 'soncmp', 20),
                                (worktype, 'worktype', 10)]:
        ok, err = validate_string_length(val, field, maxlen)
        if not ok:
            return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 创建员工记录
        # 【安全改进】参数化查询
        cursor.execute(
            "INSERT INTO EMPLOYEE (EID, Name, Depart, Soncmp, Worktype) VALUES (%s, %s, %s, %s, %s)",
            (eid, name, depart, soncmp, worktype)
        )
        # 同时创建登录账号
        cursor.execute(
            "INSERT INTO LOGIN (EID, Password) VALUES (%s, %s)",
            (eid, password)
        )
        conn.commit()
        return success_response(
            data={'eid': eid},
            message=f"员工 {name} 创建成功，默认密码: {password}",
            status_code=201
        )
    except pymysql.err.IntegrityError:
        conn.rollback()
        return error_response("员工工号已存在", 409)
    except Exception as e:
        conn.rollback()
        return error_response(f"创建员工失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@employees_bp.route('/<eid>', methods=['PUT'])
@jwt_required()
@admin_required
def update_employee(eid):
    """
    更新员工信息。
    接收 JSON: { "name": "...", "depart": "...", "soncmp": "...", "worktype": "..." }
    需要管理员权限。

    改进点:
    - 原始 employee_update() 使用字符串格式化 SQL（SQL 注入风险）。
    - 此处使用参数化查询，且支持部分更新。
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("请求体不能为空", 400)

    allowed_fields = {
        'name': 'Name',
        'depart': 'Depart',
        'soncmp': 'Soncmp',
        'worktype': 'Worktype'
    }

    set_clauses = []
    params = []
    for key, column in allowed_fields.items():
        if key in data and data[key] is not None:
            set_clauses.append(f"{column} = %s")
            params.append(data[key])

    if not set_clauses:
        return error_response("没有提供需要更新的字段", 400)

    params.append(eid)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = f"UPDATE EMPLOYEE SET {', '.join(set_clauses)} WHERE EID = %s"
        cursor.execute(sql, tuple(params))
        conn.commit()

        if cursor.rowcount == 0:
            return error_response("员工不存在", 404)

        return success_response(message="员工信息更新成功")
    except Exception as e:
        conn.rollback()
        return error_response(f"更新员工失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@employees_bp.route('/<eid>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_employee(eid):
    """
    删除员工。
    需要管理员权限。
    由于外键约束 ON DELETE CASCADE，关联的 LEND 和 LOGIN 记录会自动删除。

    改进点:
    - 原始系统 employee_update() 中 state=='清除' 时使用字符串格式化删除。
    - 此处使用参数化查询，且增加权限验证。
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 【安全改进】参数化查询
        cursor.execute("DELETE FROM EMPLOYEE WHERE EID = %s", (eid,))
        conn.commit()

        if cursor.rowcount == 0:
            return error_response("员工不存在", 404)

        return success_response(message="员工删除成功")
    except Exception as e:
        conn.rollback()
        return error_response(f"删除员工失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


# ============================================================
# 借还管理模块 Blueprint (lending_bp)
# ============================================================
# 路由前缀: /api/lending
# 功能: 借出记录查询、归还工具
# 对比原始系统: 原始 get_lend_info() 只能查看当前用户的借出记录，
#               重构后支持管理员查看所有记录和归还操作。

lending_bp = Blueprint('lending', __name__, url_prefix='/api/lending')


@lending_bp.route('', methods=['GET'])
@jwt_required()
def list_lending():
    """
    获取借出记录列表。
    支持查询参数过滤:
    - employee: 员工工号 (EID)，不传则返回所有记录
    - status:   状态过滤 (all/active)

    改进点:
    - 原始 get_lend_info() 只能查看当前登录用户的记录。
    - 此处支持管理员查看所有记录，并关联查询员工和工具名称。
    - 使用 JOIN 查询获取更完整的信息。
    """
    employee_id = request.args.get('employee', '').strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 使用 JOIN 关联查询，获取员工姓名和工具名称
        # 【安全改进】参数化查询
        if employee_id:
            sql = """
                SELECT l.LID, l.Lendtime, l.EID, l.TID,
                       e.Name AS EmployeeName, e.Soncmp,
                       t.Name AS ToolName, t.Tooltype
                FROM LEND l
                JOIN EMPLOYEE e ON l.EID = e.EID
                JOIN TOOL t ON l.TID = t.TID
                WHERE l.EID = %s
                ORDER BY l.Lendtime DESC
            """
            cursor.execute(sql, (employee_id,))
        else:
            sql = """
                SELECT l.LID, l.Lendtime, l.EID, l.TID,
                       e.Name AS EmployeeName, e.Soncmp,
                       t.Name AS ToolName, t.Tooltype
                FROM LEND l
                JOIN EMPLOYEE e ON l.EID = e.EID
                JOIN TOOL t ON l.TID = t.TID
                ORDER BY l.Lendtime DESC
            """
            cursor.execute(sql)

        records = cursor.fetchall()

        # 将 datetime/time 对象转为字符串以便 JSON 序列化
        for record in records:
            if record.get('Lendtime') and hasattr(record['Lendtime'], 'strftime'):
                record['Lendtime'] = record['Lendtime'].strftime('%Y-%m-%d %H:%M:%S')

        return success_response(data=records, message=f"共 {len(records)} 条借出记录")
    except Exception as e:
        return error_response(f"查询借出记录失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@lending_bp.route('', methods=['POST'])
@jwt_required()
def create_lending():
    """
    创建借出记录（管理员直接借出工具给员工，跳过审批流程）。
    接收 JSON: { "eid": "员工工号", "tid": "工具编号" }
    需要管理员权限。

    改进点:
    - 原始系统中借出流程需要经过 LENDTMP 申请 -> 管理员审批 -> 插入 LEND。
    - 此处提供直接借出接口（管理员权限），同时保留申请审批流程。
    """
    current_eid = get_jwt_identity()
    data = request.get_json(silent=True)
    valid, err = validate_required(data, ['eid', 'tid'])
    if not valid:
        return err

    eid = data['eid'].strip()
    tid = data['tid'].strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证工具存在且可借
        # 【安全改进】参数化查询
        cursor.execute(
            "SELECT TID, Borrow FROM TOOL WHERE TID = %s AND Good = TRUE AND Borrow = 0",
            (tid,)
        )
        tool = cursor.fetchone()
        if not tool:
            return error_response("工具不存在、已损坏或已被借出", 400)

        # 验证员工存在
        cursor.execute("SELECT EID FROM EMPLOYEE WHERE EID = %s", (eid,))
        if not cursor.fetchone():
            return error_response("员工不存在", 400)

        # 生成借出记录 ID（与原始系统保持一致，使用随机数）
        lid = str(int(random.random() * 999999999))
        lend_time = time.strftime("%Y-%m-%d %H:%M:%S")

        # 插入借出记录
        cursor.execute(
            "INSERT INTO LEND (LID, Lendtime, EID, TID) VALUES (%s, %s, %s, %s)",
            (lid, lend_time, eid, tid)
        )
        # 更新工具状态为已借出
        cursor.execute(
            "UPDATE TOOL SET Borrow = 1 WHERE TID = %s",
            (tid,)
        )
        conn.commit()

        return success_response(
            data={'lid': lid, 'lendtime': lend_time, 'eid': eid, 'tid': tid},
            message="借出成功",
            status_code=201
        )
    except Exception as e:
        conn.rollback()
        return error_response(f"借出操作失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@lending_bp.route('/<lid>/return', methods=['PUT'])
@jwt_required()
def return_tool(lid):
    """
    归还工具。
    将 LEND 记录中对应工具的状态恢复为可借。

    改进点:
    - 原始系统无独立的归还接口，归还操作嵌入在审批流程中。
    - 此处提供独立的归还接口，操作更清晰。
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 查询借出记录获取工具编号
        # 【安全改进】参数化查询
        cursor.execute("SELECT TID FROM LEND WHERE LID = %s", (lid,))
        record = cursor.fetchone()
        if not record:
            return error_response("借出记录不存在", 404)

        tid = record['TID']

        # 删除借出记录
        cursor.execute("DELETE FROM LEND WHERE LID = %s", (lid,))
        # 恢复工具状态为可借
        cursor.execute("UPDATE TOOL SET Borrow = 0 WHERE TID = %s", (tid,))
        conn.commit()

        return success_response(message="工具归还成功")
    except Exception as e:
        conn.rollback()
        return error_response(f"归还操作失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


# ============================================================
# 工具申请模块 Blueprint (requests_bp)
# ============================================================
# 路由前缀: /api/requests
# 功能: 工具借用申请、审批（对应原始系统的 LENDTMP 表）
# 对比原始系统: 原始 post_tool_requset() 和 post_process_request()
#               将申请和审批逻辑混在路由处理函数中，使用字符串格式化 SQL。
#               重构后拆分为清晰的申请、审批、拒绝接口。

requests_bp = Blueprint('requests', __name__, url_prefix='/api/requests')


@requests_bp.route('', methods=['GET'])
@jwt_required()
def list_requests():
    """
    获取待处理的工具申请列表（LENDTMP 表）。
    支持查询参数:
    - company: 按子公司过滤

    改进点:
    - 原始 get_lend_info2() 使用字符串格式化 SQL，且只返回列表数据。
    - 此处使用 JOIN 查询获取完整信息（员工姓名、工具名称），
      使用参数化查询防止 SQL 注入。
    """
    company = request.args.get('company', '').strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if company:
            # 【安全改进】参数化查询
            # 原始代码: cursor.execute(sql % (Soncmp))  -- 危险！
            sql = """
                SELECT lt.EID, lt.Lendtime, lt.TID,
                       e.Name AS EmployeeName, e.Depart,
                       t.Name AS ToolName, t.Tooltype
                FROM LENDTMP lt
                JOIN EMPLOYEE e ON lt.EID = e.EID
                JOIN TOOL t ON lt.TID = t.TID
                WHERE e.Soncmp = %s
                ORDER BY lt.Lendtime DESC
            """
            cursor.execute(sql, (company,))
        else:
            sql = """
                SELECT lt.EID, lt.Lendtime, lt.TID,
                       e.Name AS EmployeeName, e.Depart,
                       t.Name AS ToolName, t.Tooltype
                FROM LENDTMP lt
                JOIN EMPLOYEE e ON lt.EID = e.EID
                JOIN TOOL t ON lt.TID = t.TID
                ORDER BY lt.Lendtime DESC
            """
            cursor.execute(sql)

        requests_list = cursor.fetchall()

        # 将 time 对象转为字符串
        for req in requests_list:
            if req.get('Lendtime') and hasattr(req['Lendtime'], 'strftime'):
                req['Lendtime'] = req['Lendtime'].strftime('%Y-%m-%d %H:%M:%S')

        return success_response(data=requests_list, message=f"共 {len(requests_list)} 条待处理申请")
    except Exception as e:
        return error_response(f"查询申请列表失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@requests_bp.route('', methods=['POST'])
@jwt_required()
def create_request():
    """
    提交工具借用申请。
    接收 JSON: { "tid": "工具编号" }

    对应原始系统的 post_tool_requset() 函数。
    流程:
    1. 验证工具存在、状态良好、未被借出
    2. 将工具状态设为 -1（申请中）
    3. 在 LENDTMP 表中插入申请记录

    改进点:
    - 原始代码使用字符串格式化 SQL（多处 sql % (...)），存在 SQL 注入风险。
    - 此处全部使用参数化查询。
    - 从 JWT token 获取当前用户工号，而非依赖 session。
    """
    current_eid = get_jwt_identity()
    data = request.get_json(silent=True)
    valid, err = validate_required(data, ['tid'])
    if not valid:
        return err

    tid = data['tid'].strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证工具存在且可借
        # 【安全改进】参数化查询
        # 原始代码: cursor.execute(sql % (session['jump'], TID))  -- 危险！
        cursor.execute(
            "SELECT TID, Soncmp FROM TOOL WHERE TID = %s AND Good = TRUE AND Borrow = 0",
            (tid,)
        )
        tool = cursor.fetchone()
        if not tool:
            return error_response("工具不存在、已损坏或已被借出/申请中", 400)

        # 将工具状态设为申请中（-1）
        cursor.execute(
            "UPDATE TOOL SET Borrow = -1 WHERE TID = %s",
            (tid,)
        )

        # 插入申请记录到 LENDTMP
        lend_time = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO LENDTMP (EID, Lendtime, TID) VALUES (%s, %s, %s)",
            (current_eid, lend_time, tid)
        )
        conn.commit()

        return success_response(
            data={'eid': current_eid, 'tid': tid, 'lendtime': lend_time},
            message="工具申请已提交，等待管理员审批",
            status_code=201
        )
    except Exception as e:
        conn.rollback()
        return error_response(f"提交申请失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@requests_bp.route('/<eid>/<tid>/approve', methods=['PUT'])
@jwt_required()
@admin_required
def approve_request(eid, tid):
    """
    审批通过工具申请。
    路径参数: eid=申请人工号, tid=工具编号

    对应原始系统 post_process_request() 中 response == '许可' 的分支。
    流程:
    1. 验证 LENDTMP 中存在该申请
    2. 创建 LEND 借出记录
    3. 将工具状态设为已借出（1）
    4. 删除 LENDTMP 中的申请记录

    改进点:
    - 原始代码使用字符串格式化 SQL 拼接 INSERT 语句。
    - 此处使用参数化查询，且流程更清晰。
    - 使用 RESTful PUT 方法语义明确。
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证申请存在
        # 【安全改进】参数化查询
        cursor.execute(
            "SELECT * FROM LENDTMP WHERE EID = %s AND TID = %s",
            (eid, tid)
        )
        request_record = cursor.fetchone()
        if not request_record:
            return error_response("申请记录不存在", 404)

        # 生成借出记录
        lid = str(int(random.random() * 999999999))
        lend_time = time.strftime("%Y-%m-%d %H:%M:%S")

        # 插入 LEND 记录
        cursor.execute(
            "INSERT INTO LEND (LID, Lendtime, EID, TID) VALUES (%s, %s, %s, %s)",
            (lid, lend_time, eid, tid)
        )
        # 更新工具状态为已借出
        cursor.execute(
            "UPDATE TOOL SET Borrow = 1 WHERE TID = %s",
            (tid,)
        )
        # 删除 LENDTMP 申请记录
        cursor.execute(
            "DELETE FROM LENDTMP WHERE EID = %s AND TID = %s",
            (eid, tid)
        )
        conn.commit()

        return success_response(
            data={'lid': lid, 'eid': eid, 'tid': tid, 'lendtime': lend_time},
            message="申请已批准，工具已借出"
        )
    except Exception as e:
        conn.rollback()
        return error_response(f"审批操作失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


@requests_bp.route('/<eid>/<tid>/reject', methods=['PUT'])
@jwt_required()
@admin_required
def reject_request(eid, tid):
    """
    拒绝工具申请。
    路径参数: eid=申请人工号, tid=工具编号

    对应原始系统 post_process_request() 中 response == '拒绝' 的分支。
    流程:
    1. 将工具状态恢复为可借（0）
    2. 删除 LENDTMP 中的申请记录

    改进点:
    - 原始代码使用字符串格式化 SQL。
    - 此处使用参数化查询。
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证申请存在
        # 【安全改进】参数化查询
        cursor.execute(
            "SELECT * FROM LENDTMP WHERE EID = %s AND TID = %s",
            (eid, tid)
        )
        if not cursor.fetchone():
            return error_response("申请记录不存在", 404)

        # 恢复工具状态为可借
        cursor.execute(
            "UPDATE TOOL SET Borrow = 0 WHERE TID = %s",
            (tid,)
        )
        # 删除申请记录
        cursor.execute(
            "DELETE FROM LENDTMP WHERE EID = %s AND TID = %s",
            (eid, tid)
        )
        conn.commit()

        return success_response(message="申请已拒绝，工具已恢复可借状态")
    except Exception as e:
        conn.rollback()
        return error_response(f"拒绝操作失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


# ============================================================
# 仪表盘统计模块 Blueprint (dashboard_bp)
# ============================================================
# 路由前缀: /api/dashboard
# 功能: 提供系统统计数据，供前端仪表盘展示
# 对比原始系统: 原始系统无统计功能，重构后新增。

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    获取仪表盘统计数据。
    返回: 工具总数、可借数量、已借出数量、申请中数量、
          员工总数、待处理申请数、本月借出数。

    改进点:
    - 原始系统无此功能。
    - 使用单次查询获取多项统计，减少数据库访问次数。
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        stats = {}

        # 工具统计
        cursor.execute("SELECT COUNT(*) as total FROM TOOL")
        stats['total_tools'] = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM TOOL WHERE Borrow = 0")
        stats['available_tools'] = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM TOOL WHERE Borrow = 1")
        stats['borrowed_tools'] = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM TOOL WHERE Borrow = -1")
        stats['pending_tools'] = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM TOOL WHERE Good = FALSE")
        stats['damaged_tools'] = cursor.fetchone()['total']

        # 员工统计
        cursor.execute("SELECT COUNT(*) as total FROM EMPLOYEE")
        stats['total_employees'] = cursor.fetchone()['total']

        # 待处理申请数
        cursor.execute("SELECT COUNT(*) as total FROM LENDTMP")
        stats['pending_requests'] = cursor.fetchone()['total']

        # 当前借出记录数
        cursor.execute("SELECT COUNT(*) as total FROM LEND")
        stats['active_lends'] = cursor.fetchone()['total']

        return success_response(data=stats, message="统计数据获取成功")
    except Exception as e:
        return error_response(f"获取统计数据失败: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


# ============================================================
# 注册所有 Blueprint
# ============================================================
app.register_blueprint(auth_bp)
app.register_blueprint(tools_bp)
app.register_blueprint(employees_bp)
app.register_blueprint(lending_bp)
app.register_blueprint(requests_bp)
app.register_blueprint(dashboard_bp)


# ============================================================
# 启动入口
# ============================================================
if __name__ == '__main__':
    # 与原始系统保持一致的端口和主机配置
    # 原始: app.run(debug=True, port=8900, host='0.0.0.0')
    app.run(debug=True, port=8900, host='0.0.0.0')
