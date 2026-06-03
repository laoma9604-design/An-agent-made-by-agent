# Herrs Desktop

> Hermes 的穷鬼表弟。DeepSeek 驱动，能动手不动嘴的桌面 AI。

## 这玩意是啥

**Hermes** 很牛逼——80 个工具、有记忆、跨平台、能自我进化。但它装起来烦。

**Herrs** 就是我把 Hermes 的皮扒了，留了最核心的东西：**AI 应该干活，不是光逼逼**。然后拿 Python 糊了个窗口。

| | Hermes | Herrs（就这） |
|------|------|------|
| 工具 | 80+ | 18 |
| 安装 | 一堆脚本 | pip install 三行 |
| 启动 | 开终端打 hermes | 双击 exe |
| 关系 | 航母 | 橡皮艇 |

橡皮艇也能过河。

## 能干啥

| | 能干的事 |
|------|------|
| 📁 文件 | 读、写、搜——比你翻文件夹快 |
| ⚡ 系统 | 跑命令、跑 Python、杀进程、查磁盘 |
| 🌐 网络 | 搜索、抓网页、下文件 |
| 🖥️ 桌面 | 打开东西、剪贴板、截图、弹通知 |

## 两种模式

| | 🛠️ 工具 | 💬 纯聊 |
|------|------|------|
| 干嘛的 | 真动手干活 | 纯聊天 |
| 比如 | "帮我把C盘垃圾清了" | "给我讲讲什么叫反向传播" |
| Skill 面板 | 显示 | 隐藏 |

点顶部按钮切。

## 跟一般 AI 有啥区别

你问 ChatGPT "C盘满了咋办" → 它写 500 字教程。

你问 Herrs → 它自己扫一遍，直接开删。

**不是它聪明，是它真敢动手。**

## 怎么用

```bash
pip install -r requirements.txt
python main.py
```

然后去 [platform.deepseek.com](https://platform.deepseek.com) 搞个 Key，粘进去，完事。

## 打包

```bash
pyinstaller --onefile --noconsole --name "Herrs" main.py
```

exe 在 `dist/Herrs.exe`。

## 其他

- 80+ Skill 在左边（虽然只能当提示词）
- 关窗口缩托盘，`Ctrl+Shift+H` 叫回来
- Key 存本地，不上传
- `my_skills/` 里放自己的 Skill

---

*Hermes 的山寨模仿品。致敬原版，但跟官方没半毛钱关系。*
