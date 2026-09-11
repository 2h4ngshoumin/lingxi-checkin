# 灵犀每日自动签到

基于 Playwright 的灵犀网页版（lingxi.kdocs.cn）每日自动签到脚本。

## 功能特性

- 登录态持久化：首次扫码登录后保存 cookie，后续无头运行
- 自动进入任务中心，识别签到按钮状态
- 支持 systemd timer 或 crontab 定时执行
- 双通道日志：journald + 文件日志
- 防重复签到：识别冷却状态
- ARM64 兼容（统信 UOS 验证）

## 环境要求

- Python 3.9+（推荐 3.10）
- Playwright 及 Chromium 内核
- Linux 系统

注意：Playwright 需要 Python 3.9+，系统自带的 Python 3.7 无法安装，请先编译安装 Python 3.10。

## 快速开始

### 1. 安装依赖

    bash install.sh

### 2. 首次登录

    python3.10 lingxi_checkin.py --login

浏览器弹出后扫码登录，进入灵犀主界面后回终端按 Enter 保存登录态。

### 3. 测试

    python3.10 lingxi_checkin.py --dry-run

## 配置定时任务

### 方案 A：systemd timer（推荐）

    mkdir -p ~/.config/systemd/user
    cp systemd/lingxi-checkin.service ~/.config/systemd/user/
    cp systemd/lingxi-checkin.timer ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now lingxi-checkin.timer
    sudo loginctl enable-linger $USER

### 方案 B：crontab

    bash setup_cron.sh

## 日志查看

    journalctl --user -u lingxi-checkin.service -n 50
    tail -f ~/lingxi-checkin/checkin.log

## 常见问题

### pip install playwright 报 No matching distribution found

Python 版本低于 3.9。编译安装 Python 3.10 后，用 python3.10 -m pip install playwright。

### cookie 过期

    rm -f cookies.json
    python3.10 lingxi_checkin.py --login

### 提示未能进入任务中心

灵犀网页改版，JS 选择器失效。检查 enter_task_center 和 do_checkin 中的选择器，按新页面结构调整。

## 免责声明

- 本项目仅供个人学习与技术研究使用。
- 使用本脚本产生的任何后果由使用者自行承担。
- 请遵守灵犀平台的服务条款。
- cookies.json 包含登录凭证，切勿分享或上传到公开仓库。

## License

MIT
