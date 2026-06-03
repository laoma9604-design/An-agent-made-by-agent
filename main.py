# Herrs v5 — 双模式明确区分 + UI质感升级
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, json, os, sys, subprocess, time as _time, collections, datetime, urllib.request, urllib.parse, tempfile, shutil, webbrowser

# 抑制 SSL 警告（使用本地代理时）
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests

# ── Debug ──
DEBUG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "herrs_debug.log")
def debug(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except: pass

debug("=== Herrs v5 启动 ===")

# ── 代理配置 ──
def get_proxy_config():
    """检测代理配置，优先从配置文件读取，其次读环境变量"""
    # 从配置文件读
    lc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "herrs_config.json")
    try:
        if os.path.exists(lc):
            cfg = json.load(open(lc))
            if cfg.get("proxy"):
                proxy_url = cfg["proxy"]
                debug(f"使用配置代理: {proxy_url}")
                return {"http": proxy_url, "https": proxy_url}
    except: pass
    # 从环境变量
    for env_var in ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"]:
        val = os.environ.get(env_var)
        if val:
            debug(f"使用环境变量代理 ({env_var}): {val}")
            return {"http": val, "https": val}
    # ── 自动扫描本机代理端口（兜底）──
    debug("未检测到代理配置，启动自动扫描...")
    candidates = [
        "http://127.0.0.1:7890",   # Clash default
        "http://127.0.0.1:7891",   # Clash mixed
        "http://127.0.0.1:10809",  # v2ray/clash mixed
        "http://127.0.0.1:1080",   # SOCKS5
        "http://127.0.0.1:8080",   # common HTTP
        "http://127.0.0.1:8118",   # privoxy
    ]
    for proxy_url in candidates:
        try:
            r = requests.get("https://www.baidu.com",
                           proxies={"http": proxy_url, "https": proxy_url},
                           timeout=4, verify=False)
            if r.status_code == 200:
                debug(f"自动检测到代理: {proxy_url}")
                return {"http": proxy_url, "https": proxy_url}
        except Exception:
            continue
    debug("自动扫描未发现可用代理")
    return None

# ── 代理扫描结果缓存（避免每次启动重复扫）──
def _save_auto_proxy(proxies):
    """把自动检测到的代理写入配置文件，下次直接读"""
    lc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "herrs_config.json")
    try:
        cfg = {}
        if os.path.exists(lc):
            cfg = json.load(open(lc))
        if proxies and not cfg.get("proxy"):
            cfg["proxy"] = proxies["http"]
            json.dump(cfg, open(lc, "w"), indent=2)
            debug(f"已将自动检测的代理写入配置: {proxies['http']}")
    except Exception:
        pass

_proxy = get_proxy_config()
if _proxy:
    _save_auto_proxy(_proxy)

HERMES_HOME = os.path.expandvars(r"%LOCALAPPDATA%\hermes")
SKILLS_DIR = os.path.join(HERMES_HOME, "skills")
MY_SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_skills")

