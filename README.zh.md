<p align="center">
  <img src="docs/icon.png" width="88" alt="Notro">
</p>

<h1 align="center">Notro</h1>

<p align="center">
  <b>不用 Nitro 也能发自定义表情和大文件 —— 完全不碰 Discord 客户端。</b>
</p>

<p align="center">
  <a href="../../releases/latest"><img src="https://img.shields.io/github/v/release/writingdeveloper/Notro?label=download&color=5865F2" alt="最新版本"></a>
  <a href="../../releases"><img src="https://img.shields.io/github/downloads/writingdeveloper/Notro/total?color=57F287" alt="下载次数"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4" alt="Windows 10 / 11">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
</p>

<p align="center"><a href="README.md">English</a> | <a href="README.ko.md">한국어</a> | <a href="README.ja.md">日本語</a> | <b>中文</b> | <a href="README.es.md">Español</a></p>

---

Discord 要收费的两件事，在应用之外解决：

- **图片有 14MB，免费上限是 10MB。** 你复制的那一刻 Notro 就把它压好放回剪贴板，
  你只要按 <kbd>Ctrl</kbd>+<kbd>V</kbd>。
- **想在任何地方用自定义表情。** 按 <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd>
  挑一个，它就进到输入框里。

**不打补丁、不注入、不登录。** Notro 只是一个托盘程序，负责准备剪贴板并替你按下
<kbd>Ctrl</kbd>+<kbd>V</kbd> —— 和 Windows 表情面板（<kbd>Win</kbd>+<kbd>.</kbd>）
属于同一类输入自动化。它不修改 Discord 客户端，也从不接触你的账号或令牌。诚实的代价是：
接收方看到的是图片附件，而不是原生的内嵌表情。

<p align="center">
  <img src="docs/picker.png" width="620" alt="装满自定义表情的 Notro 选择器 —— 表情/贴纸/GIF 标签页，左侧收藏集，顶部收藏与最近使用">
</p>

<p align="center">
  <a href="../../releases/latest"><b>⬇ 下载 NotroSetup.exe</b></a><br>
  <sub>无需管理员权限。安装到用户目录，可从 设置 → 应用 卸载。</sub>
</p>

---

## 选择器

在任何地方按 <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd>，光标旁会弹出一个深色窗口，
分为 **表情 / 贴纸 / GIF** 三个标签页。

**发出来就是真表情该有的大小。** Discord 会按附件图片的原始像素尺寸绘制，所以当收藏里
同时有 20×20 的 GIF 和 1080×1080 的 PNG 时，一个小得像芝麻，另一个大得像照片。Notro 在
粘贴前把长边统一 —— 表情 **48px**（等同放大版自定义表情），贴纸 **160px**，GIF 保持原样。
**收藏里的文件不会被改动**，只调整放到剪贴板上的那份副本。

**加入表情** —— 粘贴 *"复制链接"* 的 URL，或直接粘贴从消息里复制表情得到的 `<:名称:id>`
文本，或把图片文件拖进来，或指定一个**监视文件夹**，甚至只要在 `%APPDATA%\Notro\assets`
下建个文件夹放进去，它就会成为一个收藏集，不需要任何注册步骤。

**再找出来** —— 按名称或关键词搜索，还支持**韩语首字母检索**（输入 `ㅁㅋ` 能找到 `미쿠`）。
收藏和最近使用的项目会留在最上面。

**不用鼠标** —— 方向键移动，<kbd>Enter</kbd> 粘贴，<kbd>Esc</kbd> 关闭。按下热键之后，
手不必离开键盘。

<details>
<summary>选择器的更多行为</summary>

- 右键点击项目 → 修改名称和关键词、移动到其他收藏集、以链接方式粘贴（通过 URL 添加的项目）、删除。
- 当同一标签页和收藏集里已有相同图片时，会提示而不是悄悄重复添加。
- 会动的 APNG 贴纸在注册时转换为 GIF —— 因为 Discord 不播放上传的 APNG。
- 剪贴板按钮可把当前图片直接存入 **捕获** 收藏集。设置中也可以自动保存每张新的剪贴板图片，
  默认关闭。
- 窗口可以调整大小并记住尺寸（会考虑显示器缩放比例）。
- 超出上限的项目：静态图片自动压缩，过大的 GIF 会带警告按原样发送。
- 还有一个粘贴后替你按 <kbd>Enter</kbd> 的自动发送选项 —— 默认关闭。

</details>

## 自动压缩

Notro 会监视剪贴板。出现新图片时，它计算 **Discord 实际会生成的 PNG 体积**，如果在上限之内
就什么都不做。超出时按 WebP → JPEG 依次重新编码，先降质量，仍不够再降分辨率，压到约 9.5MB
以下，并把结果**以文件形式**放回剪贴板，这样 <kbd>Ctrl</kbd>+<kbd>V</kbd> 就会作为附件上传。

