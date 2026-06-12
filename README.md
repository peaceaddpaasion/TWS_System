# TWS 工具仓库管理系统 (Tool Warehouse System)

> 西安电子科技大学 · 软件体系结构课程大作业  
> ETMS（员工与工具信息管理系统）— 前后端分离架构重构版

## 📋 项目概述

本项目实现了一个智能工具仓库管理系统（TWS），支持工具的借还管理、员工信息维护、借用申请审批等核心功能。系统模拟了管理员通过控制电脑调度机器人抓取工具并放置到传送带的完整流程。

## 🏗️ 目录结构

```
TWS_System/
├── legacy/                     # 原始版本（Flask + Jinja2 模板渲染）
│   ├── web.py                  # 后端主程序（Flask）
│   ├── main.py                 # TWS 模拟主程序
│   ├── computer.py             # 控制电脑模块
│   ├── robot.py                # 机器人模块
│   ├── person.py               # 人员模块（User/Admin）
│   ├── product.py              # 工具产品模块
│   ├── converger.py            # 传送带模块
│   ├── create_database.sql     # 数据库建表脚本
│   ├── templates/              # Jinja2 HTML 模板
│   ├── static/js/              # 前端 JS 资源
│   └── result_img/             # 原系统运行截图
│
├── refactored/                 # 重构版本（前后端分离架构）
│   ├── frontend/               # 现代化 SPA 前端
│   │   ├── index.html          # SPA 主入口
│   │   ├── style.css           # 深色工业风样式表
│   │   └── app.js              # 应用逻辑（路由/状态管理/CRUD）
│   │
│   └── backend/                # RESTful API 后端
│       └── api.py              # Flask RESTful API（Blueprint 架构）
│
├── docs/                       # 文档目录
├── 体系结构大作业.pdf           # 课程大作业要求文档
├── .gitignore
└── README.md
```

## 🚀 重构创新点

### 1. 软件体系架构改造

| 维度 | 原始版本 | 重构版本 |
|------|---------|---------|
| **架构模式** | Flask + Jinja2 模板渲染（前后端耦合） | 前后端分离 SPA + RESTful API |
| **认证方式** | 服务端 Session + Cookie | JWT 无状态令牌认证 |
| **代码组织** | 单文件 355 行 | Blueprint 模块化（6 个 Blueprint） |
| **URL 设计** | 不规范命名 | RESTful 规范 `/api/resources` |
| **SQL 安全** | 字符串拼接（SQL 注入风险） | 参数化查询 |
| **跨域支持** | 无 | CORS 配置 |
| **错误处理** | try/except 吞异常 | 统一 JSON 错误格式 |

### 2. 前端优化

| 特性 | 说明 |
|------|------|
| **SPA 单页应用** | Hash 路由，无页面刷新，流畅体验 |
| **深色工业风主题** | Glass Morphism 毛玻璃效果，专业仓库管理视觉 |
| **数据可视化仪表盘** | CSS 柱状图 + 环形图 + 动画计数器 |
| **响应式设计** | 三断点适配（480px / 768px / 1024px） |
| **动画交互** | 粒子背景、视图切换过渡、按钮涟漪效果 |
| **组件化设计** | 独立视图渲染函数，可复用组件 |

## 🛠️ 技术栈

### 原始版本
- **后端**: Python Flask + PyMySQL
- **前端**: HTML + CSS + JavaScript + Jinja2
- **数据库**: MySQL
- **模拟**: Python threading（机器人/传送带多线程模拟）

### 重构版本
- **后端**: Python Flask + Flask-CORS + Flask-JWT-Extended + PyMySQL
- **前端**: Vanilla JavaScript SPA（无框架依赖）
- **样式**: CSS Custom Properties + Google Fonts + Glass Morphism
- **数据库**: MySQL（表结构不变）

## 📦 快速开始

### 原始版本

```bash
# 1. 安装依赖
pip install flask pymysql

# 2. 创建数据库
mysql -u root -p < legacy/create_database.sql

# 3. 修改数据库连接信息
# 编辑 legacy/web.py 中的 connect_database() 函数

# 4. 启动服务
cd legacy
python web.py
# 访问 http://localhost:8900
```

### 重构版本 - 前端预览

```bash
# 直接打开即可，无需构建工具
cd refactored/frontend
# 用浏览器打开 index.html
# 或使用 http.server:
python -m http.server 8080
# 访问 http://localhost:8080
```

### 重构版本 - 后端 API

```bash
# 1. 安装依赖
pip install flask flask-cors flask-jwt-extended pymysql

# 2. 配置数据库连接
# 编辑 refactored/backend/api.py 中的 DB_CONFIG

# 3. 启动 API 服务
cd refactored/backend
python api.py
# API 地址 http://localhost:8900/api/
```

## 📸 系统截图

- 登录页面：深色工业风 + 粒子动画背景
- 仪表盘：KPI 统计卡片 + 数据可视化图表 + 活动日志
- 工具管理：完整 CRUD + 搜索过滤
- 员工管理：信息维护 + 权限管理
- 借用管理：借还流程 + 逾期检测
- 审批中心：申请审批工作流

## 👥 团队成员

（请在此处填写团队成员信息）

## 📄 许可证

本项目仅用于课程学习与交流。
