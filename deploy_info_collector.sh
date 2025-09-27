#!/usr/bin/env bash
# 一键部署：最小可用信息采集系统（姓名/性别/年龄）
# 适用：Ubuntu 20.04/22.04+
set -Eeuo pipefail

########## 可配置变量 ##########
DOMAIN="app.jp03osj.daoguilai.com"
EMAIL="you@example.com"         # 用于 Let's Encrypt；开启 HTTPS 时必填
ENABLE_TLS=0                    # 0 仅 HTTP；1 同时签发 HTTPS 并自动跳转

APP_USER="infoapp"
APP_DIR="/opt/info-collector"
SERVICE_NAME="info-collector"
APP_PORT="8000"

ADMIN_USERNAME="admin"
# 若留空则自动随机
ADMIN_PASSWORD="Jds@123456"
# 若留空则自动随机
SECRET_KEY="1234567890987654321"
################################

# 需要 root
if [[ "${EUID}" -ne 0 ]]; then
  echo "请用 root 运行：sudo $0"
  exit 1
fi

echo "==> 安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
apt update -y
apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx curl

echo "==> 创建应用用户与目录（若已存在将跳过）"
id -u "${APP_USER}" >/dev/null 2>&1 || useradd -r -m -d "${APP_DIR}" -s /bin/bash "${APP_USER}"
mkdir -p "${APP_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "==> 生成随机密钥/密码（如未自定义）"
if [[ -z "${SECRET_KEY}" ]]; then
  SECRET_KEY="$(openssl rand -hex 32)"
fi
if [[ -z "${ADMIN_PASSWORD}" ]]; then
  ADMIN_PASSWORD="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)"
fi

echo "==> 创建虚拟环境并安装依赖"
sudo -u "${APP_USER}" bash -lc "
  cd '${APP_DIR}' && \
  python3 -m venv venv && \
  source venv/bin/activate && \
  pip install --upgrade pip && \
  pip install flask flask_sqlalchemy gunicorn
"

echo "==> 写入应用代码 app.py"
cat > "${APP_DIR}/app.py" <<'PY'
import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, session, make_response

from flask_sqlalchemy import SQLAlchemy
import io, csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'please-change-me')

# 根据环境变量决定是否仅在 HTTPS 下发送会话 cookie（0/1）
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(8), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    ip = db.Column(db.String(64))
    user_agent = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

with app.app_context():
    db.create_all()

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')

BASE_CSS = """
<style>
:root{--bg:#0f172a;--card:#111827;--muted:#94a3b8;--text:#e5e7eb;--accent:#38bdf8;}
*{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--text);
font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;line-height:1.5;}
.container{max-width:920px;margin:40px auto;padding:0 16px;}
.card{background:var(--card);border:1px solid #1f2937;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,0.2);padding:24px;}
h1{margin:0 0 12px 0;font-size:28px;letter-spacing:0.2px;}
.sub{color:var(--muted);margin-bottom:16px;}
label{display:block;margin:14px 0 6px 2px;font-weight:600;}
input[type=text], input[type=number], select{width:100%;padding:12px 14px;border:1px solid #334155;background:#0b1220;color:var(--text);border-radius:12px;outline:none;}
input::placeholder{color:#6b7280;}
.btn{display:inline-block;background:var(--accent);color:#001018;border:0;padding:12px 18px;border-radius:12px;font-weight:700;cursor:pointer;margin-top:12px;}
.btn:hover{filter:brightness(1.05);} .table{width:100%;border-collapse:separate;border-spacing:0 8px;}
.table th{color:#cbd5e1;text-align:left;font-weight:600;padding:10px 12px;}
.table td{padding:12px;background:#0b1220;border:1px solid #1f2937;}
.table tr td:first-child{border-top-left-radius:12px;border-bottom-left-radius:12px;}
.table tr td:last-child{border-top-right-radius:12px;border-bottom-right-radius:12px;}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}
a.link{color:#7dd3fc;text-decoration:none;} a.link:hover{text-decoration:underline;}
.badge{display:inline-block;padding:4px 10px;background:#0b1220;border:1px solid #1f2937;border-radius:999px;color:#93c5fd;font-size:12px;}
.footer{color:#64748b;margin-top:16px;font-size:13px;}
input[type=number]::-webkit-outer-spin-button,input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0;}
</style>
"""

