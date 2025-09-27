
import io, csv
from flask import Flask, request, redirect, url_for, render_template, session, make_response
from db import db, check_and_migrate_database, ensure_database_schema, migrate_database_runtime, database_path

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'please-change-me'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 绑定db到app
db.init_app(app)

# 启动时迁移和初始化数据库（db初始化后再导入模型）
with app.app_context():
    from db import Lead
    check_and_migrate_database()
    db.create_all()

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '123456'

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
    try:
        # 运行时检查和修复数据库结构
        if not ensure_database_schema(db):
            return "<h1>数据库维护中...</h1><p>数据库结构正在更新，请稍后刷新页面。</p>", 503
        page = max(int(request.args.get('page', 1)), 1)
        per_page = 20
        q = Lead.query.order_by(Lead.created_at.desc())
        total = q.count()
        items = q.offset((page-1)*per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page
        return render_template('admin.html', items=items, total=total, page=page, pages=pages)
    except Exception as e:
        print(f"❌ 管理页面出错: {e}")
        return f"<h1>管理页面错误</h1><p>{e}</p><p><a href='/admin/fix-db'>尝试修复数据库</a></p>", 500

@app.route('/admin/export.csv')
@app.route('/admin/fix-db')
def fix_database():
    if not logged_in():
        return redirect(url_for('login'))
    try:
        print("🔧 开始手动数据库修复...")
        result = db.session.execute(db.text("PRAGMA table_info(lead);")).fetchall()
        current_columns = [row[1] for row in result]
        html_output = f"""
        <html>
        <head><title>数据库修复工具</title></head>
        <body>
        <h1>数据库修复工具</h1>
        <h2>当前表结构</h2>
        <p>现有列: {', '.join(current_columns)}</p>
        """
        # 直接调用迁移函数
        migrate_database_runtime(db)
        html_output += "<h2>已尝试修复数据库结构，请返回后台刷新页面。</h2>"
        html_output += "<p><a href='/admin'>返回管理后台</a></p>"
        html_output += "</body></html>"
        print("🎉 手动数据库修复完成")
        return html_output
    except Exception as e:
        print(f"❌ 手动修复失败: {e}")
        return f"<h1>数据库修复失败</h1><p>{str(e)}</p><p><a href='/admin'>返回管理后台</a></p>", 500
