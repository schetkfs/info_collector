#!/usr/bin/env bash
# 一键部署：完整RWA信息采集系统
# 适用：Ubuntu 20.04/22.04+
set -Eeuo pipefail

########## 可配置变量 ##########
DOMAIN="rwa.yuansheng.net.cn"
EMAIL="1254965564@qq.com"         # 用于 Let's Encrypt；开启 HTTPS 时必填
ENABLE_TLS=0                    # 0 仅 HTTP；1 同时签发 HTTPS 并自动跳转

APP_USER="infoapp"
APP_DIR="/opt/info-collector"
SERVICE_NAME="info-collector"
APP_PORT="8000"

ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Jds@123456"
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

# 代码文件请手动上传或同步到 ${APP_DIR}
# 如需自动写入可参考 deploy_info_collector.sh 的写法

SESSION_COOKIE_SECURE_VAL="0"
if [[ "${ENABLE_TLS}" -eq 1 ]]; then
  SESSION_COOKIE_SECURE_VAL="1"
fi

echo "==> 写入 systemd 服务"
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
cat > /etc/nginx/sites-available/${SERVICE_NAME} <<'NGINX'
server {
  listen 80;
  server_name ${DOMAIN};

  location / {
    proxy_pass http://127.0.0.1:${APP_PORT};
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
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
    if command -v ufw >/dev/null 2>&1; then
      if ufw status | grep -q "Status: active"; then
        ufw allow 'Nginx Full' || true
      fi
    fi
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