# ── App 目录 ──
APP_NAME = "Herrs"
def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════
# 工具定义（18个）
# ═══════════════════════════════════════════
TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "读取文件内容", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "创建或覆盖文件", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "列出目录内容", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "目录路径，默认当前"}}, "required": []}}},
    {"type": "function", "function": {"name": "search_files", "description": "搜索文件（名称+内容）", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}, "file_glob": {"type": "string"}, "search_content": {"type": "boolean"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "执行终端命令", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "description": "超时秒数，默认120"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "run_python", "description": "执行 Python 代码", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
    {"type": "function", "function": {"name": "disk_info", "description": "磁盘空间", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "get_env", "description": "系统环境信息", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "process_list", "description": "进程列表", "parameters": {"type": "object", "properties": {"top": {"type": "integer", "description": "显示前N个"}}, "required": []}}},
    {"type": "function", "function": {"name": "web_search", "description": "搜索网页（Bing）", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}, "max_results": {"type": "integer", "description": "最多返回条数，默认5"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_fetch", "description": "获取网页内容", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "网页地址"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "download_file", "description": "下载文件到本地", "parameters": {"type": "object", "properties": {"url": {"type": "string"}, "save_path": {"type": "string", "description": "保存路径，默认下载到桌面"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "open_file", "description": "用默认程序打开文件/文件夹/网址", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "clipboard_get", "description": "读取剪贴板内容", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "clipboard_set", "description": "设置剪贴板内容", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "notify", "description": "弹出桌面通知", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "message": {"type": "string"}}, "required": ["title", "message"]}}},
    {"type": "function", "function": {"name": "screenshot", "description": "截屏并保存", "parameters": {"type": "object", "properties": {"save_path": {"type": "string", "description": "保存路径，默认桌面"}}, "required": []}}},
    {"type": "function", "function": {"name": "kill_process", "description": "强制结束进程", "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "进程名(如 notepad.exe)"}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "datetime_now", "description": "获取当前日期时间", "parameters": {"type": "object", "properties": {}, "required": []}}},
]

def execute_tool(name, args):
    try:
        if name == "read_file":
            p = args.get("path", "")
            if not os.path.exists(p): return f"文件不存在: {p}"
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return f.read()[:10000] or "(空文件)"
        elif name == "write_file":
            p, c = args.get("path", ""), args.get("content", "")
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as f: f.write(c)
            return f"已写入 {p} ({len(c)} 字符)"
        elif name == "list_files":
            p = args.get("path") or "."
            if not os.path.exists(p): return f"路径不存在: {p}"
            items = sorted(os.listdir(p))
            r = [f"  {'[DIR]' if os.path.isdir(os.path.join(p,i)) else ''} {i}" for i in items[:100]]
            return "\n".join(r) or "(空)"
        elif name == "search_files":
            pat, sp, fg = args.get("pattern",""), args.get("path","."), args.get("file_glob","*")
            import fnmatch
            results = []
            for root, dirs, files in os.walk(sp):
                for f in files:
                    if fnmatch.fnmatch(f, fg) and pat.lower() in f.lower():
                        results.append(os.path.join(root, f))
                if len(results) > 50: break
            return "\n".join(results[:30]) if results else f"未找到 '{pat}'"
        elif name == "run_command":
            cmd, to = args.get("command",""), args.get("timeout",60)
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                    encoding="gbk", errors="replace",
                                    timeout=to, cwd=os.path.expanduser("~"))
                return (r.stdout.strip() or r.stderr.strip() or "(无输出)")[:5000]
            except subprocess.TimeoutExpired:
                return f"超时 ({to}s)"
        elif name == "disk_info":
            import shutil
            result = []
            for d in ["C:\\", "D:\\", "E:\\"]:
                try:
                    u = shutil.disk_usage(d)
                    result.append(f"  {d} {u.free/2**30:.1f}GB 空闲 / {u.total/2**30:.1f}GB ({(1-u.free/u.total)*100:.0f}% 已用)")
                except: pass
            return "\n".join(result)
        elif name == "get_env":
            return f"用户名: {os.environ.get('USERNAME','?')}\n主目录: {os.path.expanduser('~')}\n桌面: {os.path.expanduser('~/Desktop')}\nOS: Windows\nPython: {sys.version.split()[0]}"
        elif name == "process_list":
            top = args.get("top", 10)
            try:
                r = subprocess.run("tasklist /fo csv /nh", shell=True,
                                    capture_output=True, text=True,
                                    encoding="gbk", errors="replace", timeout=10)
                lines = r.stdout.strip().split("\n")[:top*2]
                return "\n".join(lines) if lines else "无法获取"
            except: return "获取进程失败"
        elif name == "run_python":
            code = args.get("code", "")
            try:
                import io, contextlib
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    exec(code, {"__builtins__": __builtins__}, {})
                return stdout.getvalue() or "(执行成功，无输出)"
            except Exception as e:
                return f"Python 错误: {e}"
        elif name == "web_search":
            query = args.get("query", "")
            max_r = args.get("max_results", 5)
            try:
                import requests as _req, urllib3, re
                urllib3.disable_warnings()
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                req_kw = {"headers": headers, "timeout": 15, "verify": False}
                if _proxy:
                    req_kw["proxies"] = _proxy
                r = _req.get(f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
                           **req_kw)
                html = r.text
                # Bing搜索结果：匹配 cite (链接) + a标签（标题）
                cites = re.findall(r'<cite>(.*?)</cite>', html, re.DOTALL)
                links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
                # 过滤掉bing自身链接，保留外部结果
                results = [(re.sub(r'<[^>]+>', '', text).strip(), href)
                          for href, text in links
                          if 'bing.com' not in href and 'microsoft.com' not in href]
                seen = set(); out = []
                for title, url in results:
                    if len(title) < 10 or url in seen:
                        continue
                    seen.add(url)
                    # 匹配cite
                    cite_text = ""
                    for c in cites:
                        clean = re.sub(r'<[^>]+>', '', c).strip()
                        if clean and clean.split('/')[0].rstrip() in url:
                            cite_text = clean; break
                    out.append(f"{len(out)+1}. {title}\n   {cite_text or url}\n   {url}")
                    if len(out) >= max_r:
                        break
                return "\n\n".join(out) if out else f"未找到 '{query}' 的结果"
            except Exception as e:
                return f"搜索失败: {e}"
        elif name == "web_fetch":
            url = args.get("url", "")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"})
                html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")
                import re
                text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:8000] if text else "(空内容)"
            except Exception as e:
                return f"获取失败: {e}"
        elif name == "download_file":
            url = args.get("url", "")
            save = args.get("save_path") or os.path.join(os.path.expanduser("~/Desktop"), url.split("/")[-1] or "download")
            try:
                urllib.request.urlretrieve(url, save)
                size = os.path.getsize(save)
                return f"已下载到 {save} ({size/1024:.1f} KB)"
            except Exception as e:
                return f"下载失败: {e}"
        elif name == "open_file":
            p = args.get("path", "")
            webbrowser.open(p)
            return f"已打开: {p}"
        elif name == "clipboard_get":
            try:
                r = tk.Tk(); r.withdraw(); data = r.clipboard_get(); r.destroy(); return data
            except:
                return "(剪贴板为空或无法访问)"
        elif name == "clipboard_set":
            text = args.get("text", "")
            r = tk.Tk(); r.withdraw(); r.clipboard_clear(); r.clipboard_append(text); r.update(); r.destroy()
            return "已复制到剪贴板"
        elif name == "notify":
            title, msg = args.get("title", ""), args.get("message", "")
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, msg, duration=5, threaded=True)
            except:
                subprocess.Popen(["powershell", "-Command",
                    f"$n=New-Object Windows.UI.Notifications.ToastNotification;"
                    f"echo '{title}: {msg}'"], shell=True)
            return f"已通知: {title}"
        elif name == "screenshot":
            save = args.get("save_path") or os.path.join(os.path.expanduser("~/Desktop"), f"screenshot_{datetime.datetime.now():%H%M%S}.png")
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(save)
                return f"截图已保存: {save} ({img.size[0]}x{img.size[1]})"
            except Exception as e:
                return f"截图失败 (需要 pip install pillow): {e}"
        elif name == "kill_process":
            pname = args.get("name", "")
            r = subprocess.run(f"taskkill /f /im {pname}", shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout.strip() or r.stderr.strip() or f"已结束: {pname}"
        elif name == "datetime_now":
            now = datetime.datetime.now()
            return f"{now:%Y-%m-%d %H:%M:%S} ({now:%A}) 第{now.isocalendar()[1]}周"
        return f"未知工具: {name}"
    except Exception as e:
        return f"工具错误: {e}"

def _check_permission_issue(tool_name, args, result):
    """检测工具执行结果中的权限问题，返回提示信息"""
    result_lower = result.lower()
    # 文件写入权限
    if tool_name == "write_file":
        if "permission" in result_lower or "access denied" in result_lower or "拒绝访问" in result:
            return f"文件写入被拒绝: {args.get('path','?')}\n    → 请以管理员身份运行，或将文件保存到桌面/文档文件夹"
    # 命令执行权限
    if tool_name == "run_command":
        if "access denied" in result_lower or "requires elevation" in result_lower or "拒绝访问" in result:
            return "该命令需要管理员权限\n    → 请右键→以管理员身份运行 Herrs"
    if tool_name == "kill_process":
        if "access denied" in result_lower or "拒绝访问" in result:
            return "结束该进程需要管理员权限\n    → 请右键→以管理员身份运行 Herrs"
    if tool_name == "screenshot":
        if "access" in result_lower and "denied" in result_lower:
            return "截屏权限不足\n    → 检查Windows隐私设置→屏幕截图权限"
    return None

# ═══════════════════════════════════════════
# DeepSeek API（工具模式 = function calling）
# ═══════════════════════════════════════════
def call_deepseek_with_tools(messages, api_key, progress_cb=None):
    import requests
    system = {"role": "system", "content": (
        "你是 Herrs，功能完整的 AI 桌面助手。你可以：读取/写入文件、浏览目录、搜索文件、"
        "执行终端命令和 Python 代码、查看磁盘/进程/环境信息、搜索网页和抓取内容、"
        "下载文件、打开文件/网址、读写剪贴板、截屏、结束进程、桌面通知、查看时间。"
        "优先使用工具直接完成任务，不要只给文字建议。用中文回复，简洁高效。"
    )}
    full = [system] + list(messages[-10:])
    
    # 请求配置（代理 + SSL）
    req_kwargs = {"timeout": (10, 120)}  # (连接超时, 读取超时)
    if _proxy:
        req_kwargs["proxies"] = _proxy
        if "127.0.0.1" in str(_proxy) or "localhost" in str(_proxy):
            req_kwargs["verify"] = False  # 本地代理可能不验证SSL
    
    for loop in range(15):
        try:
            if progress_cb: progress_cb("📡 调用 DeepSeek API...", phase="api")
            debug(f"API请求 #{loop+1}: messages={len(full)}, proxy={bool(_proxy)}")
            
            resp = requests.post("https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": full, "tools": TOOLS, "max_tokens": 4096},
                **req_kwargs)
            
            if resp.status_code != 200:
                err_detail = resp.text[:300]
                debug(f"API错误 [{resp.status_code}]: {err_detail}")
                if resp.status_code in (401, 403):
                    return f"🔑 API Key 无效或过期 [{resp.status_code}]"
                elif resp.status_code == 429:
                    import time as _t
                    if progress_cb: progress_cb(f"⏳ API限流 [{resp.status_code}]，等3秒重试...", phase="wait")
                    _t.sleep(3)
                    continue
                return f"🌐 API 错误 [{resp.status_code}]: {err_detail}"
            
            if progress_cb: progress_cb("🧠 模型思考中...", phase="model")
            data = resp.json()
            msg = data["choices"][0]["message"]
            
            if msg.get("tool_calls"):
                if progress_cb: progress_cb(f"🔧 模型决定调用 {len(msg['tool_calls'])} 个工具", phase="decide")
                full.append(msg)
                for i, tc in enumerate(msg["tool_calls"]):
                    tn = tc["function"]["name"]
                    try:
                        ta = json.loads(tc["function"]["arguments"])
                    except:
                        ta = {}
                    if progress_cb: progress_cb(f"🔧 执行工具 ({i+1}/{len(msg['tool_calls'])}): {tn}", phase="tool")
                    result = execute_tool(tn, ta)
                    # 检测权限问题
                    perm_issue = _check_permission_issue(tn, ta, result)
                    if perm_issue and progress_cb:
                        progress_cb(f"⚠️ 权限提示: {perm_issue}", phase="perm")
                    full.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                if progress_cb: progress_cb("📊 工具结果已返回，等待模型处理...", phase="done")
                continue
            
            if progress_cb: progress_cb("✍️ 生成回复中...", phase="done")
            return msg.get("content", "")
            
        except requests.exceptions.ProxyError as e:
            debug(f"代理错误: {e}")
            return f"🔌 代理连接失败 ({_proxy.get('http','?')}): 请检查代理是否在运行，或在配置中移除代理"
        except requests.exceptions.SSLError as e:
            debug(f"SSL错误: {e}")
            # 策略1: 先关SSL验证试试
            if req_kwargs.get("verify") is not False:
                req_kwargs["verify"] = False
                debug("关闭SSL验证重试...")
                continue
            # 策略2: verify=False 仍报错（如 EOF）→ 延迟重试，服务端临时问题
            if loop < 2:
                import time as _t
                wait = (loop + 1) * 2
                if progress_cb:
                    progress_cb(f"🔒 SSL握手异常，{wait}秒后重试 ({loop+1}/2)...", phase="wait")
                debug(f"SSL重试 {loop+1}/2，等待{wait}s...")
                _t.sleep(wait)
                continue
            return f"🔒 SSL连接失败（已重试2次）: {str(e)[:120]}"
        except requests.exceptions.ConnectionError as e:
            debug(f"连接错误: {e}")
            if "getaddrinfo failed" in str(e) or "Name or service not known" in str(e):
                return f"🌐 DNS解析失败: 检查网络连接"
            return f"🔌 网络连接失败: 请检查网络/代理\n  ({str(e)[:150]})"
        except requests.exceptions.Timeout as e:
            debug(f"超时: {e}")
            return f"⏰ 请求超时 (120s): 可能网络较慢或模型负载高，请重试"
        except Exception as e:
            debug(f"未知错误: {e}")
            return f"❌ 连接异常: {e}"
    
    return "⏰ 达到最大工具调用轮数(15轮)"

# ═══════════════════════════════════════════
# Skills 加载
# ═══════════════════════════════════════════
SKILL_CN = {
    "arxiv": "论文搜索", "github-code-review": "代码审查", "ocr-and-documents": "PDF提取",
    "powerpoint": "PPT制作", "obsidian": "Obsidian", "notion": "Notion",
    "mumu-emulator": "MuMu模拟器", "nano-pdf": "PDF编辑", "airtable": "Airtable",
    "google-workspace": "谷歌办公", "himalaya": "邮件", "linear": "Linear",
    "maps": "地图", "polymarket": "预测市场", "blogwatcher": "博客监控",
    "youtube-content": "YouTube", "comfyui": "ComfyUI绘图", "pixel-art": "像素画",
    "ascii-art": "字符画", "manim-video": "数学动画", "excalidraw": "手绘风格图",
    "architecture-diagram": "架构图", "sketch": "原型草图", "p5js": "p5.js创意编程",
    "pretext": "浏览器Demo", "popular-web-designs": "网页设计参考", "claude-design": "网页设计",
    "baoyu-article-illustrator": "文章配图", "baoyu-comic": "知识漫画", "baoyu-infographic": "信息图",
    "humanizer": "文本人性化", "gif-search": "GIF搜索", "ascii-video": "字符视频",
    "songsee": "音频分析", "huggingface-hub": "HuggingFace", "jupyter-live-kernel": "Jupyter",
    "llm-wiki": "LLM知识库", "godmode": "AI越狱", "dspy": "DSPy编程",
    "heartmula": "AI音乐", "touchdesigner-mcp": "TouchDesigner", "native-mcp": "MCP连接",
    "hermes-agent": "Hermes配置", "github-auth": "GitHub登录", "github-issues": "Issues",
    "github-pr-workflow": "PR流程", "github-repo-management": "仓库管理",
    "requesting-code-review": "代码自查", "test-driven-development": "TDD测试",
    "subagent-driven-development": "子代理", "systematic-debugging": "系统调试",
    "writing-plans": "编写方案", "plan": "制定计划", "spike": "快速验证",
    "claude-code": "Claude编程", "codex": "Codex编程", "opencode": "OpenCode",
    "codebase-inspection": "代码库分析", "node-inspect-debugger": "Node调试",
    "python-debugpy": "Python调试", "hermes-agent-skill-authoring": "Skill编写",
    "hermes-s6-container-supervision": "容器管理", "debugging-hermes-tui-commands": "Hermes调试",
    "webhook-subscriptions": "Webhook", "kanban-orchestrator": "看板编排",
    "kanban-worker": "看板工人", "kanban-codex-lane": "看板Codex",
    "design-md": "设计文档", "findmy": "查找设备", "imessage": "iMessage",
    "apple-notes": "苹果备忘录", "apple-reminders": "苹果提醒",
    "pokemon-player": "宝可梦", "minecraft-modpack-server": "MC服务器",
    "openhue": "智能灯控", "creative-ideation": "创意点子", "dogfood": "QA测试",
    "research-paper-writing": "论文写作", "windows-diagnostics": "Win诊断",
    "xurl": "链接处理", "teams-meeting-pipeline": "Teams会议",
    "macos-computer-use": "Mac操控", "zhexue-methods": "玄学数术",
    "spotify": "Spotify", "songwriting-and-ai-music": "AI歌曲创作",
    "canvas-design": "画布设计",
}

CATEGORY_CN = {
    "software-development": "💻 软件开发", "creative": "🎨 创意设计",
    "productivity": "📊 办公效率", "github": "🐙 GitHub",
    "autonomous-ai-agents": "🤖 AI代理", "mlops": "🧠 AI/ML",
    "media": "🎵 媒体", "research": "🔬 研究", "apple": "🍎 Apple",
    "devops": "⚙️ DevOps", "gaming": "🎮 游戏", "dogfood": "🐶 测试",
    "email": "📧 邮件", "note-taking": "📝 笔记", "smart-home": "🏠 智能家居",
    "red-teaming": "🔴 红队", "data-science": "📈 数据科学", "mcp": "🔌 MCP",
    "zhexue-methods": "🔮 玄学", "social-media": "📱 社交",
}

def load_skills():
    groups = collections.OrderedDict()
    # ⭐ 我的技能
    my = []
    if os.path.exists(MY_SKILLS_DIR):
        for sn in os.listdir(MY_SKILLS_DIR):
            if os.path.isfile(os.path.join(MY_SKILLS_DIR, sn, "SKILL.md")):
                my.append({"name": sn, "label": sn, "category": "__my__"})
    if my:
        groups["⭐ 我的技能"] = sorted(my, key=lambda s: s["label"])
    # 系统技能
    if not os.path.exists(SKILLS_DIR): return groups
    cat_skills = collections.OrderedDict()
    for cat in sorted(os.listdir(SKILLS_DIR)):
        cp = os.path.join(SKILLS_DIR, cat)
        if not os.path.isdir(cp): continue
        for sn in sorted(os.listdir(cp)):
            smd = os.path.join(cp, sn, "SKILL.md")
            if os.path.isfile(smd):
                if cat not in cat_skills: cat_skills[cat] = []
                cat_skills[cat].append({"name": sn, "label": SKILL_CN.get(sn, sn), "category": cat})
    for cat, slist in cat_skills.items():
        cn = CATEGORY_CN.get(cat, f"📁 {cat}")
        slist.sort(key=lambda s: s["label"])
        groups[cn] = slist
    return groups

def get_api_key():
    lc = os.path.join(get_app_dir(), "herrs_config.json")
    if os.path.exists(lc):
        try:
            with open(lc) as f:
                if json.load(f).get("api_key"): return json.load(open(lc))["api_key"]
        except: pass
    for e in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
        if os.environ.get(e): return os.environ[e]
    envf = os.path.join(HERMES_HOME, ".env")
    if os.path.exists(envf):
        try:
            with open(envf) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        if "API_KEY" in k.upper():
                            return v.strip().strip('"').strip("'")
        except: pass
    return ""

# ═══════════════════════════════════════════
# 主窗口 — v5 双模式 + 质感升级
# ═══════════════════════════════════════════
class HerrsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Herrs")
        self.root.geometry("1000x720")
        self.root.minsize(750, 500)

        # ── 配色体系 ──
        self.c = {
            "bg":        "#0f0f1a",   # 最深背景
            "bg_card":   "#1a1a2e",   # 卡片/面板
            "bg_input":  "#12122a",   # 输入框
            "bg_hover":  "#252550",   # 悬停
            "fg":        "#e0e0f0",   # 主文字
            "fg_dim":    "#8888aa",   # 次要文字
            "accent":    "#6c5ce7",   # 主色调（紫色）
            "accent2":   "#a29bfe",   # 浅紫
            "danger":    "#e94560",   # 红色高亮
            "success":   "#00cec9",   # 绿色
            "warn":      "#fdcb6e",   # 黄色
            "bubble_u":  "#2d1b69",   # 用户气泡背景
            "bubble_a":  "#1a1a2e",   # AI气泡背景
            "border":    "#2a2a4a",   # 边框线
        }
        self.root.configure(bg=self.c["bg"])

        self.api_key = get_api_key()
        self.skill_groups = load_skills()
        self.selected_skills = set()
        self.engine = "tools"       # "tools" | "simple"
        self.messages = []
        self._collapsed_cats = set()
        self._skill_vars = {}
        self._skills_visible = True  # 纯聊模式隐藏面板

        self._build_ui()
        self._load_skills_ui()
        self._apply_engine_ui()

        self.root.bind("<Control-Return>", lambda e: self.send_message())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._add_message(APP_NAME, "👋 Herrs v5 — 🛠️工具模式 · 左侧Skills可用 · Ctrl+Enter发送", "system")

    # ── 构建 UI ──
    def _build_ui(self):
        c = self.c

        # ═══ 顶部栏 ═══
        topbar = tk.Frame(self.root, bg=c["bg_card"], height=44)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        # Logo
        logo = tk.Label(topbar, text="⚡ Herrs", fg=c["accent2"], bg=c["bg_card"],
                        font=("Segoe UI", 14, "bold"))
        logo.pack(side="left", padx=(16, 12))

        # 分隔
        tk.Frame(topbar, bg=c["border"], width=1, height=24).pack(side="left", padx=(0, 10))

        # 模式切换 — 胶囊按钮
        self.mode_frame = tk.Frame(topbar, bg=c["bg_card"])
        self.mode_frame.pack(side="left")

        self.btn_tools = tk.Label(self.mode_frame, text="  🛠️  工具模式  ", fg="white",
                                  bg=c["accent"], font=("Segoe UI", 10, "bold"),
                                  cursor="hand2", padx=12, pady=5)
        self.btn_tools.pack(side="left")
        self.btn_tools.bind("<Button-1>", lambda e: self._switch_engine("tools"))
        self.btn_tools.bind("<Enter>", lambda e: self._on_hover(e, self.btn_tools, True))
        self.btn_tools.bind("<Leave>", lambda e: self._on_hover(e, self.btn_tools, False))

        self.btn_simple = tk.Label(self.mode_frame, text="  💬  纯聊模式  ", fg=c["fg_dim"],
                                   bg=c["bg_card"], font=("Segoe UI", 10),
                                   cursor="hand2", padx=12, pady=5)
        self.btn_simple.pack(side="left")
        self.btn_simple.bind("<Button-1>", lambda e: self._switch_engine("simple"))
        self.btn_simple.bind("<Enter>", lambda e: self._on_hover(e, self.btn_simple, True))
        self.btn_simple.bind("<Leave>", lambda e: self._on_hover(e, self.btn_simple, False))

        # 右上角 API 按钮
        key_text = "🔑 已配置"
        if _proxy:
            key_text += " · 代理"
        elif not self.api_key:
            key_text = "⚠️ 设置API"
        self.key_btn = tk.Label(topbar, text=key_text,
                                fg=c["warn"] if self.api_key else c["danger"],
                                bg=c["bg_card"], font=("Segoe UI", 9, "bold"),
                                cursor="hand2", padx=14)
        self.key_btn.pack(side="right", padx=(0, 16))
        self.key_btn.bind("<Button-1>", lambda e: self._show_api_dialog())
        self.key_btn.bind("<Enter>", lambda e: self._on_hover(e, self.key_btn, True))
        self.key_btn.bind("<Leave>", lambda e: self._on_hover(e, self.key_btn, False))

        # ═══ 主体 ═══
        main = tk.Frame(self.root, bg=c["bg"])
        main.pack(fill="both", expand=True, side="top")

        # 左侧 Skill 面板
        self.skill_panel = tk.Frame(main, bg=c["bg_card"], width=220)
        self.skill_panel.pack(side="left", fill="y")
        self.skill_panel.pack_propagate(False)

        tk.Label(self.skill_panel, text="📋 Skills", fg=c["accent2"], bg=c["bg_card"],
                 font=("Segoe UI", 12, "bold")).pack(pady=(14, 8))

        scf = tk.Frame(self.skill_panel, bg=c["bg_card"])
        scf.pack(fill="both", expand=True, padx=2, pady=(0, 8))

        self.skill_canvas = tk.Canvas(scf, bg=c["bg_card"], highlightthickness=0, width=210)
        sbar = tk.Scrollbar(scf, orient="vertical", command=self.skill_canvas.yview)
        self.skill_inner = tk.Frame(self.skill_canvas, bg=c["bg_card"])
        self.skill_inner.bind("<Configure>",
            lambda e: self.skill_canvas.configure(scrollregion=self.skill_canvas.bbox("all")))
        self.skill_canvas.create_window((0, 0), window=self.skill_inner, anchor="nw")
        self.skill_canvas.configure(yscrollcommand=sbar.set)
        self.skill_canvas.pack(side="left", fill="both", expand=True)
        sbar.pack(side="right", fill="y")
        self.skill_canvas.bind("<MouseWheel>",
            lambda e: self.skill_canvas.yview_scroll(int(-e.delta/60), "units"))

        # 右侧聊天区
        self.chat_frame = tk.Frame(main, bg=c["bg"])
        self.chat_frame.pack(side="left", fill="both", expand=True)

        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, wrap="word", state="disabled",
            bg=c["bg"], fg=c["fg"], font=("Segoe UI", 11), insertbackground=c["fg"],
            bd=0, padx=16, pady=12, selectbackground=c["accent"])
        self.chat_display.pack(fill="both", expand=True)

        # 配置聊天气泡标签
        self.chat_display.tag_config("sender_user", foreground=c["accent2"],
                                     font=("Segoe UI", 11, "bold"), spacing1=8, spacing3=2)
        self.chat_display.tag_config("sender_ai", foreground=c["success"],
                                     font=("Segoe UI", 11, "bold"), spacing1=8, spacing3=2)
        self.chat_display.tag_config("bubble_user", background=c["bubble_u"],
                                     lmargin1=60, lmargin2=60, rmargin=16,
                                     spacing1=2, spacing3=2)
        self.chat_display.tag_config("bubble_ai", background=c["bubble_a"],
                                     lmargin1=16, lmargin2=16, rmargin=60,
                                     spacing1=2, spacing3=2)
        self.chat_display.tag_config("system_msg", foreground=c["fg_dim"],
                                     font=("Segoe UI", 9, "italic"), spacing1=4)

        # ═══ 输入区 ═══
        inf = tk.Frame(self.root, bg=c["bg_card"], height=72)
        inf.pack(fill="x", side="bottom")
        inf.pack_propagate(False)

        # 输入框 + placeholder
        self.input_frame = tk.Frame(inf, bg=c["bg_card"])
        self.input_frame.pack(fill="both", expand=True, padx=12, pady=10)

        self.input_box = tk.Text(self.input_frame, height=2, wrap="word",
                                 bg=c["bg_input"], fg=c["fg"],
                                 font=("Segoe UI", 11), insertbackground=c["accent2"],
                                 bd=0, padx=14, pady=10)
        self.input_box.pack(side="left", fill="both", expand=True)

        # Placeholder 标签（叠在输入框上）
        self._placeholder_text = "输入消息...  (Ctrl+Enter 发送)"
        self._placeholder_label = tk.Label(self.input_box, text=self._placeholder_text,
                                           fg=c["fg_dim"], bg=c["bg_input"],
                                           font=("Segoe UI", 11, "italic"))
        self._placeholder_label.place(x=16, y=10)
        self.input_box.bind("<FocusIn>", self._on_input_focus_in)
        self.input_box.bind("<FocusOut>", self._on_input_focus_out)
        self.input_box.bind("<KeyRelease>", self._on_input_keyrelease)

        # 发送按钮
        self.send_btn = tk.Label(inf, text=" 发送 → ", fg="white", bg=c["accent"],
                                 font=("Segoe UI", 11, "bold"), cursor="hand2", padx=22, pady=10)
        self.send_btn.pack(side="right", padx=(0, 12))
        self.send_btn.bind("<Button-1>", lambda e: self.send_message())
        self.send_btn.bind("<Enter>", lambda e: self._on_hover(e, self.send_btn, True))
        self.send_btn.bind("<Leave>", lambda e: self._on_hover(e, self.send_btn, False))

        # ═══ 状态栏 ═══
        sb = tk.Frame(self.root, bg=c["bg_card"], height=26)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        # 分隔线
        tk.Frame(self.root, bg=c["border"], height=1).pack(fill="x", side="bottom")

        total = sum(len(v) for v in self.skill_groups.values())
        self.status_lbl = tk.Label(sb, text=f"  🟢 就绪  |  Skills: {total}  |  Ctrl+Enter 发送",
                                   fg=c["fg_dim"], bg=c["bg_card"],
                                   font=("Segoe UI", 9), anchor="w")
        self.status_lbl.pack(fill="x", padx=12, pady=2)

        os.makedirs(MY_SKILLS_DIR, exist_ok=True)

    # ── 悬停效果 ──
    def _on_hover(self, event, widget, entering):
        c = self.c
        if widget == self.send_btn:
            widget.configure(bg=c["accent2"] if entering else c["accent"])
        elif widget == self.key_btn:
            widget.configure(fg=c["fg"] if entering else (c["warn"] if self.api_key else c["danger"]))
        elif widget in (self.btn_tools, self.btn_simple):
            if widget.cget("bg") != c["accent"]:  # 非激活状态才变色
                widget.configure(fg=c["fg"] if entering else c["fg_dim"])

    # ── 输入框 placeholder ──
    def _on_input_focus_in(self, e):
        self._placeholder_label.place_forget()

    def _on_input_focus_out(self, e):
        if not self.input_box.get("1.0", "end-1c").strip():
            self._placeholder_label.place(x=16, y=10)

    def _on_input_keyrelease(self, e):
        if self.input_box.get("1.0", "end-1c").strip():
            self._placeholder_label.place_forget()
        elif not self.input_box.focus_get():
            self._placeholder_label.place(x=16, y=10)

    # ═══════════════════════════════════════════
    # 引擎切换 —— 核心区别！
    # ═══════════════════════════════════════════
    def _switch_engine(self, engine):
        if self.engine == engine:
            return
        self.engine = engine
        self._apply_engine_ui()

    def _apply_engine_ui(self):
        """工具模式 vs 纯聊模式 —— 视觉完全不同"""
        c = self.c

        if self.engine == "tools":
            # 按钮样式
            self.btn_tools.configure(bg=c["accent"], fg="white", font=("Segoe UI", 10, "bold"))
            self.btn_simple.configure(bg=c["bg_card"], fg=c["fg_dim"], font=("Segoe UI", 10))

            # 显示 Skill 面板
            if not self._skills_visible:
                self.skill_panel.pack(side="left", fill="y", before=self.chat_frame)
                self._skills_visible = True

            # 输入框提示
            self._placeholder_text = "🛠️ 工具模式 — 我能操作文件/执行命令/搜索网页...  (Ctrl+Enter)"

            # 状态
            self._update_placeholder_show()

        else:  # 纯聊
            self.btn_simple.configure(bg=c["accent"], fg="white", font=("Segoe UI", 10, "bold"))
            self.btn_tools.configure(bg=c["bg_card"], fg=c["fg_dim"], font=("Segoe UI", 10))

            # 隐藏 Skill 面板 —— 纯聊模式不需要
            if self._skills_visible:
                self.skill_panel.pack_forget()
                self._skills_visible = False

            # 输入框提示
            self._placeholder_text = "💬 纯聊模式 — 直接对话，不用工具...  (Ctrl+Enter)"

            self._update_placeholder_show()

    def _update_placeholder_show(self):
        if self.input_box.winfo_exists() and not self.input_box.get("1.0", "end-1c").strip():
            self._placeholder_label.configure(text=self._placeholder_text)
            self._placeholder_label.place(x=16, y=10)

    # ═══════════════════════════════════════════
    # Skills UI
    # ═══════════════════════════════════════════
    def _load_skills_ui(self):
        for w in self.skill_inner.winfo_children():
            w.destroy()
        self._skill_vars.clear()
        c = self.c

        for cat_name, slist in self.skill_groups.items():
            is_my = cat_name.startswith("⭐")
            collapsed = cat_name in self._collapsed_cats and not is_my

            arrow = "▸" if collapsed else "▾"
            count = len(slist)
            header = tk.Label(self.skill_inner,
                            text=f"  {arrow}  {cat_name}  ({count})",
                            fg=c["warn"] if is_my else c["accent2"],
                            bg=c["bg_card"],
                            font=("Segoe UI", 10, "bold"), anchor="w",
                            cursor="hand2", padx=4, pady=3)
            header.pack(fill="x", pady=(8 if self.skill_inner.winfo_children() else 2, 1))
            header.bind("<Button-1>", lambda e, cn=cat_name: self._toggle_category(cn))
            header.bind("<Enter>", lambda e, w=header: w.configure(bg=c["bg_hover"]))
            header.bind("<Leave>", lambda e, w=header: w.configure(bg=c["bg_card"]))

            if collapsed:
                continue

            for s in slist:
                var = tk.BooleanVar(value=s["name"] in self.selected_skills)
                self._skill_vars[s["name"]] = var
                f = tk.Frame(self.skill_inner, bg=c["bg_card"])
                f.pack(fill="x", pady=1)
                cb = tk.Checkbutton(f, text=" " + s["label"], variable=var,
                                   bg=c["bg_card"], fg=c["fg"],
                                   selectcolor=c["bg_hover"],
                                   activebackground=c["bg_hover"],
                                   activeforeground=c["accent2"],
                                   font=("Segoe UI", 9),
                                   command=lambda n=s["name"], v=var: (
                                       self.selected_skills.add(n) if v.get()
                                       else self.selected_skills.discard(n)))
                cb.pack(side="left", padx=16)

    def _toggle_category(self, cat_name):
        if cat_name in self._collapsed_cats:
            self._collapsed_cats.discard(cat_name)
        else:
            self._collapsed_cats.add(cat_name)
        self._load_skills_ui()

    # ═══════════════════════════════════════════
    # 消息显示 —— 气泡风格
    # ═══════════════════════════════════════════
    def _add_message(self, sender, text, role="user"):
        self.chat_display.configure(state="normal")

        if role == "system":
            self.chat_display.insert("end", f"\n{text}\n", "system_msg")
        elif role == "user":
            # 用户消息 —— 右对齐气泡
            self.chat_display.insert("end", f"\n{'► 你':>60}\n", "sender_user")
            self.chat_display.insert("end", f"{text}\n", "bubble_user")
        else:
            # AI 消息 —— 左对齐气泡
            self.chat_display.insert("end", f"\n◄ {sender}\n", "sender_ai")
            self.chat_display.insert("end", f"{text}\n", "bubble_ai")

        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    # ═══════════════════════════════════════════
    # 发送消息
    # ═══════════════════════════════════════════
    def send_message(self):
        text = self.input_box.get("1.0", "end-1c").strip()
        if not text:
            return
        self.input_box.delete("1.0", "end")
        self._placeholder_label.place(x=16, y=10)

        # 显示用户消息
        self._add_message("", text, role="user")
        self.messages.append({"role": "user", "content": text})

        # 工具模式下附加勾选的 Skills
        sp = ""
        if self.selected_skills and self.engine == "tools":
            labels = []
            for n in self.selected_skills:
                for slist in self.skill_groups.values():
                    for s in slist:
                        if s["name"] == n:
                            labels.append(s["label"])
                            break
            sp = "可用技能: " + ", ".join(labels)
        if sp:
            self.messages[-1]["content"] += f"\n\n[{sp}]"

        # 思考动画
        self._think_start = _time.time()
        self._think_dots = 0
        self._thinking_active = True
        self._animate_thinking()

        # 异步调用
        def do_call():
            eng = self.engine
            if eng == "tools" and self.api_key:
                result = call_deepseek_with_tools(
                    self.messages[-6:], self.api_key,
                    progress_cb=lambda l, phase="": self.root.after(0, lambda: self._update_progress(l, phase)))
            elif self.api_key:
                import requests
                try:
                    self._update_progress("📡 调用 DeepSeek API...", "api")
                    req_kw = {"timeout": (10, 120)}
                    if _proxy:
                        req_kw["proxies"] = _proxy
                        if "127.0.0.1" in str(_proxy) or "localhost" in str(_proxy):
                            req_kw["verify"] = False
                    r = requests.post("https://api.deepseek.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}",
                                 "Content-Type": "application/json"},
                        json={"model": "deepseek-chat",
                              "messages": [{"role": "system",
                                            "content": "你是 Herrs，AI桌面助手。纯聊天模式，不用工具。简洁回答，中文。"}]
                                          + self.messages[-6:],
                              "max_tokens": 4096}, **req_kw)
                    if r.status_code == 200:
                        self._update_progress("🧠 模型思考中...", "model")
                        result = r.json()["choices"][0]["message"]["content"]
                    elif r.status_code in (401, 403):
                        result = f"🔑 API Key 无效 [{r.status_code}]"
                    elif r.status_code == 429:
                        result = f"⏳ API限流 [{r.status_code}]，请稍后重试"
                    else:
                        result = f"🌐 API 错误 [{r.status_code}]: {r.text[:200]}"
                except requests.exceptions.SSLError as e:
                    # 尝试关SSL验证重试一次
                    if req_kw.get("verify") is not False:
                        req_kw["verify"] = False
                        try:
                            r = requests.post("https://api.deepseek.com/v1/chat/completions",
                                headers={"Authorization": f"Bearer {self.api_key}",
                                         "Content-Type": "application/json"},
                                json={"model": "deepseek-chat",
                                      "messages": [{"role": "system",
                                                    "content": "你是 Herrs，AI桌面助手。纯聊天模式，不用工具。简洁回答，中文。"}]
                                                  + self.messages[-6:],
                                      "max_tokens": 4096}, **req_kw)
                            if r.status_code == 200:
                                result = r.json()["choices"][0]["message"]["content"]
                            else:
                                result = f"🌐 API 错误 [{r.status_code}]"
                        except Exception as e2:
                            result = f"🔒 SSL连接失败: {str(e2)[:100]}"
                    else:
                        result = f"🔒 SSL连接失败: {str(e)[:100]}"
                except requests.exceptions.ConnectionError as e:
                    result = f"🔌 网络连接失败: 检查网络或代理设置\n  ({str(e)[:120]})"
                except requests.exceptions.ProxyError:
                    result = f"🔌 代理连接失败: 检查代理 ({_proxy.get('http','?') if _proxy else '无'})"
                except Exception as e:
                    result = f"❌ {e}"
            else:
                result = "⚠️ 请先设置 API Key"
            self.root.after(0, lambda: self._on_response(result))

        threading.Thread(target=do_call, daemon=True).start()

    def _animate_thinking(self):
        if not getattr(self, "_thinking_active", False):
            return
        dots = [" ·", " ··", " ···", " ····", " ·····", " ······"]
        elapsed = int(_time.time() - self._think_start)
        eng_icon = "🛠️" if self.engine == "tools" else "💬"
        mode_name = "工具模式" if self.engine == "tools" else "纯聊模式"
        self.status_lbl.configure(
            text=f"  {eng_icon} {mode_name} 思考中{dots[self._think_dots % 6]}  ({elapsed}s)")
        self._think_dots += 1
        self._think_timer = self.root.after(250, self._animate_thinking)

    def _update_progress(self, line, phase=""):
        """更新状态栏 — 显示详细进度阶段"""
        if line:
            self.status_lbl.configure(
                text=f"  {line[:65]}",
                fg=self.c["accent2"] if phase == "perm" else self.c["fg_dim"])
            
            # 权限问题——闪烁提示并在聊天区显示
            if phase == "perm":
                self._add_message("⚡ 权限提示", line, "system")

    def _on_response(self, text):
        self._thinking_active = False
        if hasattr(self, "_think_timer"):
            self.root.after_cancel(self._think_timer)

        elapsed = int(_time.time() - self._think_start)
        # 工具模式显示调用了多少工具
        mode_label = "🛠️ 工具模式" if self.engine == "tools" else "💬 纯聊"
        self._add_message(f"Herrs · {mode_label} · {elapsed}s", text, role="ai")
        self.messages.append({"role": "assistant", "content": text})

        total = sum(len(v) for v in self.skill_groups.values())
        self.status_lbl.configure(
            text=f"  🟢 就绪  |  Skills: {total}  |  Ctrl+Enter 发送",
            fg=self.c["fg_dim"])

    # ═══════════════════════════════════════════
    # API Key 弹窗
    # ═══════════════════════════════════════════
    def _show_api_dialog(self):
        c = self.c
        d = tk.Toplevel(self.root)
        d.title("API & 代理设置"); d.geometry("540x360")
        d.configure(bg=c["bg_card"]); d.resizable(False, False)
        d.transient(self.root); d.grab_set()

        tk.Label(d, text="🔑 DeepSeek API Key", fg=c["accent2"], bg=c["bg_card"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(20, 6))
        tk.Label(d, text="platform.deepseek.com → API Keys", fg=c["fg_dim"],
                 bg=c["bg_card"], font=("Segoe UI", 9)).pack()

        e = tk.Entry(d, font=("Segoe UI", 11), bg=c["bg_input"], fg=c["fg"],
                     insertbackground=c["accent2"], bd=0, show="•", width=52)
        e.pack(pady=(12, 6), ipady=6)
        if self.api_key:
            e.insert(0, self.api_key)

        # ── 代理设置 ──
        tk.Label(d, text="🔌 代理地址（可选，如 http://127.0.0.1:7890）",
                 fg=c["accent2"], bg=c["bg_card"],
                 font=("Segoe UI", 12, "bold")).pack(pady=(16, 4))
        proxy_entry = tk.Entry(d, font=("Segoe UI", 11), bg=c["bg_input"], fg=c["fg"],
                     insertbackground=c["accent2"], bd=0, width=52)
        proxy_entry.pack(pady=(4, 2), ipady=6)
        # 读取当前代理配置
        lc = os.path.join(get_app_dir(), "herrs_config.json")
        current_proxy = ""
        try:
            if os.path.exists(lc):
                current_proxy = json.load(open(lc)).get("proxy", "")
        except: pass
        if current_proxy:
            proxy_entry.insert(0, current_proxy)
        tk.Label(d, text="留空则不使用代理", fg=c["fg_dim"],
                 bg=c["bg_card"], font=("Segoe UI", 8)).pack()

        st = tk.Label(d, text="", fg=c["success"], bg=c["bg_card"],
                      font=("Segoe UI", 9))
        st.pack(pady=(2, 0))

        def save():
            k = e.get().strip()
            if not k:
                st.configure(text="请输入 Key", fg=c["danger"]); return
            if not k.startswith("sk-"):
                st.configure(text="格式不对（应以 sk- 开头）", fg=c["danger"]); return
            self.api_key = k
            p = proxy_entry.get().strip()
            lc = os.path.join(get_app_dir(), "herrs_config.json")
            cfg = {"api_key": k}
            if p:
                cfg["proxy"] = p
            try:
                json.dump(cfg, open(lc, "w"))
            except:
                pass
            # 更新全局代理
            global _proxy
            _proxy = {"http": p, "https": p} if p else None
            self.key_btn.configure(text="🔑 已配置" if not p else f"🔑 已配置 · 代理",
                                   fg=c["warn"])
            st.configure(text="✅ 保存成功！", fg=c["success"])
            total = sum(len(v) for v in self.skill_groups.values())
            self.status_lbl.configure(
                text=f"  🟢 就绪  |  Skills: {total}  |  Ctrl+Enter 发送",
                fg=c["fg_dim"])
            d.after(800, d.destroy)

        btn_save = tk.Label(d, text="  保  存  ", fg="white", bg=c["accent"],
                            font=("Segoe UI", 12, "bold"), cursor="hand2", padx=36, pady=6)
        btn_save.pack(pady=(12, 0))
        btn_save.bind("<Button-1>", lambda e: save())
        btn_save.bind("<Enter>", lambda e: btn_save.configure(bg=c["accent2"]))
        btn_save.bind("<Leave>", lambda e: btn_save.configure(bg=c["accent"]))

    # ═══════════════════════════════════════════
    # 系统托盘 & 快捷键
    # ═══════════════════════════════════════════
    def _on_close(self):
        self.root.withdraw()

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _quit_app(self):
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([4, 4, 60, 60], fill="#1a1a2e", outline="#6c5ce7", width=3)
            draw.text((20, 14), "H", fill="#a29bfe")
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口",
                    lambda: self.root.after(0, self._restore_window), default=True),
                pystray.MenuItem("退出",
                    lambda: self.root.after(0, self._quit_app)))
            self.tray_icon = pystray.Icon("herrs", img, APP_NAME, menu)
            threading.Thread(target=lambda: self.tray_icon.run(), daemon=True).start()
        except Exception as e:
            debug(f"托盘失败: {e}")

    def _setup_hotkey(self):
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+shift+h", self._restore_window)
        except Exception as e:
            debug(f"快捷键失败: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except:
        pass
    app = HerrsApp(root)
    app._setup_tray()
    app._setup_hotkey()
    root.mainloop()