FORM_TEMPLATE = BASE_CSS + """
<div class="container">
  <div class="card">
    <h1>基本信息采集</h1>
    <div class="sub">请填写以下信息。仅用于内部分析，不对外公开。</div>
    <form method="post" action="{{ url_for('submit') }}">
      <label>姓名 <span class="badge">必填</span></label>
      <input type="text" name="name" maxlength="64" placeholder="请输入姓名" required>

      <label>性别 <span class="badge">必填</span></label>
      <select name="gender" required>
        <option value="">请选择</option>
        <option value="男">男</option>
        <option value="女">女</option>
        <option value="其他">其他</option>
      </select>

      <label>年龄 <span class="badge">必填</span></label>
      <input type="number" name="age" min="0" max="120" placeholder="例如：28" required>

      <button class="btn" type="submit">提交</button>
    </form>
    {% if msg %}
      <div class="footer">{{ msg }}</div>
    {% endif %}
    <div class="footer">提交即表示同意我们对于数据使用的说明：仅用于业务沟通，不会出售或泄露给第三方。</div>
  </div>
</div>
"""

SUCCESS_TEMPLATE = BASE_CSS + """
<div class="container">
  <div class="card">
    <h1>提交成功</h1>
    <div class="sub">感谢填写，我们已收到你的信息。</div>
    <a class="link" href="{{ url_for('index') }}">返回继续</a>
  </div>
</div>
"""

LOGIN_TEMPLATE = BASE_CSS + """
<div class="container">
  <div class="card">
    <h1>管理员登录</h1>
    <form method="post">
      <label>用户名</label>
      <input type="text" name="username" required>
      <label>密码</label>
      <input type="password" name="password" required>
      <button class="btn" type="submit">登录</button>
    </form>
  </div>
</div>
"""

ADMIN_TEMPLATE = BASE_CSS + """
<div class="container">
  <div class="topbar">
    <h1>信息采集后台</h1>
    <div>
      <a class="link" href="{{ url_for('export_csv') }}">导出 CSV</a>　|　
      <a class="link" href="{{ url_for('logout') }}">退出</a>
    </div>
  </div>
  <div class="card">
    <div class="sub">共 {{ total }} 条，当前第 {{ page }} / {{ pages }} 页</div>
    <table class="table">
      <thead>
        <tr><th>ID</th><th>姓名</th><th>性别</th><th>年龄</th><th>来源 IP</th><th>时间</th></tr>
      </thead>
      <tbody>
        {% for x in items %}
        <tr>
          <td>{{ x.id }}</td><td>{{ x.name }}</td><td>{{ x.gender }}</td><td>{{ x.age }}</td>
          <td>{{ x.ip }}</td><td>{{ x.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <div class="topbar">
      <div>
        {% if page > 1 %}<a class="link" href="{{ url_for('admin', page=page-1) }}">上一页</a>{% endif %}
        {% if page < pages %}{% if page > 1 %} · {% endif %}<a class="link" href="{{ url_for('admin', page=page+1) }}">下一页</a>{% endif %}
      </div>
      <div>每页 20 条</div>
    </div>
  </div>
</div>
"""

def get_client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    return xff.split(',')[0].strip() if xff else (request.remote_addr or '')

def logged_in():
    return session.get('is_admin') is True

@app.route('/', methods=['GET'])
def index():
    return render_template_string(FORM_TEMPLATE)

@app.route('/submit', methods=['POST'])
def submit():
    name = (request.form.get('name') or '').strip()
    gender = (request.form.get('gender') or '').strip()
    age_raw = (request.form.get('age') or '').strip()

    if not name or len(name) > 64:
        return render_template_string(FORM_TEMPLATE, msg="姓名必填，且不超过 64 字符")
    if gender not in ('男', '女', '其他'):
        return render_template_string(FORM_TEMPLATE, msg="请选择正确的性别")
    try:
        age = int(age_raw)
        if age < 0 or age > 120:
            raise ValueError
    except ValueError:
        return render_template_string(FORM_TEMPLATE, msg="年龄请输入 0–120 的整数")

    lead = Lead(name=name, gender=gender, age=age,
                ip=get_client_ip(),
                user_agent=request.headers.get('User-Agent', '')[:255])
    db.session.add(lead)
    db.session.commit()
    return render_template_string(SUCCESS_TEMPLATE)

