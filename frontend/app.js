/* ============================================
   TWS - Tool Warehouse System
   Vanilla JS SPA with SQLite persistence
   ============================================ */

// ========== API 配置 ==========
const API_BASE = 'http://localhost:8900/api';

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('tws_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  });
  const body = await res.json();
  if (!body.success) throw new Error(body.message || '请求失败');
  return body.data;
}

// ========== 应用状态管理 ==========
const AppState = {
  currentUser: null,
  currentView: 'login',
  notifications: [],
  sidebarOpen: true,
  notificationPanelOpen: false,

  // 数据存储
  tools: [],
  employees: [],
  lendingRecords: [],
  borrowRequests: [],

  // 搜索/过滤
  searchQuery: '',
  filterStatus: 'all',

  // 分页
  currentPage: 1,
  pageSize: 10,
};

// ========== 从 API 加载数据 ==========
async function fetchAllData() {
  try {
    const [tools, employees, lending, requests, notifs] = await Promise.all([
      api('/tools'),
      api('/employees'),
      api('/lending'),
      api('/requests'),
      api('/notifications'),
    ]);

    AppState.tools = (tools || []).map(t => ({
      id: t.TID, name: t.Name, category: t.Tooltype || '',
      brand: '', model: '',
      status: t.Borrow || 'available', location: t.Soncmp || '',
      purchaseDate: '', price: t.Price || 0,
      quantity: 1, available: t.Borrow === 'available' ? 1 : 0, image: '',
      soncmp: t.Soncmp || '', good: t.Good || 'Normal',
    }));

    AppState.employees = (employees || []).map(e => ({
      id: e.EID, name: e.Name, department: e.Depart || '',
      position: e.Worktype || '', phone: '', email: '',
      status: 'active', joinDate: '', avatar: '', soncmp: e.Soncmp || '',
    }));

    AppState.lendingRecords = (lending || []).map(r => ({
      id: r.LID, toolId: r.TID, toolName: r.ToolName || '',
      employeeId: r.EID, employeeName: r.EmployeeName || '',
      borrowDate: r.Lendtime || '', returnDate: '',
      expectedReturn: '', status: 'active', purpose: '',
    }));

    AppState.borrowRequests = (requests || []).map(r => ({
      id: r.TID, toolId: r.TID, toolName: r.ToolName || '',
      employeeId: r.EID, employeeName: r.EmployeeName || '',
      requestDate: r.Lendtime || '', reason: '',
      status: 'pending', quantity: 1,
    }));

    AppState.notifications = (notifs || []).map(n => ({
      id: n.NID, type: n.Type || 'info', title: n.Title || '',
      desc: n.Detail || '', time: n.Time || '', read: !!n.Read,
    }));

    return true;
  } catch (e) {
    console.error('Failed to load data:', e);
    return false;
  }
}

