import os
import sqlite3
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# 数据库配置 - 使用 instance/data.db
basedir = os.path.abspath(os.path.dirname(__file__))

instance_dir = os.path.join(basedir, 'instance')
if not os.path.exists(instance_dir):
    try:
        os.makedirs(instance_dir, exist_ok=True)
        print(f"已创建数据库目录: {instance_dir}")
    except Exception as e:
        print(f"❌ 创建数据库目录失败: {e}")
database_path = os.path.join(instance_dir, 'data.db')
# 确保数据库文件可写（首次运行时创建空文件）
try:
    if not os.path.exists(database_path):
        open(database_path, 'a').close()
        print(f"已创建数据库文件: {database_path}")
except Exception as e:
    print(f"❌ 创建数据库文件失败: {e}")
print(f"数据库文件路径: {database_path}")

# db对象需要在app初始化后绑定

db = SQLAlchemy()

class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(8), nullable=False)
    contact = db.Column(db.String(128), nullable=False)
    industry = db.Column(db.String(128), nullable=False)
    job_role = db.Column(db.String(128), nullable=False)
    preference_type = db.Column(db.String(32), nullable=False)
    investment_preference = db.Column(db.Text)
    incubation_info = db.Column(db.Text)
    age = db.Column(db.Integer)
    location = db.Column(db.String(128))
    investment_experience = db.Column(db.Text)
    tech_adaptability = db.Column(db.String(64))
    high_net_worth = db.Column(db.String(16))
    expected_investment = db.Column(db.String(64))
    ip = db.Column(db.String(64))
    user_agent = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

def check_and_migrate_database():
    if not os.path.exists(database_path):
        print("📊 数据库文件不存在，将创建新的数据库")
        return
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lead';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print("📊 lead表不存在，将创建新表")
            conn.close()
            return
        cursor.execute("PRAGMA table_info(lead);")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"📋 现有数据库列: {column_names}")
        new_columns = [
            ('contact', 'VARCHAR(128) NOT NULL DEFAULT ""'),
            ('industry', 'VARCHAR(128) NOT NULL DEFAULT ""'),
            ('job_role', 'VARCHAR(128) NOT NULL DEFAULT ""'),
            ('preference_type', 'VARCHAR(32) NOT NULL DEFAULT ""'),
            ('investment_preference', 'TEXT'),
            ('incubation_info', 'TEXT'),
            ('location', 'VARCHAR(128)'),
            ('investment_experience', 'TEXT'),
            ('tech_adaptability', 'VARCHAR(64)'),
            ('high_net_worth', 'VARCHAR(16)'),
            ('expected_investment', 'VARCHAR(64)')
        ]
        migrations_needed = []
        for col_name, col_definition in new_columns:
            if col_name not in column_names:
                migrations_needed.append((col_name, col_definition))
        if migrations_needed:
            print(f"🔄 需要添加的列: {[col[0] for col in migrations_needed]}")
            for col_name, col_definition in migrations_needed:
                try:
                    alter_sql = f"ALTER TABLE lead ADD COLUMN {col_name} {col_definition};"
                    cursor.execute(alter_sql)
                    print(f"✅ 添加列: {col_name}")
                except sqlite3.Error as e:
                    print(f"❌ 添加列 {col_name} 失败: {e}")
            conn.commit()
            print("✅ 数据库迁移完成")
        else:
            print("✅ 数据库结构已是最新版本")
        conn.close()
    except Exception as e:
        print(f"❌ 数据库迁移检查失败: {e}")

def ensure_database_schema(db):
    try:
        db.session.execute(db.text("SELECT contact FROM lead LIMIT 1")).fetchone()
        return True
    except Exception:
        print("🔄 检测到数据库结构过时，开始运行时迁移...")
        return migrate_database_runtime(db)

def migrate_database_runtime(db):
    try:
        migrations = [
            ("contact", "VARCHAR(128) NOT NULL DEFAULT ''"),
            ("industry", "VARCHAR(128) NOT NULL DEFAULT ''"),
            ("job_role", "VARCHAR(128) NOT NULL DEFAULT ''"),
            ("preference_type", "VARCHAR(32) NOT NULL DEFAULT ''"),
            ("investment_preference", "TEXT"),
            ("incubation_info", "TEXT"),
            ("location", "VARCHAR(128)"),
            ("investment_experience", "TEXT"),
            ("tech_adaptability", "VARCHAR(64)"),
            ("high_net_worth", "VARCHAR(16)"),
            ("expected_investment", "VARCHAR(64)")
        ]
        success_count = 0
        for col_name, col_definition in migrations:
            try:
                sql = f"ALTER TABLE lead ADD COLUMN {col_name} {col_definition};"
                db.session.execute(db.text(sql))
                db.session.commit()
                print(f"✅ 成功添加列: {col_name}")
                success_count += 1
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"ℹ️  列已存在: {col_name}")
                else:
                    print(f"❌ 添加列失败 {col_name}: {e}")
        print(f"🎉 运行时迁移完成，成功添加 {success_count} 列")
        return True
    except Exception as e:
        print(f"❌ 运行时迁移失败: {e}")
        return False
