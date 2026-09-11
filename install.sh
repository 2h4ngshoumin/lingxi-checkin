#!/usr/bin/env bash
# 灵犀自动签到 - Linux 一键环境安装脚本
# 用法：bash install.sh
set -e

echo "==> [1/4] 检查 python3"
if ! command -v python3 >/dev/null 2>&1; then
  echo "未检测到 python3，请先安装："
  echo "  Debian/Ubuntu:  sudo apt install python3 python3-pip"
  echo "  CentOS/RHEL:    sudo yum install python3 python3-pip"
  exit 1
fi
python3 --version

echo "==> [2/4] 安装 playwright"
python3 -m pip install playwright || python3 -m pip install --user playwright

echo "==> [3/4] 安装 Chromium 内核"
python3 -m playwright install chromium

echo "==> [4/4] 完成"
echo
echo "接下来两步："
echo "  1) 首次登录生成登录态：  python3 lingxi_checkin.py --login"
echo "  2) 测试：                python3 lingxi_checkin.py --dry-run"
echo "  3) 配置定时任务：        crontab -e   （内容见 crontab 文件）"
