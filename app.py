import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template, session, make_response

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

def get_client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    return xff.split(',')[0].strip() if xff else (request.remote_addr or '')

def logged_in():
    return session.get('is_admin') is True

@app.route('/', methods=['GET'])
def index():
    return render_template('form.html')

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
        return render_template('form.html', msg="姓名必填，且不超过 64 字符")
    
    if gender not in ('男', '女', '其他'):
        return render_template('form.html', msg="请选择正确的性别")
    
    if not contact or len(contact) > 128:
        return render_template('form.html', msg="联系方式必填，且不超过 128 字符")
    
    if not industry or len(industry) > 128:
        return render_template('form.html', msg="主要从事行业必填，且不超过 128 字符")
    
    if not job_role or len(job_role) > 128:
        return render_template('form.html', msg="职务或角色必填，且不超过 128 字符")
    
    if preference_type not in ('RWA投资', 'RWA孵化'):
        return render_template('form.html', msg="请选择投资偏好类型")
    
    # 根据偏好类型验证条件必填字段
    if preference_type == 'RWA投资' and not investment_preference:
        return render_template('form.html', msg="选择RWA投资时，投资偏好为必填项")
    
    if preference_type == 'RWA孵化' and not incubation_info:
        return render_template('form.html', msg="选择RWA孵化时，RWA孵化产业及参与资金为必填项")
    
    # 验证年龄（选填，但如果填写则需要有效）
    age = None
    if age_raw:
        try:
            age = int(age_raw)
            if age < 0 or age > 120:
                raise ValueError
        except ValueError:
            return render_template('form.html', msg="年龄请输入 0–120 的整数")

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
    return render_template('success.html')

@app.route('/admin/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin'))
        return render_template('login.html')
    return render_template('login.html')

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
    return render_template('admin.html', items=items, total=total, page=page, pages=pages)

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