// ========== 工具函数 ==========
function generateId(prefix) {
  const num = Math.floor(Math.random() * 9000) + 1000;
  return `${prefix}${num}`;
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return `${formatDate(dateStr)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function getStatusText(status) {
  const map = {
    available: '可用', borrowed: '借出', maintenance: '维护中', retired: '已报废',
    active: '在用', inactive: '停用', pending: '待审批', approved: '已批准',
    rejected: '已拒绝', returned: '已归还', overdue: '已逾期',
  };
  return map[status] || status;
}

function getStatusBadgeClass(status) {
  const map = {
    available: 'badge-green', borrowed: 'badge-amber', maintenance: 'badge-red',
    retired: 'badge-gray', active: 'badge-green', inactive: 'badge-gray',
    pending: 'badge-amber', approved: 'badge-green', rejected: 'badge-red',
    returned: 'badge-blue', overdue: 'badge-red',
  };
  return map[status] || 'badge-gray';
}

function getStatusDotClass(status) {
  const map = {
    available: 'available', borrowed: 'borrowed', maintenance: 'maintenance', retired: 'retired',
  };
  return map[status] || '';
}

function getInitials(name) {
  return name ? name.charAt(0) : '?';
}

// ========== Toast 通知系统 ==========
function showToast(type, title, message, duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = {
    success: '\u2714',
    error: '\u2716',
    warning: '\u26A0',
    info: '\u2139',
  };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.classList.add('removing'); setTimeout(() => this.parentElement.remove(), 300)">&times;</button>
    <div class="toast-progress" style="animation-duration: ${duration}ms"></div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 300);
    }
  }, duration);
}

// ========== 按钮涟漪效果 ==========
function addRippleEffect(e) {
  const btn = e.currentTarget;
  const rect = btn.getBoundingClientRect();
  const ripple = document.createElement('span');
  const size = Math.max(rect.width, rect.height);
  ripple.className = 'ripple';
  ripple.style.width = ripple.style.height = `${size}px`;
  ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
}

// ========== 数字动画计数器 ==========
function animateCounter(element, target, duration = 1000) {
  const start = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(start + (target - start) * eased);
    element.textContent = current;
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = target;
    }
  }

  requestAnimationFrame(update);
}

// ========== 路由系统 ==========
function navigate(hash) {
  window.location.hash = hash;
}

function handleRoute() {
  const hash = window.location.hash.slice(1) || 'login';

  if (hash === 'login') {
    showLoginView();
    return;
  }

  if (!AppState.currentUser) {
    navigate('login');
    return;
  }

  AppState.currentView = hash;

  // 隐藏登录页，显示应用
  document.getElementById('login-page').style.display = 'none';
  document.getElementById('app-layout').classList.add('active');

  // 更新侧边栏激活状态
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.view === hash);
  });

  // 更新顶部标题
  const titleMap = {
    dashboard: '仪表盘',
    tools: '工具管理',
    employees: '员工管理',
    lending: '借用管理',
    requests: '借用申请',
  };
  const topbarTitle = document.getElementById('topbar-title');
  if (topbarTitle) topbarTitle.textContent = titleMap[hash] || '';

  // 渲染视图
  const content = document.getElementById('page-content');
  if (!content) return;

  content.className = 'page-content view-enter';

  switch (hash) {
    case 'dashboard': renderDashboard(content); break;
    case 'tools': renderTools(content); break;
    case 'employees': renderEmployees(content); break;
    case 'lending': renderLending(content); break;
    case 'requests': renderRequests(content); break;
    default: renderDashboard(content); break;
  }

  // 关闭移动端侧边栏
  closeMobileSidebar();
}

// ========== 登录视图 ==========
function showLoginView() {
  document.getElementById('login-page').style.display = 'flex';
  document.getElementById('app-layout').classList.remove('active');
  AppState.currentView = 'login';
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value.trim();

  if (!username || !password) {
    showToast('warning', '提示', '请输入用户名和密码');
    return;
  }

  try {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });

    localStorage.setItem('tws_token', data.token);
    AppState.currentUser = data.user;

    // 登录成功后加载所有数据
    await fetchAllData();

    showToast('success', '登录成功', `欢迎回来，${AppState.currentUser.name}`);
    updateSidebarUser();
    navigate('dashboard');
  } catch (err) {
    showToast('error', '登录失败', err.message || '用户名或密码错误');
  }
}

function handleLogout() {
  AppState.currentUser = null;
  localStorage.removeItem('tws_token');
  showToast('info', '已退出', '您已安全退出系统');
  navigate('login');
}

// ========== 仪表盘视图 ==========
function renderDashboard(container) {
  const totalTools = AppState.tools.length;
  const borrowedTools = AppState.tools.filter(t => t.status === 'borrowed').length;
  const pendingRequests = AppState.borrowRequests.filter(r => r.status === 'pending').length;
  const activeEmployees = AppState.employees.filter(e => e.status === 'active').length;

  // 工具类别统计
  const categories = {};
  AppState.tools.forEach(t => {
    categories[t.category] = (categories[t.category] || 0) + t.quantity;
  });

  // 工具状态统计
  const statusStats = { available: 0, borrowed: 0, maintenance: 0 };
  AppState.tools.forEach(t => {
    if (statusStats[t.status] !== undefined) statusStats[t.status]++;
  });

  // 最近活动
  const recentActivities = [
    { icon: '\uD83D\uDD04', iconBg: 'rgba(45,156,219,0.12)', text: '<strong>张伟</strong> 借用了 <strong>万用表</strong>', time: '10分钟前' },
    { icon: '\u2705', iconBg: 'rgba(39,174,96,0.12)', text: '<strong>孙磊</strong> 归还了 <strong>角磨机</strong>', time: '2小时前' },
    { icon: '\uD83D\uDCCB', iconBg: 'rgba(242,153,74,0.12)', text: '<strong>张伟</strong> 提交了借用申请', time: '30分钟前' },
    { icon: '\uD83D\uDEE0\uFE0F', iconBg: 'rgba(235,87,87,0.12)', text: '<strong>焊接机</strong> 进入维护状态', time: '1天前' },
    { icon: '\uD83D\uDC65', iconBg: 'rgba(39,174,96,0.12)', text: '新员工 <strong>黄磊</strong> 入职', time: '1天前' },
  ];

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2>仪表盘</h2>
        <p>系统运行概览与数据统计</p>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-ghost" onclick="showToast('info','刷新','数据已更新')">
          &#x21bb; 刷新数据
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card blue">
        <div class="stat-card-icon">&#x1F527;</div>
        <div class="stat-card-value" data-count="${totalTools}">0</div>
        <div class="stat-card-label">工具总数</div>
        <div class="stat-card-trend up">&#x2191; 12% 较上月</div>
      </div>
      <div class="stat-card amber">
        <div class="stat-card-icon">&#x1F4E6;</div>
        <div class="stat-card-value" data-count="${borrowedTools}">0</div>
        <div class="stat-card-label">借出工具</div>
        <div class="stat-card-trend down">&#x2193; 5% 较上月</div>
      </div>
      <div class="stat-card red">
        <div class="stat-card-icon">&#x1F4CC;</div>
        <div class="stat-card-value" data-count="${pendingRequests}">0</div>
        <div class="stat-card-label">待审批请求</div>
        <div class="stat-card-trend up">&#x2191; 2 新增</div>
      </div>
      <div class="stat-card emerald">
        <div class="stat-card-icon">&#x1F465;</div>
        <div class="stat-card-value" data-count="${activeEmployees}">0</div>
        <div class="stat-card-label">在岗员工</div>
        <div class="stat-card-trend up">&#x2191; 1 新入职</div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3>&#x1F4CA; 工具类别分布</h3>
        <div class="bar-chart" id="bar-chart"></div>
      </div>
      <div class="chart-card">
        <h3>&#x1F3AF; 工具状态概览</h3>
        <div class="donut-chart-container">
          <div class="donut-chart" id="donut-chart">
            <div class="donut-center">
              <div class="donut-center-value">${totalTools}</div>
              <div class="donut-center-label">总计</div>
            </div>
          </div>
          <div class="donut-legend">
            <div class="legend-item">
              <span class="legend-dot" style="background:var(--emerald)"></span>
              <span class="legend-label">可用</span>
              <span class="legend-value">${statusStats.available}</span>
            </div>
            <div class="legend-item">
              <span class="legend-dot" style="background:var(--amber)"></span>
              <span class="legend-label">借出</span>
              <span class="legend-value">${statusStats.borrowed}</span>
            </div>
            <div class="legend-item">
              <span class="legend-dot" style="background:var(--danger)"></span>
              <span class="legend-label">维护中</span>
              <span class="legend-value">${statusStats.maintenance}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <div class="quick-action-card" onclick="navigate('tools')">
        <div class="quick-action-icon">&#x2795;</div>
        <div class="quick-action-info">
          <h4>登记新工具</h4>
          <p>添加新的工具到仓库</p>
        </div>
      </div>
      <div class="quick-action-card" onclick="navigate('lending')">
        <div class="quick-action-icon">&#x1F504;</div>
        <div class="quick-action-info">
          <h4>工具借还</h4>
          <p>处理工具借用与归还</p>
        </div>
      </div>
      <div class="quick-action-card" onclick="navigate('requests')">
        <div class="quick-action-icon">&#x1F4CB;</div>
        <div class="quick-action-info">
          <h4>审批请求</h4>
          <p>查看待审批的借用申请</p>
        </div>
      </div>
      <div class="quick-action-card" onclick="navigate('employees')">
        <div class="quick-action-icon">&#x1F465;</div>
        <div class="quick-action-info">
          <h4>员工管理</h4>
          <p>管理员工信息与权限</p>
        </div>
      </div>
    </div>

    <!-- 最近活动 -->
    <div class="chart-card" style="animation-delay:0.4s">
      <h3>&#x1F552; 最近活动</h3>
      <ul class="activity-list">
        ${recentActivities.map(a => `
          <li class="activity-item">
            <div class="activity-icon" style="background:${a.iconBg}">${a.icon}</div>
            <div class="activity-content">
              <div class="activity-text">${a.text}</div>
              <div class="activity-time">${a.time}</div>
            </div>
          </li>
        `).join('')}
      </ul>
    </div>
  `;

  // 动画计数器
  setTimeout(() => {
    document.querySelectorAll('[data-count]').forEach(el => {
      animateCounter(el, parseInt(el.dataset.count));
    });
  }, 200);

  // 渲染柱状图
  renderBarChart(categories);
  // 渲染环形图
  renderDonutChart(statusStats);
}

