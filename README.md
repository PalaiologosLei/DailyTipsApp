# DailyTipsApp

一个最小可用的本地 Python 工具，用来：

1. 递归扫描 Markdown 笔记
2. 提取符合规则的公式/知识点
3. 生成适配 iPhone 锁屏的图片
4. 输出到当前项目目录
5. 同步复制到你选择的云盘目录，例如 iCloud Drive 或 OneDrive

## 项目结构

```text
assets/
  backgrounds/
    default/
      .gitkeep
src/
  app.py
  background_library.py
  cloud_sync.py
  device_profiles.py
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

## 当前工作流

- 扫描本地或 GitHub 公开笔记仓库中的 Markdown
- 提取公式/知识点
- 生成锁屏图片到 `output/images`
- 再把 PNG 镜像复制到你指定的云盘目录

项目不再自动把生成图片提交到 GitHub。GitHub 只用于代码版本管理。

## GUI 功能

```bash
python -m src.main --gui
```

GUI 支持：

- 中文 / English 切换
- 选择本地 Markdown 目录或 GitHub 公开仓库地址
- 选择 iPhone 型号
- 自定义尺寸（`Custom`）
- 设置项目输出目录和云盘目录
- 如果云盘目录不存在，运行前提示创建
- 自动记住上次使用的语言、路径、云盘目录、设备型号、背景模式等

## 图片渲染

- 顶部约 `1/3` 高度留白，避免挡住 iPhone 锁屏时间和小组件
- 支持正文和说明中的行内公式 `$...$`
- 公式中的中文按普通文字渲染，避免乱码
- 公式字母尺寸做了回调，尽量贴近普通正文大小
- 背景可选纯白或背景图库中的图片
- 有背景图时，程序会自动裁剪到目标锁屏尺寸，并在内容区下方加半透明白底保证可读性

## 背景图库

背景图库位于 `assets/backgrounds/`，按“分组目录”组织。

GUI 里支持：

- 查看分组
- 新增 / 删除分组
- 导入图片到某个分组
- 删除图片
- 选择以下背景模式：
  - 纯白背景
  - 指定图片
  - 指定分组随机
  - 全部图片随机

说明：

- 用户导入的背景图必须是图片文件
- 支持常见格式：`png/jpg/jpeg/webp/bmp`
- 不限制原图尺寸，生成时会自动裁剪适配
- 背景图库中的用户图片默认被 `.gitignore` 忽略，不会提交到 GitHub
- “随机”模式采用稳定选择策略，同一条目在背景池不变时不会每次都变图，避免无意义重生成

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

## 安装依赖

```bash
pip install -r requirements.txt
```

## 命令行运行

```bash
python -m src.main --notes-dir "D:\path\to\DailyTips" --cloud-dir "C:\Users\lky14\iCloudDrive\DailyTips"
```

或：

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

程序会：

- 为每个条目计算内容哈希
- 未变化的图片不重新生成
- 已删除的条目对应图片会自动删除
- 在 `output/images/.manifest.json` 中记录当前生成状态
- 每次将当前全部 PNG 镜像到云盘目录，并删除云盘目录里已过期的旧 PNG

## 测试

```bash
python -m unittest discover -s tests
```
