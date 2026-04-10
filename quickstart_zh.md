# 中文快速说明（医生友好版）

这是一份给临床老师、医学生和医学科研使用者的快速说明。  
如果你只是想先把工具跑起来，再看结果，这一页就够用了。

## 这是什么

paper-radar 可以把它理解成一个“文献雷达”：

1. 输入一个主题  
2. 检索最近一段时间的文献  
3. 自动做一轮初步排序  
4. 生成一个比较好看的网页报告

你真正最需要看的文件通常是：

```text
outputs/你的主题/report.html
```

双击这个文件，一般就可以在浏览器里打开。

<p align="center">
  <img src="./report-preview.png" alt="report preview" width="88%">
</p>

## 它适合做什么

适合：
- 跟踪某个课题最近 1 个月的新文献
- 每周例行看某个方向有没有新文章
- 给课题组做文献扫描
- 做一轮自动初筛，决定先看哪几篇

不适合：
- 代替严格意义上的系统综述检索
- 直接替代人工学术判断
- 当作最终纳入标准

## 安装

在项目目录下运行：

```bash
python -m pip install -e .
```

如果你的电脑里 Python 环境比较乱，不建议直接用 `pip`，优先用：

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

意思就是：

- 检索 `multimodal imaging`
- 看最近 30 天
- 按默认权重排序
- 输出到 `outputs` 文件夹

## 更贴近真实检索习惯的写法

这个工具支持一种更接近实际检索式的写法：

- **括号内用 OR**
- **括号之间用 AND**
- **短语可以加双引号**

例如：

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

你可以把它理解成：

- 第一组：胆囊癌相关说法
- 第二组：多模态相关说法
- 第三组：病理相关说法

程序会更接近“组内同义词、组间同时满足”的方式去检索。

## 运行后会生成什么

通常会生成：

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

### 其他文件是什么

- `report.md`：文字版摘要
- `papers.csv`：表格版结果，适合 Excel 打开
- `run_metadata.json`：记录这次检索的元信息

## 如果结果看起来“不对劲”

这很常见，通常不是程序坏了，而是下面两个原因。

### 1）关键词太宽

比如只搜：

```text
gallbladder
```

这种太宽，会混进很多“沾边但并不是你真正想看”的文章。

通常更好的写法是：
- `gallbladder cancer`
- `gallbladder neoplasms`
- `malignant biliary stricture`
- `deep learning`
- `radiomics`
- `pathology`

### 2）当前权重不适合你的目的

排序规则在这里：

```text
configs/default_weights.yml
```

如果你更在意“主题贴合度”，就把 `relevance` 权重调高。  
如果你更在意“最近刚发”，就把 `freshness` 权重调高。

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

如果你希望结果自动发到邮箱，需要先配置 SMTP。

以 QQ 邮箱为例，一般需要先在邮箱后台开启 SMTP / IMAP 服务，并获取授权码。  
然后在终端里设置环境变量。

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

### 注意

这里的 `SMTP_PASSWORD` 一般不是邮箱登录密码，而是邮箱后台生成的 **SMTP 授权码**。

## 第一次用，建议按这个顺序

1. 先跑一个简单关键词  
2. 打开 `report.html` 看效果  
3. 如果结果太泛，把关键词改得更具体  
4. 如果排序不符合直觉，再改 `configs/default_weights.yml`  
5. 最后再考虑周更和发邮件

## 一句话总结

这个工具更适合做：

**“某个方向最近文献的自动监测和初筛”**

而不是做：

**“严格系统综述级别的正式检索”**

## 常见问题

### 为什么有些看起来不太对的文章排得很前？
通常是因为关键词太宽，或者当前权重更奖励“新、完整、综述类文献”。

### 为什么我没有收到邮件？
通常是 SMTP 没配好，或者没有使用授权码，或者程序只生成了本地文件但没有真正进入邮件发送环节。

### 我最应该先看哪个文件？
先看 `report.html`。

### 这个工具可以公开分享吗？
可以。更适合把它定位成一个“研究监测工具”，不是系统综述平台。

---

如果你是项目维护者，仓库首页建议看英文版 `README.md`；中文使用者看这一份就够了。