function renderBarChart(categories) {
  const chart = document.getElementById('bar-chart');
  if (!chart) return;

  const entries = Object.entries(categories);
  const maxVal = Math.max(...entries.map(e => e[1]));
  const colors = ['#2d9cdb', '#27ae60', '#f2994a', '#eb5757', '#9b59b6', '#e67e22', '#1abc9c', '#3498db'];

  chart.innerHTML = entries.map(([name, value], i) => {
    const heightPercent = Math.max((value / maxVal) * 100, 5);
    const color = colors[i % colors.length];
    return `
      <div class="bar-group">
        <div class="bar" data-value="${value}" style="height:0%;background:${color}"></div>
        <div class="bar-label">${name}</div>
      </div>
    `;
  }).join('');

  // 动画显示柱状图
  setTimeout(() => {
    chart.querySelectorAll('.bar').forEach((bar, i) => {
      const entries2 = Object.entries(categories);
      const maxVal2 = Math.max(...entries2.map(e => e[1]));
      const heightPercent = Math.max((entries2[i][1] / maxVal2) * 100, 5);
      bar.style.height = heightPercent + '%';
    });
  }, 300);
}

function renderDonutChart(stats) {
  const chart = document.getElementById('donut-chart');
  if (!chart) return;

  const total = stats.available + stats.borrowed + stats.maintenance;
  if (total === 0) return;

  const availableDeg = (stats.available / total) * 360;
  const borrowedDeg = (stats.borrowed / total) * 360;

  chart.style.background = `conic-gradient(
    var(--emerald) 0deg ${availableDeg}deg,
    var(--amber) ${availableDeg}deg ${availableDeg + borrowedDeg}deg,
    var(--danger) ${availableDeg + borrowedDeg}deg 360deg
  )`;
}

