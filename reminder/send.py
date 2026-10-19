# -*- coding: utf-8 -*-
"""云端讲座邮件提醒。

由 GitHub Actions 定时调用（见 .github/workflows/lecture-reminder.yml），
也可以在本机直接跑：

    python reminder/send.py --dry-run     # 只判断不发，看它现在会做什么
    python reminder/send.py --test        # 立刻发一封测试邮件
    python reminder/send.py               # 正常模式：落在时间窗内才发

环境变量（除 SMTP_SSL / LECTURE_TEST 外都必需）：
    SMTP_HOST  SMTP_PORT  SMTP_SSL  SENDER  AUTH_CODE  RECIPIENT

时间表里的时间一律按**北京时间**理解，比较时统一换算成 UTC。
"""
import argparse
import json
import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

BASE = Path(__file__).resolve().parent
LECTURES = BASE / "lectures.json"
SENT_DIR = BASE / "sent"
CST = timezone(timedelta(hours=8))  # 北京时间，无夏令时
# 提醒时刻之后仍允许补发的时长。GitHub 的定时任务可能延迟几分钟，
# 这个窗口既是容忍度，也决定了「最晚什么时候还算有效提醒」。
WINDOW = timedelta(hours=2, minutes=30)


def env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit("缺少环境变量：%s" % name)
    return value


def load_lectures():
    if not LECTURES.exists():
        raise SystemExit("找不到时间表：%s" % LECTURES)
    data = json.loads(LECTURES.read_text(encoding="utf-8"))
    return sorted(data, key=lambda item: item["start"])


def parse_start(lecture):
    """时间表里的开始时间按北京时间解释。"""
    return datetime.strptime(lecture["start"], "%Y-%m-%d %H:%M").replace(tzinfo=CST)


def build_message(lecture, start, remind_at, prefix=""):
    advance = int(lecture.get("advance_minutes", 60))
    weekday = "一二三四五六日"[start.weekday()]
    subject = "%s【讲座提醒】%d 分钟后开始：%s" % (prefix, advance, lecture["title"])
    body = [
        "讲座：%s" % lecture["title"],
        "开始：%s（周%s）%s" % (start.strftime("%Y-%m-%d"), weekday, start.strftime("%H:%M")),
        "地点：%s" % lecture["venue"],
        "本提醒发出时间：%s（比开始时间早 %d 分钟）"
        % (remind_at.astimezone(CST).strftime("%Y-%m-%d %H:%M"), advance),
        "",
        "—— 由 GitHub Actions 云端发出（cloud-reminder）",
    ]
    message = EmailMessage()
    message["From"] = formataddr(("讲座提醒", env("SENDER")))
    message["To"] = env("RECIPIENT")
    message["Subject"] = subject
    message.set_content("\n".join(body), charset="utf-8")
    return message


def send(message, dry_run=False):
    if dry_run:
        print("[dry-run] 本应发送：%s" % message["Subject"])
        return
    host = env("SMTP_HOST")
    port = int(env("SMTP_PORT"))
    sender = env("SENDER")
    code = env("AUTH_CODE")
    context = ssl.create_default_context()
    if os.environ.get("SMTP_SSL", "1").strip() == "1":
        with smtplib.SMTP_SSL(host, port, context=context, timeout=45) as server:
            server.login(sender, code)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=45) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, code)
            server.send_message(message)
    print("已发送：%s -> %s" % (message["Subject"], env("RECIPIENT")))


def main():
    parser = argparse.ArgumentParser(description="云端讲座邮件提醒")
    parser.add_argument("--test", action="store_true", help="立刻发一封测试邮件")
    parser.add_argument("--dry-run", action="store_true", help="只判断，不发信")
    args = parser.parse_args()

    lectures = load_lectures()
    now = datetime.now(timezone.utc)
    print(
        "当前时间：UTC %s / 北京 %s"
        % (now.strftime("%Y-%m-%d %H:%M"), now.astimezone(CST).strftime("%Y-%m-%d %H:%M"))
    )

    test_mode = args.test or os.environ.get("LECTURE_TEST", "").strip() == "1"
    if test_mode:
        lecture = lectures[0]
        start = parse_start(lecture)
        remind_at = start - timedelta(minutes=int(lecture.get("advance_minutes", 60)))
        send(build_message(lecture, start, remind_at, prefix="[测试]"), args.dry_run)
        return 0

    sent = 0
    for lecture in lectures:
        start = parse_start(lecture)
        remind_at = start - timedelta(minutes=int(lecture.get("advance_minutes", 60)))
        marker = SENT_DIR / ("%s.txt" % lecture["id"])
        if marker.exists():
            print("已发过，跳过：#%s %s" % (lecture["id"], lecture["title"]))
            continue
        if remind_at <= now <= remind_at + WINDOW:
            send(build_message(lecture, start, remind_at), args.dry_run)
            if not args.dry_run:
                SENT_DIR.mkdir(parents=True, exist_ok=True)
                marker.write_text(
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC\n"), encoding="utf-8"
                )
            sent += 1
        else:
            print(
                "未到窗口：#%s 提醒时刻 %s（北京），现在 %s（北京）"
                % (
                    lecture["id"],
                    remind_at.astimezone(CST).strftime("%m-%d %H:%M"),
                    now.astimezone(CST).strftime("%m-%d %H:%M"),
                )
            )
    print("本次发送 %d 封。" % sent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
