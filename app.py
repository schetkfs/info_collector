@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    if not logged_in():
        return {'success': False, 'msg': '未登录'}, 403
    from db import Lead
    data = request.get_json(force=True)
    user_id = data.get('id')
    if not user_id:
        return {'success': False, 'msg': '缺少用户ID'}
    lead = Lead.query.get(user_id)
    if not lead:
        return {'success': False, 'msg': '用户不存在'}
    try:
        db.session.delete(lead)
        db.session.commit()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'msg': str(e)}

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


# 分步提交接口
from flask import jsonify
@app.route('/submit_step', methods=['POST'])
def submit_step():
    from db import Lead
    data = request.get_json(force=True)
    step = data.get('step')
    if not step:
        return jsonify(success=False, msg='缺少step参数')
    # 第一步新建Lead，未填写字段保存为空
    if int(step) == 1:
        lead_data = {
            'name': data.get('name', ''),
            'gender': data.get('gender', ''),
            'contact': data.get('contact', ''),
            'age': None,
            'location': '',
            'industry': '',
            'job_role': '',
            'preference_type': '',
            'investment_preference': '',
            'incubation_info': '',
            'investment_experience': '',
            'tech_adaptability': '',
            'high_net_worth': '',
            'expected_investment': '',
            'ip': get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:255]
        }
        if 'age' in data and str(data['age']).strip():
            try:
                age_val = int(data['age'])
                if 0 <= age_val <= 120:
                    lead_data['age'] = age_val
            except Exception:
                pass
        lead = Lead(**lead_data)
        db.session.add(lead)
        db.session.commit()
        session['lead_id'] = lead.id
        session.modified = True
        return jsonify(success=True)
    # 后续步骤更新同一条Lead
    lead_id = session.get('lead_id')
    if not lead_id:
        return jsonify(success=False, msg='未找到用户记录，请刷新页面重新填写')
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify(success=False, msg='用户记录不存在，请刷新页面重新填写')
    # step 2
    if int(step) == 2:
        lead.location = data.get('location', '')
        lead.industry = data.get('industry', '')
        lead.job_role = data.get('job_role', '')
    # step 3
    if int(step) == 3:
        lead.preference_type = data.get('preference_type', '')
        lead.investment_preference = data.get('investment_preference', '')
        lead.incubation_info = data.get('incubation_info', '')
        lead.investment_experience = data.get('investment_experience', '')
        lead.tech_adaptability = data.get('tech_adaptability', '')
    # step 4
    if int(step) == 4:
        lead.high_net_worth = data.get('high_net_worth', '')
        lead.expected_investment = data.get('expected_investment', '')
        db.session.commit()
        # 清理session，跳转到成功页面
        session.pop('lead_id', None)
        return jsonify(success=True, redirect=url_for('success'))
    db.session.commit()
    return jsonify(success=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    # 分步提交已完成，直接跳转到成功页面
    return render_template('success.html')
@app.route('/success', methods=['GET'])
def success():
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
def export_csv():
    if not logged_in():
        return redirect(url_for('login'))
    from db import Lead
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow([
        '编号', '姓名', '性别', '联系方式', '行业', '职务或角色', '投资偏好类型',
        '投资偏好', '孵化产业及资金', '年龄', '地域', '投资经验',
        '对RWA的了解程度', '高净值人群', '预期投资金额', 'IP', '设备信息', '提交时间'
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
        migrate_database_runtime(db)
        html_output += "<h2>已尝试修复数据库结构，请返回后台刷新页面。</h2>"
        html_output += "<p><a href='/admin'>返回管理后台</a></p>"
        html_output += "</body></html>"
        print("🎉 手动数据库修复完成")
        return html_output
    except Exception as e:
        print(f"❌ 手动修复失败: {e}")
        return f"<h1>数据库修复失败</h1><p>{str(e)}</p><p><a href='/admin'>返回管理后台</a></p>", 500