// ========== 工具管理视图 ==========
function renderTools(container) {
  const filteredTools = getFilteredTools();

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2>工具管理</h2>
        <p>管理仓库中的所有工具设备</p>
      </div>
      <button class="btn btn-primary" onclick="openToolModal()">
        &#x2795; 添加工具
      </button>
    </div>

    <div class="data-table-wrapper">
      <div class="table-toolbar">
        <div class="table-toolbar-left">
          <div class="search-box">
            <span class="search-box-icon">&#x1F50D;</span>
            <input type="text" placeholder="搜索工具名称、编号..." value="${AppState.searchQuery}" oninput="handleToolSearch(this.value)" />
          </div>
          <select class="form-select" style="width:auto;padding:8px 36px 8px 12px;font-size:0.8125rem;" onchange="handleToolFilter(this.value)">
            <option value="all" ${AppState.filterStatus === 'all' ? 'selected' : ''}>全部状态</option>
            <option value="available" ${AppState.filterStatus === 'available' ? 'selected' : ''}>可用</option>
            <option value="borrowed" ${AppState.filterStatus === 'borrowed' ? 'selected' : ''}>借出</option>
            <option value="maintenance" ${AppState.filterStatus === 'maintenance' ? 'selected' : ''}>维护中</option>
          </select>
        </div>
        <div class="table-toolbar-right">
          <span class="text-muted" style="font-size:0.8125rem;">共 ${filteredTools.length} 件工具</span>
        </div>
      </div>

      ${filteredTools.length > 0 ? `
        <table class="data-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>工具名称</th>
              <th>类别</th>
              <th>品牌/型号</th>
              <th>库存/可用</th>
              <th>存放位置</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${filteredTools.map(tool => `
              <tr>
                <td><span class="tag">${tool.id}</span></td>
                <td class="tool-name">
                  <span class="status-dot ${getStatusDotClass(tool.status)}"></span>
                  ${tool.name}
                </td>
                <td>${tool.category}</td>
                <td>${tool.brand} ${tool.model}</td>
                <td>
                  <span style="color:var(--text-primary);font-weight:500;">${tool.available}</span>
                  <span style="color:var(--text-muted);">/ ${tool.quantity}</span>
                </td>
                <td><span class="tag">${tool.location}</span></td>
                <td><span class="badge ${getStatusBadgeClass(tool.status)}">${getStatusText(tool.status)}</span></td>
                <td>
                  <div style="display:flex;gap:4px;">
                    <button class="btn btn-ghost btn-sm" onclick="openToolModal('${tool.id}')" title="编辑">&#x270F;</button>
                    <button class="btn btn-ghost btn-sm" onclick="deleteTool('${tool.id}')" title="删除" style="color:var(--danger);">&#x1F5D1;</button>
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div class="pagination">
          <span>显示 ${Math.min(1, filteredTools.length)}-${Math.min(AppState.pageSize, filteredTools.length)} / 共 ${filteredTools.length} 条</span>
          <div class="pagination-btns">
            <button class="pagination-btn" disabled>&#x25C0;</button>
            <button class="pagination-btn active">1</button>
            <button class="pagination-btn" disabled>&#x25B6;</button>
          </div>
        </div>
      ` : `
        <div class="empty-state">
          <div class="empty-state-icon">&#x1F50D;</div>
          <h3>未找到匹配的工具</h3>
          <p>尝试修改搜索条件或清除筛选</p>
        </div>
      `}
    </div>
  `;
}

function getFilteredTools() {
  let tools = [...AppState.tools];
  if (AppState.searchQuery) {
    const q = AppState.searchQuery.toLowerCase();
    tools = tools.filter(t =>
      t.name.toLowerCase().includes(q) ||
      t.id.toLowerCase().includes(q) ||
      t.category.toLowerCase().includes(q) ||
      t.brand.toLowerCase().includes(q)
    );
  }
  if (AppState.filterStatus !== 'all') {
    tools = tools.filter(t => t.status === AppState.filterStatus);
  }
  return tools;
}

function handleToolSearch(query) {
  AppState.searchQuery = query;
  renderTools(document.getElementById('page-content'));
}

function handleToolFilter(status) {
  AppState.filterStatus = status;
  renderTools(document.getElementById('page-content'));
}

function openToolModal(toolId) {
  const tool = toolId ? AppState.tools.find(t => t.id === toolId) : null;
  const isEdit = !!tool;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>${isEdit ? '编辑工具' : '添加新工具'}</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">工具名称 *</label>
            <input class="form-input" id="modal-tool-name" value="${tool ? tool.name : ''}" placeholder="请输入工具名称" />
          </div>
          <div class="form-group">
            <label class="form-label">工具类别 *</label>
            <select class="form-select" id="modal-tool-category">
              <option value="">请选择类别</option>
              <option ${tool && tool.category === '电动工具' ? 'selected' : ''}>电动工具</option>
              <option ${tool && tool.category === '手动工具' ? 'selected' : ''}>手动工具</option>
              <option ${tool && tool.category === '测量仪器' ? 'selected' : ''}>测量仪器</option>
              <option ${tool && tool.category === '起重设备' ? 'selected' : ''}>起重设备</option>
              <option ${tool && tool.category === '焊接设备' ? 'selected' : ''}>焊接设备</option>
              <option ${tool && tool.category === '气动设备' ? 'selected' : ''}>气动设备</option>
              <option ${tool && tool.category === '安全防护' ? 'selected' : ''}>安全防护</option>
              <option ${tool && tool.category === '检测设备' ? 'selected' : ''}>检测设备</option>
              <option ${tool && tool.category === '通信设备' ? 'selected' : ''}>通信设备</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">品牌</label>
            <input class="form-input" id="modal-tool-brand" value="${tool ? tool.brand : ''}" placeholder="请输入品牌" />
          </div>
          <div class="form-group">
            <label class="form-label">型号</label>
            <input class="form-input" id="modal-tool-model" value="${tool ? tool.model : ''}" placeholder="请输入型号" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">库存数量 *</label>
            <input class="form-input" type="number" id="modal-tool-quantity" value="${tool ? tool.quantity : 1}" min="1" />
          </div>
          <div class="form-group">
            <label class="form-label">可用数量</label>
            <input class="form-input" type="number" id="modal-tool-available" value="${tool ? tool.available : (tool ? tool.quantity : 1)}" min="0" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">存放位置</label>
            <input class="form-input" id="modal-tool-location" value="${tool ? tool.location : ''}" placeholder="例如: A-01-03" />
          </div>
          <div class="form-group">
            <label class="form-label">单价 (元)</label>
            <input class="form-input" type="number" id="modal-tool-price" value="${tool ? tool.price : ''}" placeholder="请输入单价" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">状态</label>
          <select class="form-select" id="modal-tool-status">
            <option value="available" ${tool && tool.status === 'available' ? 'selected' : ''}>可用</option>
            <option value="borrowed" ${tool && tool.status === 'borrowed' ? 'selected' : ''}>借出</option>
            <option value="maintenance" ${tool && tool.status === 'maintenance' ? 'selected' : ''}>维护中</option>
            <option value="retired" ${tool && tool.status === 'retired' ? 'selected' : ''}>已报废</option>
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" onclick="saveTool('${toolId || ''}')">${isEdit ? '保存修改' : '添加工具'}</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
}

async function saveTool(toolId) {
  const name = document.getElementById('modal-tool-name').value.trim();
  const category = document.getElementById('modal-tool-category').value;
  const brand = document.getElementById('modal-tool-brand').value.trim();
  const model = document.getElementById('modal-tool-model').value.trim();
  const quantity = parseInt(document.getElementById('modal-tool-quantity').value) || 0;
  const available = parseInt(document.getElementById('modal-tool-available').value) || 0;
  const location = document.getElementById('modal-tool-location').value.trim();
  const price = parseFloat(document.getElementById('modal-tool-price').value) || 0;
  const status = document.getElementById('modal-tool-status').value;

  if (!name || !category) {
    showToast('warning', '提示', '请填写工具名称和类别');
    return;
  }

  try {
    let result;
    if (toolId) {
      result = await api(`/tools/${toolId}`, {
        method: 'PUT',
        body: JSON.stringify({ name, tooltype: category, soncmp: location, price, good: 1, borrow: status === 'borrowed' ? 1 : 0 }),
      });
      const idx = AppState.tools.findIndex(t => t.id === toolId);
      if (idx >= 0) Object.assign(AppState.tools[idx], { name, category, price, status, location });
      showToast('success', '更新成功', `${name} 信息已更新`);
    } else {
      const payload = { name, price, soncmp: location };
      result = await api('/tools', { method: 'POST', body: JSON.stringify(payload) });
      AppState.tools.unshift({
        id: result.tid, name, category, brand, model, price, status: 'available',
        location, quantity: 1, available: 1, good: 'Normal',
      });
      showToast('success', '添加成功', `${name} 已添加到工具库`);
    }

    document.querySelector('.modal-overlay').remove();
    renderTools(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '操作失败', err.message);
  }
}

function deleteTool(toolId) {
  const tool = AppState.tools.find(t => t.id === toolId);
  if (!tool) return;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  overlay.innerHTML = `
    <div class="modal" style="max-width:400px;">
      <div class="modal-header">
        <h3>确认删除</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="color:var(--text-secondary);">确定要删除工具 <strong style="color:var(--text-primary)">${tool.name}</strong> (${tool.id}) 吗？此操作不可撤销。</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-danger" onclick="confirmDeleteTool('${toolId}')">确认删除</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
}

async function confirmDeleteTool(toolId) {
  const tool = AppState.tools.find(t => t.id === toolId);
  try {
    await api(`/tools/${toolId}`, { method: 'DELETE' });
    AppState.tools = AppState.tools.filter(t => t.id !== toolId);
    document.querySelector('.modal-overlay').remove();
    showToast('success', '删除成功', `${tool ? tool.name : '工具'} 已从库中移除`);
    renderTools(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '删除失败', err.message);
  }
}

// ========== 员工管理视图 ==========
function renderEmployees(container) {
  const filteredEmployees = getFilteredEmployees();

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2>员工管理</h2>
        <p>管理系统中的所有员工信息</p>
      </div>
      <button class="btn btn-primary" onclick="openEmployeeModal()">
        &#x2795; 添加员工
      </button>
    </div>

    <div class="data-table-wrapper">
      <div class="table-toolbar">
        <div class="table-toolbar-left">
          <div class="search-box">
            <span class="search-box-icon">&#x1F50D;</span>
            <input type="text" placeholder="搜索员工姓名、工号..." value="${AppState.searchQuery}" oninput="handleEmployeeSearch(this.value)" />
          </div>
          <select class="form-select" style="width:auto;padding:8px 36px 8px 12px;font-size:0.8125rem;" onchange="handleEmployeeFilter(this.value)">
            <option value="all" ${AppState.filterStatus === 'all' ? 'selected' : ''}>全部状态</option>
            <option value="active" ${AppState.filterStatus === 'active' ? 'selected' : ''}>在岗</option>
            <option value="inactive" ${AppState.filterStatus === 'inactive' ? 'selected' : ''}>停用</option>
          </select>
        </div>
        <div class="table-toolbar-right">
          <span class="text-muted" style="font-size:0.8125rem;">共 ${filteredEmployees.length} 名员工</span>
        </div>
      </div>

      ${filteredEmployees.length > 0 ? `
        <table class="data-table">
          <thead>
            <tr>
              <th>工号</th>
              <th>姓名</th>
              <th>部门</th>
              <th>职位</th>
              <th>联系电话</th>
              <th>入职日期</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            ${filteredEmployees.map(emp => `
              <tr>
                <td><span class="tag">${emp.id}</span></td>
                <td>
                  <div style="display:flex;align-items:center;gap:10px;">
                    <div class="sidebar-avatar" style="width:32px;height:32px;font-size:0.75rem;">${getInitials(emp.name)}</div>
                    <span class="tool-name">${emp.name}</span>
                  </div>
                </td>
                <td>${emp.department}</td>
                <td>${emp.position}</td>
                <td>${emp.phone}</td>
                <td>${formatDate(emp.joinDate)}</td>
                <td><span class="badge ${getStatusBadgeClass(emp.status)}">${getStatusText(emp.status)}</span></td>
                <td>
                  <div style="display:flex;gap:4px;">
                    <button class="btn btn-ghost btn-sm" onclick="openEmployeeModal('${emp.id}')" title="编辑">&#x270F;</button>
                    <button class="btn btn-ghost btn-sm" onclick="deleteEmployee('${emp.id}')" title="删除" style="color:var(--danger);">&#x1F5D1;</button>
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div class="pagination">
          <span>显示 1-${Math.min(AppState.pageSize, filteredEmployees.length)} / 共 ${filteredEmployees.length} 条</span>
          <div class="pagination-btns">
            <button class="pagination-btn" disabled>&#x25C0;</button>
            <button class="pagination-btn active">1</button>
            <button class="pagination-btn" disabled>&#x25B6;</button>
          </div>
        </div>
      ` : `
        <div class="empty-state">
          <div class="empty-state-icon">&#x1F465;</div>
          <h3>未找到匹配的员工</h3>
          <p>尝试修改搜索条件或清除筛选</p>
        </div>
      `}
    </div>
  `;
}

function getFilteredEmployees() {
  let employees = [...AppState.employees];
  if (AppState.searchQuery) {
    const q = AppState.searchQuery.toLowerCase();
    employees = employees.filter(e =>
      e.name.toLowerCase().includes(q) ||
      e.id.toLowerCase().includes(q) ||
      e.department.toLowerCase().includes(q)
    );
  }
  if (AppState.filterStatus !== 'all') {
    employees = employees.filter(e => e.status === AppState.filterStatus);
  }
  return employees;
}

function handleEmployeeSearch(query) {
  AppState.searchQuery = query;
  renderEmployees(document.getElementById('page-content'));
}

function handleEmployeeFilter(status) {
  AppState.filterStatus = status;
  renderEmployees(document.getElementById('page-content'));
}

function openEmployeeModal(empId) {
  const emp = empId ? AppState.employees.find(e => e.id === empId) : null;
  const isEdit = !!emp;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>${isEdit ? '编辑员工' : '添加新员工'}</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">姓名 *</label>
            <input class="form-input" id="modal-emp-name" value="${emp ? emp.name : ''}" placeholder="请输入姓名" />
          </div>
          <div class="form-group">
            <label class="form-label">部门 *</label>
            <select class="form-select" id="modal-emp-department">
              <option value="">请选择部门</option>
              <option ${emp && emp.department === '技术部' ? 'selected' : ''}>技术部</option>
              <option ${emp && emp.department === '运维部' ? 'selected' : ''}>运维部</option>
              <option ${emp && emp.department === '项目部' ? 'selected' : ''}>项目部</option>
              <option ${emp && emp.department === '质检部' ? 'selected' : ''}>质检部</option>
              <option ${emp && emp.department === '行政部' ? 'selected' : ''}>行政部</option>
              <option ${emp && emp.department === '采购部' ? 'selected' : ''}>采购部</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">职位 *</label>
            <input class="form-input" id="modal-emp-position" value="${emp ? emp.position : ''}" placeholder="请输入职位" />
          </div>
          <div class="form-group">
            <label class="form-label">联系电话</label>
            <input class="form-input" id="modal-emp-phone" value="${emp ? emp.phone : ''}" placeholder="请输入联系电话" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">邮箱</label>
          <input class="form-input" id="modal-emp-email" value="${emp ? emp.email : ''}" placeholder="请输入邮箱地址" />
        </div>
        <div class="form-group">
          <label class="form-label">状态</label>
          <select class="form-select" id="modal-emp-status">
            <option value="active" ${emp && emp.status === 'active' ? 'selected' : ''}>在岗</option>
            <option value="inactive" ${emp && emp.status === 'inactive' ? 'selected' : ''}>停用</option>
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" onclick="saveEmployee('${empId || ''}')">${isEdit ? '保存修改' : '添加员工'}</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
}

async function saveEmployee(empId) {
  const name = document.getElementById('modal-emp-name').value.trim();
  const department = document.getElementById('modal-emp-department').value;
  const position = document.getElementById('modal-emp-position').value.trim();
  const phone = document.getElementById('modal-emp-phone').value.trim();
  const email = document.getElementById('modal-emp-email').value.trim();
  const status = document.getElementById('modal-emp-status').value;

  if (!name || !department || !position) {
    showToast('warning', '提示', '请填写姓名、部门和职位');
    return;
  }

  try {
    if (empId) {
      await api(`/employees/${empId}`, {
        method: 'PUT',
        body: JSON.stringify({ name, depart: department, worktype: position }),
      });
      const idx = AppState.employees.findIndex(e => e.id === empId);
      if (idx >= 0) Object.assign(AppState.employees[idx], { name, department, position });
      showToast('success', '更新成功', `${name} 信息已更新`);
    } else {
      const payload = { name, depart: department, worktype: position, soncmp: 'FastRepair HQ' };
      const result = await api('/employees', { method: 'POST', body: JSON.stringify(payload) });
      AppState.employees.unshift({
        id: result.eid, name, department, position, phone, email,
        status: 'active', joinDate: formatDate(new Date().toISOString()), avatar: '',
      });
      showToast('success', '添加成功', `${name} 已添加到员工列表`);
    }

    document.querySelector('.modal-overlay').remove();
    renderEmployees(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '操作失败', err.message);
  }
}

function deleteEmployee(empId) {
  const emp = AppState.employees.find(e => e.id === empId);
  if (!emp) return;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  overlay.innerHTML = `
    <div class="modal" style="max-width:400px;">
      <div class="modal-header">
        <h3>确认删除</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="color:var(--text-secondary);">确定要删除员工 <strong style="color:var(--text-primary)">${emp.name}</strong> (${emp.id}) 吗？此操作不可撤销。</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-danger" onclick="confirmDeleteEmployee('${empId}')">确认删除</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
}

async function confirmDeleteEmployee(empId) {
  const emp = AppState.employees.find(e => e.id === empId);
  try {
    await api(`/employees/${empId}`, { method: 'DELETE' });
    AppState.employees = AppState.employees.filter(e => e.id !== empId);
    document.querySelector('.modal-overlay').remove();
    showToast('success', '删除成功', `${emp ? emp.name : '员工'} 已从系统中移除`);
    renderEmployees(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '删除失败', err.message);
  }
}

// ========== 借用管理视图 ==========
function renderLending(container) {
  const activeRecords = AppState.lendingRecords.filter(r => r.status === 'active');
  const returnedRecords = AppState.lendingRecords.filter(r => r.status === 'returned');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2>借用管理</h2>
        <p>管理工具的借出与归还记录</p>
      </div>
      <button class="btn btn-primary" onclick="openLendingModal()">
        &#x2795; 新建借用
      </button>
    </div>

    <!-- 统计 -->
    <div class="stats-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom:20px;">
      <div class="stat-card amber" style="animation-delay:0s;">
        <div class="stat-card-icon">&#x1F4E6;</div>
        <div class="stat-card-value" style="font-size:1.5rem;">${activeRecords.length}</div>
        <div class="stat-card-label">当前借出</div>
      </div>
      <div class="stat-card blue" style="animation-delay:0.05s;">
        <div class="stat-card-icon">&#x2705;</div>
        <div class="stat-card-value" style="font-size:1.5rem;">${returnedRecords.length}</div>
        <div class="stat-card-label">已归还</div>
      </div>
      <div class="stat-card red" style="animation-delay:0.1s;">
        <div class="stat-card-icon">&#x26A0;</div>
        <div class="stat-card-value" style="font-size:1.5rem;">${activeRecords.filter(r => new Date(r.expectedReturn) < new Date()).length}</div>
        <div class="stat-card-label">逾期未还</div>
      </div>
    </div>

    <div class="tabs">
      <div class="tab active" onclick="switchLendingTab(this, 'active')">当前借出 (${activeRecords.length})</div>
      <div class="tab" onclick="switchLendingTab(this, 'returned')">归还记录 (${returnedRecords.length})</div>
    </div>

    <div id="lending-active-list">
      ${activeRecords.length > 0 ? activeRecords.map(record => {
        const isOverdue = new Date(record.expectedReturn) < new Date();
        return `
          <div class="request-card">
            <div class="request-card-header">
              <div class="request-card-info">
                <div class="request-card-avatar">${getInitials(record.employeeName)}</div>
                <div>
                  <div class="request-card-name">${record.employeeName}</div>
                  <div class="request-card-time">借用日期: ${record.borrowDate}</div>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:8px;">
                <span class="badge ${isOverdue ? 'badge-red' : 'badge-amber'}">${isOverdue ? '已逾期' : '借出中'}</span>
              </div>
            </div>
            <div class="request-card-body">
              <div class="request-card-detail">&#x1F527; 工具: <strong style="color:var(--text-primary)">${record.toolName}</strong> (${record.toolId})</div>
              <div class="request-card-detail">&#x1F4C5; 预期归还: <strong style="color:${isOverdue ? 'var(--danger)' : 'var(--text-primary)'}">${record.expectedReturn}</strong></div>
              <div class="request-card-detail">&#x1F4DD; 用途: ${record.purpose}</div>
            </div>
            <div class="request-card-actions">
              <button class="btn btn-success btn-sm" onclick="returnTool('${record.id}')">&#x2705; 归还</button>
            </div>
          </div>
        `;
      }).join('') : `
        <div class="empty-state">
          <div class="empty-state-icon">&#x1F4E6;</div>
          <h3>暂无借出记录</h3>
          <p>当前没有正在借出的工具</p>
        </div>
      `}
    </div>

    <div id="lending-returned-list" style="display:none;">
      ${returnedRecords.length > 0 ? returnedRecords.map(record => `
        <div class="request-card">
          <div class="request-card-header">
            <div class="request-card-info">
              <div class="request-card-avatar" style="background:linear-gradient(135deg, var(--steel-blue), var(--steel-blue-dark))">${getInitials(record.employeeName)}</div>
              <div>
                <div class="request-card-name">${record.employeeName}</div>
                <div class="request-card-time">借用日期: ${record.borrowDate}</div>
              </div>
            </div>
            <span class="badge badge-blue">已归还</span>
          </div>
          <div class="request-card-body">
            <div class="request-card-detail">&#x1F527; 工具: <strong style="color:var(--text-primary)">${record.toolName}</strong> (${record.toolId})</div>
            <div class="request-card-detail">&#x1F4C5; 归还日期: ${record.returnDate}</div>
            <div class="request-card-detail">&#x1F4DD; 用途: ${record.purpose}</div>
          </div>
        </div>
      `).join('') : `
        <div class="empty-state">
          <div class="empty-state-icon">&#x1F4C1;</div>
          <h3>暂无归还记录</h3>
          <p>还没有已归还的借用记录</p>
        </div>
      `}
    </div>
  `;
}

function switchLendingTab(el, tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('lending-active-list').style.display = tab === 'active' ? 'block' : 'none';
  document.getElementById('lending-returned-list').style.display = tab === 'returned' ? 'block' : 'none';
}

function openLendingModal() {
  const availableTools = AppState.tools.filter(t => t.available > 0 && t.status !== 'maintenance');
  const activeEmployees = AppState.employees.filter(e => e.status === 'active');

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>新建借用</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">选择工具 *</label>
          <select class="form-select" id="modal-lending-tool">
            <option value="">请选择工具</option>
            ${availableTools.map(t => `<option value="${t.id}">${t.name} (${t.id}) - 可用: ${t.available}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">借用人 *</label>
          <select class="form-select" id="modal-lending-employee">
            <option value="">请选择员工</option>
            ${activeEmployees.map(e => `<option value="${e.id}">${e.name} (${e.id}) - ${e.department}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">预期归还日期 *</label>
          <input class="form-input" type="date" id="modal-lending-return" value="${formatDate(new Date(Date.now() + 7 * 86400000).toISOString())}" />
        </div>
        <div class="form-group">
          <label class="form-label">用途说明</label>
          <textarea class="form-textarea" id="modal-lending-purpose" placeholder="请输入借用用途"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" onclick="saveLending()">确认借出</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
}

async function saveLending() {
  const toolId = document.getElementById('modal-lending-tool').value;
  const employeeId = document.getElementById('modal-lending-employee').value;
  const expectedReturn = document.getElementById('modal-lending-return').value;
  const purpose = document.getElementById('modal-lending-purpose').value.trim();

  if (!toolId || !employeeId) {
    showToast('warning', '提示', '请填写完整的借用信息');
    return;
  }

  const tool = AppState.tools.find(t => t.id === toolId);
  const employee = AppState.employees.find(e => e.id === employeeId);
  if (!tool || !employee) return;

  try {
    const result = await api('/lending', {
      method: 'POST',
      body: JSON.stringify({ eid: employeeId, tid: toolId }),
    });

    AppState.lendingRecords.unshift({
      id: result.lid, toolId, toolName: tool.name,
      employeeId, employeeName: employee.name,
      borrowDate: result.lendtime || formatDate(new Date().toISOString()),
      returnDate: '', expectedReturn, status: 'active', purpose: purpose || '',
    });

    if (tool.available > 0) {
      tool.available--;
      if (tool.available === 0) tool.status = 'borrowed';
    }

    document.querySelector('.modal-overlay').remove();
    showToast('success', '借出成功', `${tool.name} 已借给 ${employee.name}`);
    renderLending(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '借出失败', err.message);
  }
}

async function returnTool(recordId) {
  const record = AppState.lendingRecords.find(r => r.id === recordId);
  if (!record) return;

  try {
    await api(`/lending/${recordId}/return`, { method: 'PUT' });

    record.status = 'returned';
    record.returnDate = formatDate(new Date().toISOString());

    const tool = AppState.tools.find(t => t.id === record.toolId);
    if (tool) {
      tool.available++;
      if (tool.available > 0) tool.status = 'available';
    }

    showToast('success', '归还成功', `${record.toolName} 已由 ${record.employeeName} 归还`);
    renderLending(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '归还失败', err.message);
  }
}

// ========== 借用申请视图 ==========
function renderRequests(container) {
  const pendingRequests = AppState.borrowRequests.filter(r => r.status === 'pending');
  const processedRequests = AppState.borrowRequests.filter(r => r.status !== 'pending');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2>借用申请</h2>
        <p>审批和管理工具借用申请</p>
      </div>
      <button class="btn btn-primary" onclick="openRequestModal()">
        &#x2795; 提交申请
      </button>
    </div>

    <div class="tabs">
      <div class="tab active" onclick="switchRequestTab(this, 'pending')">待审批 (${pendingRequests.length})</div>
      <div class="tab" onclick="switchRequestTab(this, 'processed')">已处理 (${processedRequests.length})</div>
    </div>

    <div id="requests-pending-list">
      ${pendingRequests.length > 0 ? pendingRequests.map(req => `
        <div class="request-card">
          <div class="request-card-header">
            <div class="request-card-info">
              <div class="request-card-avatar">${getInitials(req.employeeName)}</div>
              <div>
                <div class="request-card-name">${req.employeeName}</div>
                <div class="request-card-time">申请日期: ${req.requestDate}</div>
              </div>
            </div>
            <span class="badge badge-amber">待审批</span>
          </div>
          <div class="request-card-body">
            <div class="request-card-detail">&#x1F527; 申请工具: <strong style="color:var(--text-primary)">${req.toolName}</strong> (${req.toolId}) x${req.quantity}</div>
            <div class="request-card-detail">&#x1F4DD; 申请理由: ${req.reason}</div>
          </div>
          <div class="request-card-actions">
            <button class="btn btn-success btn-sm" onclick="approveRequest('${req.employeeId}','${req.toolId}')">&#x2705; 批准</button>
            <button class="btn btn-danger btn-sm" onclick="rejectRequest('${req.employeeId}','${req.toolId}')">&#x2716; 拒绝</button>
          </div>
        </div>
      `).join('') : `
        <div class="empty-state">
          <div class="empty-state-icon">&#x2705;</div>
          <h3>暂无待审批请求</h3>
          <p>所有借用申请已处理完毕</p>
        </div>
      `}
    </div>

    <div id="requests-processed-list" style="display:none;">
      ${processedRequests.length > 0 ? processedRequests.map(req => `
        <div class="request-card">
          <div class="request-card-header">
            <div class="request-card-info">
              <div class="request-card-avatar" style="background:${req.status === 'approved' ? 'linear-gradient(135deg, var(--emerald), var(--emerald-dark))' : 'linear-gradient(135deg, var(--danger), var(--danger-dark))'}">${getInitials(req.employeeName)}</div>
              <div>
                <div class="request-card-name">${req.employeeName}</div>
                <div class="request-card-time">申请日期: ${req.requestDate}</div>
              </div>
            </div>
            <span class="badge ${getStatusBadgeClass(req.status)}">${getStatusText(req.status)}</span>
          </div>
          <div class="request-card-body">
            <div class="request-card-detail">&#x1F527; 申请工具: <strong style="color:var(--text-primary)">${req.toolName}</strong> (${req.toolId}) x${req.quantity}</div>
            <div class="request-card-detail">&#x1F4DD; 申请理由: ${req.reason}</div>
          </div>
        </div>
      `).join('') : `
        <div class="empty-state">
          <div class="empty-state-icon">&#x1F4C1;</div>
          <h3>暂无已处理请求</h3>
          <p>还没有处理过的借用申请</p>
        </div>
      `}
    </div>
  `;
}

function switchRequestTab(el, tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('requests-pending-list').style.display = tab === 'pending' ? 'block' : 'none';
  document.getElementById('requests-processed-list').style.display = tab === 'processed' ? 'block' : 'none';
}

function openRequestModal() {
  const availableTools = AppState.tools.filter(t => t.available > 0 && t.status !== 'maintenance');
  const activeEmployees = AppState.employees.filter(e => e.status === 'active');

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>提交借用申请</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">申请工具 *</label>
          <select class="form-select" id="modal-req-tool">
            <option value="">请选择工具</option>
            ${availableTools.map(t => `<option value="${t.id}">${t.name} (${t.id}) - 可用: ${t.available}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">申请人 *</label>
          <select class="form-select" id="modal-req-employee">
            <option value="">请选择员工</option>
            ${activeEmployees.map(e => `<option value="${e.id}">${e.name} (${e.id}) - ${e.department}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">申请数量</label>
          <input class="form-input" type="number" id="modal-req-quantity" value="1" min="1" />
        </div>
        <div class="form-group">
          <label class="form-label">申请理由 *</label>
          <textarea class="form-textarea" id="modal-req-reason" placeholder="请详细说明借用理由"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" onclick="submitRequest()">提交申请</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
}

async function submitRequest() {
  const toolId = document.getElementById('modal-req-tool').value;
  const employeeId = document.getElementById('modal-req-employee').value;
  const quantity = parseInt(document.getElementById('modal-req-quantity').value) || 1;
  const reason = document.getElementById('modal-req-reason').value.trim();

  if (!toolId || !employeeId || !reason) {
    showToast('warning', '提示', '请填写完整的申请信息');
    return;
  }

  const tool = AppState.tools.find(t => t.id === toolId);
  const employee = AppState.employees.find(e => e.id === employeeId);
  if (!tool || !employee) return;

  try {
    const result = await api('/requests', {
      method: 'POST',
      body: JSON.stringify({ tid: toolId }),
    });

    AppState.borrowRequests.unshift({
      id: toolId, toolId, toolName: tool.name,
      employeeId, employeeName: employee.name,
      requestDate: result.lendtime || formatDate(new Date().toISOString()),
      reason, status: 'pending', quantity,
    });

    AppState.notifications.unshift({
      id: 'N' + Date.now(), type: 'info',
      title: '新借用申请',
      desc: `${employee.name} 申请借用 ${tool.name}`,
      time: '刚刚', read: false,
    });

    updateNotificationBadge();
    document.querySelector('.modal-overlay').remove();
    showToast('success', '申请已提交', `${tool.name} 的借用申请已提交，等待审批`);
    renderRequests(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '提交失败', err.message);
  }
}

async function approveRequest(eid, tid) {
  const req = AppState.borrowRequests.find(r => r.employeeId === eid && r.toolId === tid);
  if (!req) return;

  try {
    await api(`/requests/${eid}/${tid}/approve`, { method: 'PUT' });

    req.status = 'approved';

    const tool = AppState.tools.find(t => t.id === tid);
    if (tool && tool.available > 0) {
      tool.available--;
      if (tool.available === 0) tool.status = 'borrowed';

      AppState.lendingRecords.unshift({
        id: 'L' + Date.now(), toolId: tid, toolName: tool.name,
        employeeId: eid, employeeName: req.employeeName,
        borrowDate: formatDate(new Date().toISOString()),
        returnDate: '', expectedReturn: '', status: 'active', purpose: '',
      });
    }

    showToast('success', '已批准', `${req.employeeName} 的借用申请已批准`);
    renderRequests(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '操作失败', err.message);
  }
}

async function rejectRequest(eid, tid) {
  const req = AppState.borrowRequests.find(r => r.employeeId === eid && r.toolId === tid);
  if (!req) return;

  try {
    await api(`/requests/${eid}/${tid}/reject`, { method: 'PUT' });
    req.status = 'rejected';
    showToast('info', '已拒绝', `${req.employeeName} 的借用申请已拒绝`);
    renderRequests(document.getElementById('page-content'));
  } catch (err) {
    showToast('error', '操作失败', err.message);
  }
}

// ========== 通知系统 ==========
function updateSidebarUser() {
  const user = AppState.currentUser;
  if (!user) return;

  const nameEl = document.getElementById('sidebar-user-name');
  const roleEl = document.getElementById('sidebar-user-role');
  const avatarEl = document.getElementById('sidebar-user-avatar');

  if (nameEl) nameEl.textContent = user.name;
  if (roleEl) roleEl.textContent = user.position;
  if (avatarEl) avatarEl.textContent = getInitials(user.name);
}

function updateNotificationBadge() {
  const unread = AppState.notifications.filter(n => !n.read).length;
  const badge = document.getElementById('notification-badge');
  if (badge) {
    badge.style.display = unread > 0 ? 'block' : 'none';
  }
}

function toggleNotificationPanel() {
  AppState.notificationPanelOpen = !AppState.notificationPanelOpen;
  const panel = document.getElementById('notification-panel');
  if (panel) {
    panel.classList.toggle('open', AppState.notificationPanelOpen);
    if (AppState.notificationPanelOpen) {
      renderNotificationList();
    }
  }
}

function renderNotificationList() {
  const list = document.getElementById('notification-list');
  if (!list) return;

  if (AppState.notifications.length === 0) {
    list.innerHTML = `
      <div class="empty-state" style="padding:40px 20px;">
        <div class="empty-state-icon">&#x1F514;</div>
        <h3>暂无通知</h3>
      </div>
    `;
    return;
  }

  list.innerHTML = AppState.notifications.map(n => `
    <div class="notification-item ${n.read ? '' : 'unread'}" onclick="markNotificationRead('${n.id}')">
      <div class="notification-item-content">
        <div class="notification-item-title">${n.title}</div>
        <div class="notification-item-desc">${n.desc}</div>
        <div class="notification-item-time">${n.time}</div>
      </div>
    </div>
  `).join('');
}

async function markNotificationRead(id) {
  const notif = AppState.notifications.find(n => n.id === id);
  if (notif) {
    notif.read = true;
    try { await api(`/notifications/${id}/read`, { method: 'PUT' }); } catch (e) {}
    updateNotificationBadge();
    renderNotificationList();
  }
}

// ========== 侧边栏控制 ==========
function toggleSidebar() {
  AppState.sidebarOpen = !AppState.sidebarOpen;
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('main-content');
  if (sidebar) {
    sidebar.style.width = AppState.sidebarOpen ? 'var(--sidebar-width)' : 'var(--sidebar-collapsed)';
  }
  if (mainContent) {
    mainContent.style.marginLeft = AppState.sidebarOpen ? 'var(--sidebar-width)' : 'var(--sidebar-collapsed)';
  }
}

function toggleMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar) {
    sidebar.classList.toggle('mobile-open');
  }
  if (overlay) {
    overlay.classList.toggle('active');
  }
}

function closeMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar) {
    sidebar.classList.remove('mobile-open');
  }
  if (overlay) {
    overlay.classList.remove('active');
  }
}

// ========== 实时时钟 ==========
function updateClock() {
  const clockEl = document.getElementById('topbar-clock');
  if (!clockEl) return;

  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
  const weekDay = weekDays[now.getDay()];

  clockEl.textContent = `${year}-${month}-${day} 周${weekDay} ${hours}:${minutes}:${seconds}`;
}

// ========== 初始化 ==========
function initApp() {
  // Token 检查：如果有 token 但当前无用户，尝试恢复会话
  const savedToken = localStorage.getItem('tws_token');
  if (savedToken) {
    // 有 token 时保留，登录后将重新获取数据
  }

  // 绑定登录表单
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }

  // 绑定退出按钮
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // 绑定侧边栏导航
  document.querySelectorAll('.nav-item[data-view]').forEach(item => {
    item.addEventListener('click', () => {
      navigate(item.dataset.view);
    });
  });

  // 绑定移动端菜单
  const menuToggle = document.getElementById('menu-toggle');
  if (menuToggle) {
    menuToggle.addEventListener('click', toggleMobileSidebar);
  }

  // 绑定侧边栏遮罩
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeMobileSidebar);
  }

  // 绑定通知按钮
  const notifBtn = document.getElementById('notification-btn');
  if (notifBtn) {
    notifBtn.addEventListener('click', toggleNotificationPanel);
  }

  // 绑定侧边栏折叠
  const collapseBtn = document.getElementById('sidebar-collapse-btn');
  if (collapseBtn) {
    collapseBtn.addEventListener('click', toggleSidebar);
  }

  // 绑定按钮涟漪效果
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (btn) addRippleEffect(e);
  });

  // 启动路由
  window.addEventListener('hashchange', handleRoute);
  handleRoute();

  // 启动时钟
  updateClock();
  setInterval(updateClock, 1000);

  // 更新通知徽章
  updateNotificationBadge();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initApp);
