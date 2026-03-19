# DailyTipsApp

一个最小可用的本地 Python 工具，用来：

1. 递归扫描 Markdown 笔记
2. 提取符合规则的公式/知识点
3. 生成白底黑字的竖屏图片
4. 输出到当前仓库
5. 可选执行 `git add` / `git commit` / `git push`

## 项目结构

```text
src/
  app.py
  git_sync.py
  gui.py
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
- 【全概率公式】
  - $P(A)=\sum P(A|X_i)P(X_i)$
  - 期望版本 $E(X)=E(E(X|Y))$
```

规则：

- 标题行必须包含中文中括号 `【】`
- 标题下一层缩进中的第一条内容视为正文
- 同层后续内容视为说明列表
- 如果没有找到下一层缩进内容，则跳过

## 公式渲染

- 现在支持正文和说明中的行内公式 `$...$`
- 使用 `matplotlib` 的 mathtext 进行渲染
- 如果本地没有安装 `matplotlib`，程序会回退成普通文本显示

## 安装依赖

```bash
pip install -r requirements.txt
```

## 命令行运行

解析本地目录：

```bash
python -m src.main --notes-dir "D:\path\to\DailyTips"
```

解析 GitHub 公开仓库：

```bash
python -m src.main --github-url "https://github.com/PalaiologosLei/DailyTips"
```

常用参数：

- `--output-dir`：图片输出目录，默认 `output/images`
- `--width`：图片宽度，默认 `1179`
- `--height`：图片高度，默认 `2556`
- `--skip-git`：只生成图片，不执行 git 提交和推送
- `--commit-message`：自定义提交信息
- `--gui`：启动图形界面

## GUI 运行

```bash
python -m src.main --gui
```

GUI 支持：

- 中文 / English 切换
- 选择本地 Markdown 目录
- 输入 GitHub 公开仓库地址
- 设置输出目录和图片尺寸
- 勾选是否跳过 git 提交

## 文件管理策略

为了减少重复生成和无意义提交，程序现在会：

- 为每个条目计算内容哈希
- 未变化的图片不重新生成
- 已删除的条目对应图片会自动删除
- 在 `output/images/.manifest.json` 中记录当前生成状态

这能显著减缓仓库体积增长，但无法自动缩小已经存在的 Git 历史。如果历史里的图片版本已经很多，真正缩小仓库体积通常需要额外做历史重写，或者改用 Git LFS / 外部对象存储。

## 测试

```bash
python -m unittest discover -s tests
```
