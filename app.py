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
    contact = db.Column(db.String(128), nullable=False)  # 联系方式
    industry = db.Column(db.String(128), nullable=False)  # 主要从事行业
    job_role = db.Column(db.String(128), nullable=False)  # 主要从事行业中的职务或角色
    preference_type = db.Column(db.String(32), nullable=False)  # RWA投资或RWA孵化
    investment_preference = db.Column(db.Text)  # 投资偏好（RWA投资时必填）
    incubation_info = db.Column(db.Text)  # RWA孵化产业及参与资金（RWA孵化时必填）
    age = db.Column(db.Integer)  # 年龄（选填）
    location = db.Column(db.String(128))  # 目前所在地域（选填）
    investment_experience = db.Column(db.Text)  # 投资经验（选填）
    tech_adaptability = db.Column(db.String(64))  # 技术适应度（选填）
    high_net_worth = db.Column(db.String(16))  # 是否为高净值人群（选填）
    expected_investment = db.Column(db.String(64))  # 预期投资金额区间（选填）
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
    <h1>RWA投资与孵化信息采集</h1>
    <div class="sub">请填写以下信息。仅用于内部分析，不对外公开。</div>
    <form method="post" action="{{ url_for('submit') }}">
      <!-- 基本信息（必填） -->
      <h3 style="color:#38bdf8;margin-top:24px;">基本信息</h3>
      
      <label>姓名 <span class="badge">必填</span></label>
      <input type="text" name="name" maxlength="64" placeholder="请输入姓名" required>

      <label>性别 <span class="badge">必填</span></label>
      <select name="gender" required>
        <option value="">请选择</option>
        <option value="男">男</option>
        <option value="女">女</option>
        <option value="其他">其他</option>
      </select>

      <label>联系方式 <span class="badge">必填</span></label>
      <input type="text" name="contact" maxlength="128" placeholder="请输入手机号码或邮箱" required>

      <!-- 职业信息（必填） -->
      <h3 style="color:#38bdf8;margin-top:24px;">职业信息</h3>
      
      <label>主要从事行业 <span class="badge">必填</span></label>
      <input type="text" name="industry" maxlength="128" placeholder="例如：金融、科技、制造业等" required>

      <label>主要从事行业中的职务或角色 <span class="badge">必填</span></label>
      <input type="text" name="job_role" maxlength="128" placeholder="例如：投资总监、产品经理、CEO等" required>

      <!-- 偏好选择（必填） -->
      <h3 style="color:#38bdf8;margin-top:24px;">投资偏好</h3>
      
      <label>更偏好投资（RWA投资）还是企业孵化（RWA孵化） <span class="badge">必填</span></label>
      <select name="preference_type" id="preference_type" required onchange="togglePreferenceFields()">
        <option value="">请选择</option>
        <option value="RWA投资">RWA投资</option>
        <option value="RWA孵化">RWA孵化</option>
      </select>

      <!-- RWA投资相关字段 -->
      <div id="investment_fields" style="display:none;">
        <label>投资偏好 <span class="badge">必填</span></label>
        <textarea name="investment_preference" rows="3" placeholder="请描述您的投资偏好，如：短期收益、长期资产增值、风险对冲等" style="width:100%;padding:12px 14px;border:1px solid #334155;background:#0b1220;color:#e5e7eb;border-radius:12px;outline:none;resize:vertical;font-family:inherit;"></textarea>
      </div>

      <!-- RWA孵化相关字段 -->
      <div id="incubation_fields" style="display:none;">
        <label>RWA孵化产业及参与资金 <span class="badge">必填</span></label>
        <textarea name="incubation_info" rows="3" placeholder="请描述您感兴趣的RWA孵化产业及预期参与的资金规模" style="width:100%;padding:12px 14px;border:1px solid #334155;background:#0b1220;color:#e5e7eb;border-radius:12px;outline:none;resize:vertical;font-family:inherit;"></textarea>
      </div>

      <!-- 选填信息 -->
      <h3 style="color:#38bdf8;margin-top:24px;">补充信息（选填）</h3>
      
      <label>年龄 <span style="color:#94a3b8;">选填</span></label>
      <input type="number" name="age" min="0" max="120" placeholder="例如：28">

      <label>目前所在地域 <span style="color:#94a3b8;">选填</span></label>
      <input type="text" name="location" maxlength="128" placeholder="例如：北京、上海、深圳等">

      <label>投资经验 <span style="color:#94a3b8;">选填</span></label>
      <textarea name="investment_experience" rows="3" placeholder="请简述您的投资经验和背景" style="width:100%;padding:12px 14px;border:1px solid #334155;background:#0b1220;color:#e5e7eb;border-radius:12px;outline:none;resize:vertical;font-family:inherit;"></textarea>

      <label>技术适应度 <span style="color:#94a3b8;">选填</span></label>
      <select name="tech_adaptability">
        <option value="">请选择</option>
        <option value="完全不了解">完全不了解区块链、加密货币等新兴技术</option>
        <option value="基础了解">对区块链、加密货币有基础了解</option>
        <option value="有使用经验">有区块链、加密货币的使用经验</option>
        <option value="深度参与">深度参与区块链、加密货币相关业务</option>
      </select>

      <label>是否为高净值人群 <span style="color:#94a3b8;">选填</span></label>
      <select name="high_net_worth">
        <option value="">请选择</option>
        <option value="是">是</option>
        <option value="否">否</option>
        <option value="不便透露">不便透露</option>
      </select>

      <label>预期想用于投资理财RWA的金额区间 <span style="color:#94a3b8;">选填</span></label>
      <select name="expected_investment">
        <option value="">请选择</option>
        <option value="1-10万">1-10万</option>
        <option value="10-50万">10-50万</option>
        <option value="50万以上">50万以上</option>
        <option value="不确定">不确定</option>
      </select>

      <button class="btn" type="submit">提交</button>
    </form>
    {% if msg %}
      <div class="footer">{{ msg }}</div>
    {% endif %}
    <div class="footer">提交即表示同意我们对于数据使用的说明：仅用于业务沟通与画像分析，不会出售或泄露给第三方。</div>
  </div>
