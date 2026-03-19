# DailyTipsApp

一个最小可用的本地 Python 脚本项目，用来：

1. 递归扫描笔记库中的 Markdown 文件
2. 提取满足指定缩进规则的公式/知识点
3. 为每个条目生成白底黑字的竖屏图片
4. 将生成结果输出到当前仓库
5. 自动执行 `git add` / `git commit` / `git push`

## 项目结构

```text
src/
  __init__.py
  git_sync.py
  main.py
  models.py
  parser.py
  renderer.py
  scanner.py
output/
  images/
tests/
requirements.txt
```

## Markdown 识别格式

程序识别以下结构：

```markdown
- 【牛顿-莱布尼茨公式】
  - F(b) - F(a) = ∫[a,b] f(x) dx
  - 用原函数差值表示定积分
  - 常用于积分计算
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

如果你使用 conda，也可以在已激活环境中执行同样命令。

## 运行方式

```bash
python -m src.main --notes-dir "D:\path\to\DailyTips"
```

常用参数：

- `--notes-dir`：笔记库根目录，必填
- `--output-dir`：图片输出目录，默认 `output/images`
- `--width`：图片宽度，默认 `1179`
- `--height`：图片高度，默认 `2556`
- `--skip-git`：只生成图片，不执行 git 提交推送
- `--commit-message`：自定义提交信息

## 输出结果

- 生成的图片默认保存在 [output/images](D:/Coding/DailyTipsApp/output/images)
- 每张图片包含标题、正文和说明列表
- 图片为白底黑字、适合手机竖屏阅读

## 测试

```bash
python -m unittest discover -s tests
```
