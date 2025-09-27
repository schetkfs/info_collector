# RWA投资与孵化信息采集系统

## 项目结构

```
info_collector/
├── app.py                 # Flask 主应用文件
├── instance/
│   └── data.db           # SQLite 数据库文件
├── static/               # 静态资源目录
│   ├── css/
│   │   └── style.css     # 样式文件
│   └── js/
│       └── form.js       # JavaScript 脚本
├── templates/            # HTML 模板目录
│   ├── base.html         # 基础模板
│   ├── form.html         # 信息采集表单
│   ├── success.html      # 提交成功页面
│   ├── login.html        # 管理员登录页面
│   └── admin.html        # 管理员后台页面
├── deploy_info_collector.sh  # 部署脚本
└── README.md             # 项目说明
```

## 文件分离说明

### 1. 静态资源分离
- **CSS**: `static/css/style.css` - 包含所有样式定义，支持响应式设计
- **JavaScript**: `static/js/form.js` - 表单交互逻辑，支持条件字段显示/隐藏

### 2. 模板分离
- **base.html**: 基础模板，定义了页面的基本结构和资源引用
- **form.html**: 信息采集表单页面
- **success.html**: 提交成功页面
- **login.html**: 管理员登录页面
- **admin.html**: 管理员后台数据展示页面

### 3. 代码优化
- 移除了 `render_template_string` 的使用
- 使用 Flask 标准的 `render_template` 方法
- 模板继承减少了重复代码
- 更好的代码可维护性和可扩展性

## 安装和运行

1. 安装依赖：
```bash
pip install flask flask-sqlalchemy
```

2. 运行应用：
```bash
python app.py
```

3. 访问地址：
- 信息采集表单：http://127.0.0.1:8000
- 管理员后台：http://127.0.0.1:8000/admin/login

## 环境变量配置

- `ADMIN_USERNAME`: 管理员用户名 (默认: admin)
- `ADMIN_PASSWORD`: 管理员密码 (默认: changeme)
- `SECRET_KEY`: Flask 会话密钥
- `SESSION_COOKIE_SECURE`: HTTPS 下发送 cookie (0/1)

## 功能特点

- 📋 **完整信息采集**: 涵盖基本信息、职业信息、投资偏好等
- 🔄 **条件字段显示**: 根据投资偏好自动显示相关必填项
- 📱 **响应式设计**: 适配手机和桌面设备
- 🛡️ **数据验证**: 前端和后端双重验证
- 📊 **后台管理**: 分页显示、CSV导出功能
- 🎨 **现代UI**: 深色主题，用户体验优秀