</div>

<script>
function togglePreferenceFields() {
  const preferenceType = document.getElementById('preference_type').value;
  const investmentFields = document.getElementById('investment_fields');
  const incubationFields = document.getElementById('incubation_fields');
  
  if (preferenceType === 'RWA投资') {
    investmentFields.style.display = 'block';
    incubationFields.style.display = 'none';
    document.querySelector('textarea[name="investment_preference"]').required = true;
    document.querySelector('textarea[name="incubation_info"]').required = false;
  } else if (preferenceType === 'RWA孵化') {
    investmentFields.style.display = 'none';
    incubationFields.style.display = 'block';
    document.querySelector('textarea[name="investment_preference"]').required = false;
    document.querySelector('textarea[name="incubation_info"]').required = true;
  } else {
    investmentFields.style.display = 'none';
    incubationFields.style.display = 'none';
    document.querySelector('textarea[name="investment_preference"]').required = false;
    document.querySelector('textarea[name="incubation_info"]').required = false;
  }
}
</script>
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
    <h1>RWA投资与孵化信息采集后台</h1>
    <div>
      <a class="link" href="{{ url_for('export_csv') }}">导出 CSV</a>　|　
      <a class="link" href="{{ url_for('logout') }}">退出</a>
    </div>
  </div>
  <div class="card">
    <div class="sub">共 {{ total }} 条，当前第 {{ page }} / {{ pages }} 页</div>
    <table class="table">
      <thead>
        <tr>
          <th style="width:40px;">ID</th>
          <th style="width:80px;">姓名</th>
          <th style="width:60px;">性别</th>
          <th style="width:120px;">联系方式</th>
          <th style="width:100px;">行业</th>
          <th style="width:100px;">职务角色</th>
          <th style="width:80px;">投资偏好</th>
          <th style="width:60px;">年龄</th>
          <th style="width:80px;">地域</th>
          <th style="width:100px;">来源 IP</th>
          <th style="width:120px;">时间</th>
        </tr>
      </thead>
      <tbody>
        {% for x in items %}
        <tr>
          <td>{{ x.id }}</td>
          <td>{{ x.name }}</td>
          <td>{{ x.gender }}</td>
          <td>{{ x.contact }}</td>
          <td title="{{ x.industry }}">{{ x.industry[:10] }}{% if x.industry|length > 10 %}...{% endif %}</td>
          <td title="{{ x.job_role }}">{{ x.job_role[:10] }}{% if x.job_role|length > 10 %}...{% endif %}</td>
          <td>{{ x.preference_type }}</td>
          <td>{{ x.age if x.age else '-' }}</td>
          <td title="{{ x.location if x.location else '' }}">{{ x.location[:8] if x.location else '-' }}{% if x.location and x.location|length > 8 %}...{% endif %}</td>
          <td>{{ x.ip }}</td>
          <td>{{ x.created_at.strftime('%m-%d %H:%M') }}</td>
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
    <div class="footer" style="margin-top:20px;color:#64748b;font-size:12px;">
      提示：鼠标悬停在省略的内容上可查看完整信息。点击导出CSV可获取所有详细数据。
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
    # 基本信息（必填）
    name = (request.form.get('name') or '').strip()
    gender = (request.form.get('gender') or '').strip()
    contact = (request.form.get('contact') or '').strip()
    
    # 职业信息（必填）
    industry = (request.form.get('industry') or '').strip()
    job_role = (request.form.get('job_role') or '').strip()
    
    # 投资偏好（必填）
    preference_type = (request.form.get('preference_type') or '').strip()
    investment_preference = (request.form.get('investment_preference') or '').strip()
    incubation_info = (request.form.get('incubation_info') or '').strip()
    
    # 选填信息
    age_raw = (request.form.get('age') or '').strip()
    location = (request.form.get('location') or '').strip()
    investment_experience = (request.form.get('investment_experience') or '').strip()
    tech_adaptability = (request.form.get('tech_adaptability') or '').strip()
    high_net_worth = (request.form.get('high_net_worth') or '').strip()
    expected_investment = (request.form.get('expected_investment') or '').strip()

    # 验证必填字段
    if not name or len(name) > 64:
        return render_template_string(FORM_TEMPLATE, msg="姓名必填，且不超过 64 字符")
    
    if gender not in ('男', '女', '其他'):
        return render_template_string(FORM_TEMPLATE, msg="请选择正确的性别")
    
    if not contact or len(contact) > 128:
        return render_template_string(FORM_TEMPLATE, msg="联系方式必填，且不超过 128 字符")
    
    if not industry or len(industry) > 128:
        return render_template_string(FORM_TEMPLATE, msg="主要从事行业必填，且不超过 128 字符")
    
    if not job_role or len(job_role) > 128:
        return render_template_string(FORM_TEMPLATE, msg="职务或角色必填，且不超过 128 字符")
    
    if preference_type not in ('RWA投资', 'RWA孵化'):
        return render_template_string(FORM_TEMPLATE, msg="请选择投资偏好类型")
    
    # 根据偏好类型验证条件必填字段
    if preference_type == 'RWA投资' and not investment_preference:
        return render_template_string(FORM_TEMPLATE, msg="选择RWA投资时，投资偏好为必填项")
    
    if preference_type == 'RWA孵化' and not incubation_info:
        return render_template_string(FORM_TEMPLATE, msg="选择RWA孵化时，RWA孵化产业及参与资金为必填项")
    
    # 验证年龄（选填，但如果填写则需要有效）
    age = None
    if age_raw:
        try:
            age = int(age_raw)
            if age < 0 or age > 120:
                raise ValueError
        except ValueError:
            return render_template_string(FORM_TEMPLATE, msg="年龄请输入 0–120 的整数")

    # 创建数据库记录
    lead = Lead(
        name=name, 
        gender=gender, 
        contact=contact,
        industry=industry,
        job_role=job_role,
        preference_type=preference_type,
        investment_preference=investment_preference if preference_type == 'RWA投资' else None,
        incubation_info=incubation_info if preference_type == 'RWA孵化' else None,
        age=age,
        location=location if location else None,
        investment_experience=investment_experience if investment_experience else None,
        tech_adaptability=tech_adaptability if tech_adaptability else None,
        high_net_worth=high_net_worth if high_net_worth else None,
        expected_investment=expected_investment if expected_investment else None,
        ip=get_client_ip(),
        user_agent=request.headers.get('User-Agent', '')[:255]
    )
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
    writer.writerow([
        'id', 'name', 'gender', 'contact', 'industry', 'job_role', 'preference_type',
        'investment_preference', 'incubation_info', 'age', 'location', 'investment_experience',
        'tech_adaptability', 'high_net_worth', 'expected_investment', 'ip', 'user_agent', 'created_at'
    ])
    for x in Lead.query.order_by(Lead.created_at.desc()).all():
        writer.writerow([
            x.id, x.name, x.gender, x.contact, x.industry, x.job_role, x.preference_type,
            x.investment_preference or '', x.incubation_info or '', x.age or '',
            x.location or '', x.investment_experience or '', x.tech_adaptability or '',
            x.high_net_worth or '', x.expected_investment or '', x.ip,
            x.user_agent, x.created_at.isoformat(sep=' ', timespec='seconds')
        ])
    data = si.getvalue().encode('utf-8-sig')
    resp = make_response(data)
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename=rwa_leads.csv'
    return resp

@app.route('/healthz')
def healthz():
    return 'ok', 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
