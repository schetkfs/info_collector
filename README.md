# info_collector

我现在需要一个程序来收集用户的个人信息：姓名，性别，年龄，所在行业，行业内职务，愿意用作投资的金额，RWA投资与RWA孵化哪个更感兴趣
我是一个小白，我该如何使用这个程序，将它应用到实际当中
给我详细解释一下路径B的运作方式
我收集后的数据应当在哪里查看

在你的 Ubuntu 服务器上，用 Flask + SQLite + Gunicorn + Nginx + HTTPS 搭一套「前端信息采集页 + 管理员后台展示 + CSV 导出」的最小可用系统（字段：姓名、性别、年龄）。

设计点：

访客端：/ 提交表单（姓名/性别/年龄）。

后台：/admin 登录后查看列表、分页、导出 CSV。

数据：SQLite 持久化，记录 IP、User-Agent 与提交时间。

安全：后台登录（环境变量设置用户名/密码）、HTTPS、隐藏真实 Gunicorn 端口。


代码管理工具：
echo "# info_collector" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/schetkfs/info_collector.git
git push -u origin main

git remote add origin https://github.com/schetkfs/info_collector.git
git branch -M main
git push -u origin main



**如何在github上配置，让服务器不输密码？**
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的邮箱"ß

一. 在服务器上生成 SSH key
ssh-keygen -t ed25519 -C "1254965564@qq.com"

二. 查看并复制公钥内容
cat ~/.ssh/id_ed25519.pub
复制输出的那一行（以 ssh-ed25519 或 ssh-rsa 开头，一串很长）。

三. 添加 SSH key 到 GitHub
1、登录你的 GitHub 账号
2、点击右上角头像 > Settings
3、左边菜单点 SSH and GPG keys
4、点 New SSH key
5、Title 随便填（比如 "server-2025"）
6、Key 内容粘贴你刚刚复制的那一行
7、点 Add SSH key


下载代码：
git clone git@github.com:schetkfs/info_collector.git

cd /opt

cd info_collector

chmod +x deploy.sh