> 硬盘上的原始文件绝不会被改动 —— 被替换的只有剪贴板。

上限可以在托盘菜单里切换为 **10 / 50 / 500MB**（免费 / Nitro Basic / Nitro）。

## 视频片段

复制一段过大的游戏录像时，Notro 会先询问，并告诉你结果会是什么样：

```
52MB · 1:12 · 1080p60  →  约 9.5MB · 480p30
```

你可以在同一个窗口里**裁剪片段**（`开始 – 结束`）和**移除音频**，预估会随输入实时更新。
这比任何编码参数都管用：一段 30 秒的 1080p60 录像整段处理只能退到 **1080p30**，但只保留
你真正想要的 7 秒，就能维持 **1080p60**。

**从不打包 ffmpeg。** 第一次压缩视频时才按需下载（约 30MB，带 SHA-256 校验），如果你的
`PATH` 里已经有就直接用。如果一段片段连 360p 都塞不进上限，Notro 会如实告诉你，而不是
做出一片马赛克。

## 安装

下载 **[`NotroSetup.exe`](../../releases/latest)** 并运行。无需管理员权限，安装到
`%LOCALAPPDATA%\Programs\Notro`。

> ⚠️ 目前**尚未进行代码签名**，所以 SmartScreen 会提示发布者未知 —— 点击
> *更多信息 → 仍要运行*。每个版本都附带 `NotroSetup.exe.sha256`，你可以据此准确校验下载到
> 的文件，也可以[自行从源码构建](#从源码运行构建与配置)。详见
> [SECURITY.md](SECURITY.md#code-signing) 和[代码签名策略](CODE_SIGNING.md)。

**Windows 10 用户：** 选择器需要 Microsoft Edge WebView2 运行时（Windows 11 自带）。
缺少时安装程序会自动获取。即使没有，也只是选择器不可用，压缩功能照常工作。

### 它去哪了？

Notro **没有主窗口** —— 它运行在时钟旁边的托盘里。**Windows 11 默认隐藏新的托盘图标**，
如果看不到，请点击 **`^`** 箭头，再把 Notro 图标拖到任务栏上。

<p align="center">
  <img src="docs/welcome.png" width="360" alt="Notro 首次启动的说明窗口">
</p>

其余设置都在托盘图标的右键菜单里：选择器热键、暂停、最近处理记录、上传上限、语言、
输出文件夹，以及开机自动运行（**默认关闭**）。

## 隐私

Notro 会监视剪贴板，所以有必要说明它如何处理这些内容。

- **你复制的任何内容都不会被发送出去。** 没有遥测、没有分析、没有崩溃报告、没有账号。
- **不主动保存。** 捕获自动保存默认关闭。
- 它只连接**四个**端点，全部有文档说明：GitHub（检查更新与安装包，带 SHA-256 校验）、
  `cdn.discordapp.com`（仅当你用链接添加表情时）、PyPI（仅在你第一次压缩视频、需要获取
  ffmpeg 时，同样带 SHA-256 校验）。
- 卸载时**会特意保留你的收藏库**（`%APPDATA%\Notro`），这样重装后不会丢失表情。

包括每个文件的具体位置在内的完整说明见 [SECURITY.md](SECURITY.md)。

## 语言

English、한국어、日本語、中文(简体)、Español —— 自动识别 Windows 语言，也可以随时从托盘切换。

<details>
<summary><a id="从源码运行构建与配置"></a>从源码运行、构建与配置</summary>

```sh
pip install -r requirements.txt
pythonw notro.py           # 运行
build.bat                  # 构建 dist\Notro.exe
```

需要 Windows 和 Python 3.10 以上。

压缩行为位于 `notro_app/config.py` 和 `notro_app/compress.py`：

| 设置 | 默认值 | 说明 |
|---|---|---|
| `LIMIT_MB` | 10 | 上传上限 —— 也可在托盘菜单中选择 10/50/500 |
| `SAFETY` | 0.95 | 安全余量（目标约 9.5MB） |
| `WEBP_QUALITIES` | 90–50 | WebP 质量档位 |
| `MIN_SCALE` | 0.4 | 分辨率缩小下限 |

测试：

```sh
pip install -r requirements-dev.txt
pytest
```

</details>

## 许可证

[MIT](LICENSE)。随程序分发的第三方组件及各自的许可证 —— 包括 LGPL-3.0 的 pystray ——
都整理在 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) 中。

> Notro 是非官方工具，**与 Discord Inc. 无隶属、赞助或认可关系。**
> "Discord" 是 Discord Inc. 的商标。