@app.route('/admin/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin'))
        return render_template_string(LOGIN_TEMPLATE)
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if not logged_in():
        return redirect(url_for('login'))
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 20
    q = Lead.query.order_by(Lead.created_at.desc())
    total = q.count()
    items = q.offset((page-1)*per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    return render_template_string(ADMIN_TEMPLATE, items=items, total=total, page=page, pages=pages)

@app.route('/admin/export.csv')
def export_csv():
    if not logged_in():
        return redirect(url_for('login'))
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['id','name','gender','age','ip','user_agent','created_at'])
    for x in Lead.query.order_by(Lead.created_at.desc()).all():
        writer.writerow([x.id, x.name, x.gender, x.age, x.ip, x.user_agent, x.created_at.isoformat(sep=' ', timespec='seconds')])
    data = si.getvalue().encode('utf-8-sig')
    resp = make_response(data)
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename=leads.csv'
    return resp

@app.route('/healthz')
def healthz():
    return 'ok', 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
PY

chown "${APP_USER}:${APP_USER}" "${APP_DIR}/app.py"

echo "==> 写入 systemd 服务"
SESSION_COOKIE_SECURE_VAL="0"
if [[ "${ENABLE_TLS}" -eq 1 ]]; then
  SESSION_COOKIE_SECURE_VAL="1"
fi

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<SERVICE
[Unit]
Description=Info Collector (Flask) Service
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=SECRET_KEY=${SECRET_KEY}
Environment=ADMIN_USERNAME=${ADMIN_USERNAME}
Environment=ADMIN_PASSWORD=${ADMIN_PASSWORD}
Environment=SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE_VAL}
ExecStart=${APP_DIR}/venv/bin/gunicorn -w 2 -b 127.0.0.1:${APP_PORT} app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

echo "==> 配置 Nginx 站点（HTTP 反代）"
/bin/cat > /etc/nginx/sites-available/${SERVICE_NAME} <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    client_max_body_size 2m;
}
NGINX

ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME}
nginx -t
systemctl reload nginx

if command -v ufw >/dev/null 2>&1; then
  if ufw status | grep -q "Status: active"; then
    echo "==> UFW 已开启：放行 HTTP"
    ufw allow 'Nginx HTTP' || true
  fi
fi

if [[ "${ENABLE_TLS}" -eq 1 ]]; then
  echo "==> 申请并配置 Let’s Encrypt 证书（HTTPS）"
  if [[ "${EMAIL}" == "you@example.com" ]]; then
    echo "!! 请先在脚本顶部设置有效 EMAIL 再启用 HTTPS"
  else
    # 放行 HTTPS（若 UFW 开启）
    if command -v ufw >/dev/null 2>&1; then
      if ufw status | grep -q "Status: active"; then
        ufw allow 'Nginx Full' || true
      fi
    fi
    # 非交互申请证书并自动写入 Nginx 配置（含 80->443 跳转）
    if certbot --nginx -d "${DOMAIN}" --redirect -m "${EMAIL}" --agree-tos -n; then
      echo "HTTPS 配置完成"
      systemctl reload nginx
      systemctl restart "${SERVICE_NAME}"
    else
      echo "!! Certbot 申请证书失败，先以 HTTP 运行，稍后可重试：certbot --nginx -d ${DOMAIN} ..."
    fi
  fi
fi

echo
echo "==============================================="
echo "部署完成！访问："
if [[ "${ENABLE_TLS}" -eq 1 ]]; then
  echo "  - 采集页： https://${DOMAIN}/"
  echo "  - 后台：   https://${DOMAIN}/admin/login"
else
  echo "  - 采集页： http://${DOMAIN}/"
  echo "  - 后台：   http://${DOMAIN}/admin/login"
fi
echo
echo "管理员账号： ${ADMIN_USERNAME}"
echo "管理员密码： ${ADMIN_PASSWORD}"
echo
echo "管理命令："
echo "  systemctl status ${SERVICE_NAME}  # 查看状态"
echo "  journalctl -u ${SERVICE_NAME} -f  # 实时日志"
echo "  systemctl restart ${SERVICE_NAME} # 重启"
echo "SQLite 数据库： ${APP_DIR}/data.db"
echo "==============================================="
