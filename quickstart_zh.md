# 中文快速说明-医生友好

一份给临床医学生和医学科研使用者的快速说明。  

## 这是什么

paper-radar 可以把它理解成一个“文献雷达”：

1. 输入一个主题  
2. 检索最近一段时间的文献  
3. 自动做一轮初步排序  
4. 生成一个比较好看的网页报告

## 它适合做什么

适合：
- 跟踪某个课题最近1个月的新文献
- 例行看某个方向有没有新文章

不适合：
- 代替严格意义上的系统综述检索

## 安装

在项目目录下运行：

```bash
python -m pip install -e .
```

## 最短运行示例

### 普通关键词

```bash
python -m paper_radar.cli report "multimodal imaging" \
  --days 30 \
  --weights configs/default_weights.yml \
  --outdir outputs \
  --max-results-pubmed 60 \
  --max-results-arxiv 20 \
  --ncbi-email "你的邮箱"
```

即：
- 检索 `multimodal imaging`
- 看最近 30 天
- 按默认权重排序
- 输出到 `outputs` 文件夹

这个工具支持一种更接近实际检索式的写法：

```text
("gallbladder cancer" OR "gallbladder neoplasms") AND (multimodal OR "multi-modal") AND (pathology OR histopathology)
```

运行示例：

```bash
python -m paper_radar.cli report '("gallbladder cancer" OR "gallbladder neoplasms") AND (multimodal OR "multi-modal") AND (pathology OR histopathology)' \
  --days 30 \
  --weights configs/default_weights.yml \
  --outdir outputs \
  --max-results-pubmed 60 \
  --max-results-arxiv 20 \
  --ncbi-email "你的邮箱"
```

## 运行后通常会生成

```text
outputs/主题名/
├─ report.html
├─ report.md
├─ papers.csv
└─ run_metadata.json
```

### 先看哪个文件

先看：

```text
report.html
```

这个页面通常会包含：

- 检索主题
- 解析后的分组
- 高亮推荐文献
- 详细排序结果
- 趋势图

### 其他文件

- `report.md`：文字版摘要
- `papers.csv`：表格版结果，适合 Excel 打开
- `run_metadata.json`：记录这次检索的元信息


## 想每周自动更新，可以吗

可以。

你可以把多个主题写进：

```text
configs/topics.example.yml
```

然后执行：

```bash
python -m paper_radar.cli update \
  --topics configs/topics.example.yml \
  --weights configs/default_weights.yml \
  --outdir weekly_reports \
  --ncbi-email "你的邮箱"
```

这条命令会依次跑多个主题，适合做每周更新。

之后你可以：
- 本地手动运行
- 用 Windows 任务计划或 macOS 定时任务
- 放到 GitHub Actions 里每周自动跑

## 邮件发送（可选）

如果你希望结果自动发到邮箱，需要先配置SMTP。以QQ邮箱为例，一般需要先在邮箱后台开启SMTP/IMAP服务，并获取授权码。然后在终端里设置环境变量。

### PowerShell 示例

```powershell
$env:SMTP_HOST="smtp.qq.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="你的QQ邮箱"
$env:SMTP_PASSWORD="你的SMTP授权码"
$env:MAIL_FROM="你的QQ邮箱"
```

然后运行：

```bash
python -m paper_radar.cli report "multimodal imaging" \
  --days 30 \
  --weights configs/default_weights.yml \
  --outdir outputs \
  --ncbi-email "你的邮箱" \
  --email-to "收件邮箱"
```


## 常见问题

### 为什么有些看起来不太对的文章排得很前？
通常是因为关键词太宽，或者当前权重更奖励“新、完整、综述类文献”。

### 为什么我没有收到邮件？
通常是 SMTP 没配好，或者没有使用授权码，或者程序只生成了本地文件但没有真正进入邮件发送环节。

### 我最应该先看哪个文件？
先看 `report.html`。

### 这个工具可以公开分享吗？
可以。更适合把它定位成一个“研究监测工具”，不是系统综述平台。
