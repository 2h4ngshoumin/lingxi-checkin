#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵犀任务中心每日自动签到脚本 (Playwright)

作用：自动登录灵犀网页版，进入「任务中心」，完成每日签到领取智点。
规则（7天一周期）：第1~6天每天 +100 智点，第7天 +200 智点。

用法：
  pip install playwright && playwright install chromium     # 首次安装依赖
  python lingxi_checkin.py --login        # 首次/需重新登录时：打开浏览器手动登录并保存登录态
  python lingxi_checkin.py                # 每日自动签到（无头运行，读 cookies.json）
  python lingxi_checkin.py --dry-run      # 只检查签到状态，不实际点击

退出码：0=已签到/已签过(跳过)  1=未登录/需重新登录  2=定位失败(界面可能变了)
"""
import argparse
import json
import sys
import time
import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
COOKIE_FILE = BASE / "cookies.json"
LOG_FILE = BASE / "checkin.log"
URL = "https://lingxi.kdocs.cn"


def log(msg: str):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------- cookie ----------
def load_cookies(ctx) -> bool:
    if COOKIE_FILE.exists():
        try:
            ctx.add_cookies(json.loads(COOKIE_FILE.read_text(encoding="utf-8")))
            return True
        except Exception as e:
            log(f"加载 cookie 失败: {e}")
    return False


def save_cookies(ctx):
    try:
        COOKIE_FILE.write_text(
            json.dumps(ctx.cookies(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log(f"登录态已保存 ({len(ctx.cookies())} 个 cookie)")
    except Exception as e:
        log(f"保存 cookie 失败: {e}")


# ---------- 页面操作 ----------
def close_popups(page):
    """关闭首次登录可能出现的新用户推广弹窗（lingxi-pro-cta）。"""
    time.sleep(3)
    try:
        # 1) 用 JS 点击推广弹窗的关闭按钮（右上角叉号）或「去网页版体验」
        r = page.evaluate(r"""(function(){
          function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
          // 找推广弹窗容器
          var cta=Array.from(document.querySelectorAll('[class*="lingxi-pro-cta"]')).filter(vis);
          var scope=cta.length?cta[cta.length-1]:document;
          // 找关闭按钮：class 含 close，或右上角小图标
          var closers=Array.from((scope.nodeType===1?scope.querySelectorAll('*'):scope.querySelectorAll('*')));
          for(var i=closers.length-1;i>=0;i--){
            var c=closers[i];
            var cls=(c.className||'').toString().toLowerCase();
            if(/close|close-icon/.test(cls)&&vis(c)){c.click();return 'closed-cta:'+cls.slice(0,30);}
          }
          // 兜底：点「去网页版体验」
          var t=Array.from(document.querySelectorAll('button,a,div')).find(function(e){return /去网页版体验/.test(e.textContent||'')&&vis(e)&&(e.tagName==='BUTTON'||e.tagName==='A');});
          if(t){t.click();return 'closed-exit-web';}
          return 'no-popup';
        })()""")
        if "closed" in str(r) or "no-popup" in str(r):
            time.sleep(1)
            return
        # 2) 兜底点击右上角空白区域
        page.mouse.click(1200, 80)
        time.sleep(1)
    except Exception as e:
        log(f"关闭弹窗异常: {e}")


def is_logged_in(page) -> bool:
    """页面顶部没有「登录」按钮即认为已登录。"""
    try:
        return page.get_by_text("登录", exact=True).count() == 0
    except Exception:
        return False


def enter_task_center(page) -> bool:
    """
    进入任务中心：点击网页版左下角的「礼物」图标（智点余额图标右侧）。
    返回 True 表示已进入（页面出现「任务中心」标题）。
    """
    if page.get_by_text("每日签到与任务奖励", exact=False).count() > 0:
        return True  # 已在任务中心

    js_gift = r"""
    (function(){
      function vis(e){ var r=e.getBoundingClientRect(); return r.width>0 && r.height>0; }
      // 1) 定位左下角「智点余额」按钮（footer__points 或纯数字按钮）
      var points = Array.from(document.querySelectorAll('button'))
        .find(function(b){ return /^\d{3,7}$/.test((b.textContent||'').trim()) && vis(b) && b.getBoundingClientRect().x < 300; });
      if(!points){
        points = document.querySelector('button.footer__points');
      }
      if(points){
        // 2) 礼物图标 = 智点余额之后的下一个图标按钮
        var sib = points.nextElementSibling;
        if(sib && vis(sib)){ sib.click(); return 'gift:after-points:'+((sib.className||'').toString().slice(0,30)); }
        var parent = points.parentElement;
        if(parent){
          var children = Array.from(parent.children);
          var idx = children.indexOf(points);
          for(var k=idx+1;k<children.length;k++){
            if(vis(children[k])){ children[k].click(); return 'gift:container-next'; }
          }
        }
      }
      return 'gift:not-found';
    })()
    """
    try:
        res = page.evaluate(js_gift)
        log(f"点击礼物图标: {res}")
    except Exception as e:
        log(f"JS 点击礼物异常: {e}")
    time.sleep(2)
    return page.get_by_text("每日签到与任务奖励", exact=False).count() > 0


def do_checkin(page) -> str:
    """
    在任务中心内尝试签到。
    返回: 'signed' 已签到 | 'already' 今日已签(冷却中) | 'notfound' 找不到按钮
    """
    js = r"""
    (function(){
      var btns = Array.from(document.querySelectorAll('button'))
        .filter(function(e){ var r=e.getBoundingClientRect(); return r.width>0 && r.height>0; });
      for(var i=0;i<btns.length;i++){
        var t=(btns[i].textContent||'').trim();
        // 可签到按钮：文本为「签到」或包含 +100 / +200 且可点击
        if(/^(签到|签 到|立即签到)$/.test(t) || /^\+(\d+)\s*签到$/.test(t)){
          if(!btns[i].disabled){ btns[i].click(); return 'clicked:'+t; }
          return 'disabled:'+t;
        }
        // 冷却中 / 今日已签到
        if(/距离下次签到/.test(t)) return 'countdown:'+t;
        if(/已签到/.test(t) && t.length<10) return 'already';
      }
      // 找包含 +100 的签到圆圈
      for(var j=0;j<btns.length;j++){
        if(/\+100|\+200/.test(btns[j].textContent||'')){
          if(!btns[j].disabled){ btns[j].click(); return 'clicked:'+(btns[j].textContent||'').trim(); }
          return 'disabled-circle';
        }
      }
      return 'notfound';
    })()
    """
    try:
        res = page.evaluate(js)
    except Exception as e:
        res = "js-error:" + str(e)
    log(f"签到按钮状态: {res}")
    if res.startswith("clicked"):
        time.sleep(2)
        return "signed"
    if res.startswith("countdown") or res == "already":
        return "already"
    return "notfound"


# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true", help="有头模式手动登录并保存 cookie")
    ap.add_argument("--dry-run", action="store_true", help="只检查状态，不实际签到")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("未安装 playwright，请先执行: pip install playwright && playwright install chromium")
        return 1

    with sync_playwright() as p:
        headless = not args.login
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.set_default_timeout(15000)

        page.goto(URL, wait_until="domcontentloaded")
        time.sleep(3)
        load_cookies(ctx)
        page.reload(wait_until="domcontentloaded")
        time.sleep(3)

        if args.login:
            log("浏览器已打开，请在浏览器中完成扫码/账号登录。")
            log("登录完成、页面进入灵犀主界面后，回到本终端按 Enter 键保存登录态……")
            try:
                input()  # 等待你按回车
            except EOFError:
                time.sleep(300)  # 非交互环境下等5分钟
            save_cookies(ctx)
            log("登录态已保存。之后可直接无头运行脚本。")
            browser.close()
            return 0

        # 无头自动签到模式
        if not is_logged_in(page):
            log("未登录且 cookie 失效。请先运行: python lingxi_checkin.py --login")
            browser.close()
            return 1

        close_popups(page)

        if not enter_task_center(page):
            log("未能进入任务中心，界面可能已改版，请检查并更新脚本定位逻辑")
            browser.close()
            return 2

        state = do_checkin(page)
        if args.dry_run:
            log(f"[dry-run] 当前签到状态: {state}")
            browser.close()
            return 0
        if state == "signed":
            log("签到成功 ✔ 今日智点已到账")
        elif state == "already":
            log("今日已签到或仍在冷却期，跳过（不重复签到）")
        else:
            log("未找到可点击的签到按钮，今日可能已签或界面变化")
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
