# 云端讲座邮件提醒

不依赖任何一台电脑开机：GitHub 的服务器按点跑，用 163 的 SMTP 把提醒发到你邮箱。

## 它怎么工作（2026-10-23 定稿）

触发有两条路，**主力是外部的 cron-job.org**：

```
cron-job.org（每 15 分钟，准点）
   └─ POST GitHub 的 workflow_dispatch 接口
        └─ workflow 跑 reminder/send.py
             ├─ 判断：某场讲座的提醒时刻到了没？还在补发窗口内吗？
             ├─ 到了就发邮件（163 SMTP）
             └─ 在 reminder/sent/<id>.txt 留标记并自动提交回仓库 ⇒ 同一场只发一次
```

- **为什么不用 GitHub 自己的定时**：实测它被限流得极狠——写着每 30 分钟，实际一天只跑 2~3 次，
  11 次运行没有一次落在提醒窗口内，一封都没发出去。所以只留作**备胎**（全天每 30 分钟），
  主力交给外部触发。
- 多次触发不会重复发信：标记文件 + 2.5 小时窗口共同保证「一场只发一次」。
- 时间表里的时间按**北京时间**理解，脚本内部换算成 UTC。
- 已验证：cron-job.org 测试返回 **204**，GitHub 上出现 `workflow_dispatch` 运行并成功发出邮件
  （`reminder/sent/3.txt` 就是那一次留下的）。

## 部署（五步）

### 1. 建仓库

GitHub 上新建一个仓库，名字随意（比如 `lecture-reminder`）。

- **Private** 也行：免费额度 2000 分钟/月，这套四天大约跑 200 次、每次 1 分钟，够用。
- **Public** 则完全不限时。注意 public 仓库里 `lectures.json` 和 workflow 文件是公开可见的，
  但**授权码放在 Secret 里，不会泄露**。

### 2. 把文件推上去

仓库根目录应该正好是这四个文件：

```
.github/workflows/lecture-reminder.yml
reminder/send.py
reminder/lectures.json
reminder/sent/.gitkeep
```

本机这份就在 `D:\dsh生活\cloud-reminder`，用命令行最省事：

```powershell
cd D:\dsh生活\cloud-reminder
git init
git add .
git commit -m "讲座邮件提醒"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

不想用命令行就在网页上「Add file → Upload files」拖进去，再手动建 `.github/workflows/` 目录。
**注意**：workflow 文件必须落在默认分支的 `.github/workflows/` 下才会生效。

### 3. 加一个 Secret

仓库 → **Settings → Secrets and variables → Actions → New repository secret**

- Name：`MAIL_AUTH_CODE`
- Secret：163 的 SMTP 授权码（本机在 `D:\dsh生活\lecture_reminder\mail_config.json` 的 `auth_code` 字段）

只需要这一个。收发地址、SMTP 主机端口都直接写在 workflow 的 `env` 里了，要改就改那几行。

### 4. 手动跑一次验证

仓库 → **Actions** → 左侧「讲座邮件提醒」→ 右侧 **Run workflow** → `test` 填 `1` → Run。

跑完看日志：出现「已发送：[测试]【讲座提醒】…」就说明 163 那边接受了。
如果报认证错误，多半是 163 的异地登录风控（GitHub 的机器在美国）。

### 5. 就不用管了

## 以后怎么加讲座（重要）

**只需要改一个文件**，不用碰 cron、不用碰 workflow、不用开电脑：

1. 打开 https://github.com/zhouyan12331/lecture-reminder/blob/main/reminder/lectures.json
2. 点右上角铅笔图标，照葫芦画瓢加一段，`id` 换个没用过的数字：

   ```json
   { "id": 7, "title": "讲座名称", "start": "2026-11-03 14:00",
     "venue": "雁栖湖 教二楼125", "advance_minutes": 60 }
   ```

3. 拉到底点 **Commit changes**。

触发器每 15 分钟来问一次，所以提交后最长 15 分钟就生效，**不需要再做任何事**。

## 已知边界

- **时区**：`start` 写北京时间；workflow 里那条备胎 cron 写的是 UTC，别混。
- **补发窗口 2.5 小时**：提醒时刻过后 2.5 小时内，任何一次触发都会补发；再晚不发，
  避免提醒一场已经开始的讲座。要改就改 `reminder/send.py` 的 `WINDOW`。
- **令牌 2027-01-21 到期**：GitHub 会提前邮件提醒。届时重建一个 fine-grained token
  （只授权本仓库 + Actions: write），再到 cron-job.org 把 `Authorization` 头换掉。
- **cron-job.org 会自动停用**：按它 FAQ，连续失败 25 次会停用任务，所以务必开失败邮件通知；
  即便它挂了，GitHub 那条备胎定时还能兜一层。
- **触发间隔 15 分钟**：提醒会在目标时刻之后 15 分钟内到达，也就是讲座前 **45~60 分钟**。
  想更贴近「整一小时」就到 cron-job.org 把间隔改成 5 分钟，代码和 workflow 都不用动。
- **仓库是 public**：Actions 分钟数不限，每 15 分钟触发（约 96 次/天）不花钱。
  `lectures.json` 公开无妨，授权码在 Secrets 里不会泄露。

## 本地那份还要不要留

要留。它和你电脑是同一套时间表，本地任务只在电脑开着时发、云端只在 GitHub 那边发，
两边都用各自的去重记录，**互不干扰**。电脑开着时你可能会收到两封同样的提醒——
这种情况下删掉本地任务即可：

```powershell
powershell -ExecutionPolicy Bypass -File D:\dsh生活\lecture_reminder\install_tasks.ps1 -Remove
```
