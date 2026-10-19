# 云端讲座邮件提醒

不依赖任何一台电脑开机：GitHub 的服务器按点跑，用 163 的 SMTP 把提醒发到你邮箱。

## 它怎么工作

- GitHub Actions 的 cron 只能写 UTC，且**可能延迟几分钟**，所以不追求「卡秒」。
  做法是：在 10/19、10/21、10/23、10/25 这四天**每 30 分钟检查一次**，
  `reminder/send.py` 自己判断「某个讲座的提醒时刻是否已经到达、且还在 2.5 小时的补发窗口内」。
- 发过的场次会在 `reminder/sent/` 下留一个 `<id>.txt`，由 workflow **自动提交回仓库**，
  所以同一场只会发一次，GitHub 反复触发也不会重复轰炸你。
- 时间表里的时间按**北京时间**理解，脚本内部换算成 UTC。

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

之后的发送时刻（北京时间）：

| 场次 | 讲座 | 自动发信 |
|---|---|---|
| #2 | 从分子到田野 | **10/21 11:10** |
| #3 | 量子材料的非平衡动力学及其超快调控 | **10/23 17:30** |
| #4 | 新型医疗电子监测技术 | **10/25 14:30** |

（#1 超声与脑机接口那场 10/19 上午已经过去了，脚本会自动跳过，不会补发。）

## 已知边界

- **GitHub 的定时任务不是精确闹钟**：高峰期可能延迟几分钟到十几分钟，所以留了 2.5 小时补发窗口。
  真要卡到分钟，只能用自建服务器或云函数。
- **定时 workflow 只在默认分支生效**；仓库 60 天无提交会被 GitHub 自动停用定时任务
  （对这次十来天完全不影响，但别把它当长期服务）。
- **163 异地风控**：从美国 IP 登录 SMTP 可能被要求额外验证。测不通就换国内云
  （阿里云函数计算 / 腾讯云 SCF 的定时触发器，国内 IP，但需要实名账号）。
- **10/25 之后**可以把这个 workflow 禁用掉，或删仓库，避免每年 10 月空跑。

## 本地那份还要不要留

要留。它和你电脑是同一套时间表，本地任务只在电脑开着时发、云端只在 GitHub 那边发，
两边都用各自的去重记录，**互不干扰**。电脑开着时你可能会收到两封同样的提醒——
这种情况下删掉本地任务即可：

```powershell
powershell -ExecutionPolicy Bypass -File D:\dsh生活\lecture_reminder\install_tasks.ps1 -Remove
```
