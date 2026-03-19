# DailyTipsApp

一个最小可用的本地 Python 工具，用来：

1. 递归扫描 Markdown 笔记
2. 提取符合规则的公式/知识点
3. 生成白底黑字的竖屏图片
4. 输出到当前仓库
5. 将图片同步复制到你选择的云盘目录，例如 iCloud Drive 或 OneDrive

## 项目结构

```text
src/
  app.py
  cloud_sync.py
  gui.py
  gui_settings.py
  main.py
  models.py
  note_source.py
  parser.py
  renderer.py
  scanner.py
output/
  images/
tests/
requirements.txt
```

## 支持的输入来源

- 本地笔记目录
- GitHub 公开仓库 URL

支持的 GitHub URL 形式：

- `https://github.com/owner/repo`
- `https://github.com/owner/repo/tree/main/subfolder`

如果仓库根 URL 没写分支，程序会依次尝试 `main` 和 `master`。

## Markdown 识别格式

程序识别如下结构：

```markdown
- 【事件的独立性】
  - $E(XY)=E(X)E(Y)$
  - 当且仅当 $X,Y$ 独立
```

规则：

- 标题行必须包含中文中括号 `【】`
- 标题下一层缩进中的第一条内容视为正文
- 同层后续内容视为说明列表
- 如果没有找到下一层缩进内容，则跳过

## 公式渲染

- 支持正文和说明中的行内公式 `$...$`
- 公式中的中文会按普通文字渲染，避免乱码
- 公式片段会按更接近正文的尺寸进行缩放，避免明显偏小
- 如果本地没有安装 `matplotlib`，程序会回退成普通文本显示

## GUI

```bash
python -m src.main --gui
```

GUI 支持：

- 中文 / English 切换
- 选择本地 Markdown 目录
- 输入 GitHub 公开仓库地址
- 设置项目输出目录和云盘目录
- 自动将上次使用的语言、路径、地址、尺寸等保存到 `.gui_settings.json`

`云盘目录` 可以是：

- `C:\Users\lky14\iCloudDrive\DailyTips`
- OneDrive 同步目录
- Dropbox 同步目录
- 其他本地同步盘目录

应用本身只负责把图片复制到这个目录，不关心背后是哪个云服务。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 命令行运行

解析本地目录并同步到 iCloud 目录：

```bash
python -m src.main --notes-dir "D:\path\to\DailyTips" --cloud-dir "C:\Users\lky14\iCloudDrive\DailyTips"
```

解析 GitHub 公开仓库并同步到云盘目录：

```bash
python -m src.main --github-url "https://github.com/PalaiologosLei/DailyTips" --cloud-dir "C:\Users\lky14\iCloudDrive\DailyTips"
```

常用参数：

- `--output-dir`：项目内图片输出目录，默认 `output/images`
- `--cloud-dir`：云盘同步目录，例如 iCloud Drive 目录
- `--width`：图片宽度，默认 `1179`
- `--height`：图片高度，默认 `2556`
- `--gui`：启动图形界面

## 文件管理策略

为了减少重复生成和无意义复制，程序现在会：

- 为每个条目计算内容哈希
- 未变化的图片不重新生成
- 已删除的条目对应图片会自动删除
- 在 `output/images/.manifest.json` 中记录当前生成状态
- 每次将当前全部图片镜像到云盘目录，并删除云盘目录里已过期的旧图片

当前项目不再自动执行 `git add` / `git commit` / `git push`，图片也不再以 GitHub 仓库作为分发存储。

## 测试

```bash
python -m unittest discover -s tests
```
