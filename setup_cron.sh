#!/usr/bin/env bash
# 灵犀自动签到 - crontab 一键写入脚本
# 用法：bash setup_cron.sh
set -e

# ========== 可修改参数 ==========
CRON_TIME="0 8 * * *"                   # 默认每天 08:00 执行
PROJECT_DIR="$HOME/lingxi-checkin"      # 项目目录
LOG_FILE="$PROJECT_DIR/checkin.log"     # 日志文件
TASK_NAME="lingxi_checkin"              # 任务标识（用于去重）
# ================================

echo "==> [1/5] 检查项目目录"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ 目录不存在：$PROJECT_DIR"
  exit 1
fi
if [ ! -f "$PROJECT_DIR/lingxi_checkin.py" ]; then
  echo "❌ 未找到脚本：$PROJECT_DIR/lingxi_checkin.py"
  exit 1
fi

echo "==> [2/5] 查找 python3.10 路径"
PYTHON_BIN="$(command -v python3.10 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "❌ 未找到 python3.10，请先编译安装 Python 3.10"
  exit 1
fi
echo "    Python 路径: $PYTHON_BIN"

echo "==> [3/5] 检查 Playwright 是否可用"
if ! "$PYTHON_BIN" -c "import playwright" 2>/dev/null; then
  echo "❌ python3.10 中未安装 playwright，请先执行："
  echo "    $PYTHON_BIN -m pip install playwright"
  exit 1
fi

echo "==> [4/5] 写入 crontab"
CRON_LINE="$CRON_TIME cd $PROJECT_DIR && $PYTHON_BIN lingxi_checkin.py >> $LOG_FILE 2>&1"

# 获取当前 crontab（可能为空）
CURRENT_CRON="$(crontab -l 2>/dev/null || true)"

# 移除旧的同名任务（按脚本名去重）
CLEANED_CRON="$(echo "$CURRENT_CRON" | grep -v "lingxi_checkin.py" || true)"

# 追加新任务
NEW_CRON="$(printf "%s\n%s\n" "$CLEANED_CRON" "$CRON_LINE" | sed '/^$/d')"

echo "$NEW_CRON" | crontab -

echo "    已写入：$CRON_LINE"

echo "==> [5/5] 验证"
echo "----- 当前 crontab -----"
crontab -l
echo "------------------------"
echo "✅ 完成。日志文件：$LOG_FILE"
echo "   查看日志：tail -f $LOG_FILE"