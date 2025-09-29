# info_collector 部署流程

## 1. 服务器准备
- 购买云服务器，获取 root 账号和密码。
- 推荐 Ubuntu 20.04/22.04 系统。
- 使用 SSH 工具连接服务器。

## 2. 域名配置
- 购买域名并解析到服务器公网 IP（A 记录）。

## 3. GitHub SSH 免密登录
```bash
git config --global user.name "wenrui"
git config --global user.email "1254965564@qq.com"
ssh-keygen -t ed25519 -C "1254965564@qq.com"
cat ~/.ssh/id_ed25519.pub
```
将公钥添加到 GitHub > Settings > SSH and GPG keys。

## 4. 下载代码
```bash
cd /opt
git clone git@github.com:schetkfs/info_collector.git
cd info_collector
```

## 5. 部署应用
1. 修改 `deploy.sh` 里的域名、邮箱等变量。
2. 赋予执行权限并运行：
	```bash
	chmod +x deploy.sh
	./deploy.sh
	```

## 6. 访问和管理
- 采集页：http://你的域名/
- 后台：http://你的域名/admin/login
- 管理命令：
  ```bash
  systemctl status info-collector
  journalctl -u info-collector -f
  systemctl restart info-collector
  ```
- 数据库路径：`/opt/info-collector/data.db`
