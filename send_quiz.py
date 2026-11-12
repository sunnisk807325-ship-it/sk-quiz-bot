import os
import json
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRON_API_KEY = os.getenv("CRON_API_KEY")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "").strip()
TARGET_QUIZ_ID = os.getenv("TARGET_QUIZ_ID", "").strip()
RUN_MODE = os.getenv("RUN_MODE", "scheduled").strip()
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

DEFAULT_END_MSG = "भाग लेने के लिए सभी विद्यार्थियों का हार्दिक धन्यवाद! 🎉\nअपना स्कोर ऊपर लीडरबोर्ड में चेक करें और चैनल को अपने दोस्तों के साथ ज़रूर शेयर करें! 🚀"

def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    return requests.post(url, json=payload).json()

def send_poll(chat_id, question, options, correct_option_id, open_period):
    url = f"{API_URL}/sendPoll"
    payload = {
        "chat_id": chat_id,
        "question": question[:300],
        "options": [opt[:100] for opt in options],
        "type": "quiz",
        "correct_option_id": correct_option_id,
        "is_anonymous": False,
        "open_period": open_period
    }
    return requests.post(url, json=payload).json()

def delete_cron_alarm(job_id):
    if not job_id or not CRON_API_KEY:
        return
    try:
        requests.delete(
            f"https://api.cron-job.org/jobs/{job_id}",
            headers={"Authorization": f"Bearer {CRON_API_KEY}"}
        )
    except Exception as e:
        print("Cron delete error:", e)

def collect_poll_answers(last_offset, poll_correct_map, scores):
    try:
        res = requests.get(
            f"{API_URL}/getUpdates",
            params={"offset": last_offset, "timeout": 1, "allowed_updates": json.dumps(["poll_answer"])}
        ).json()
        if not res.get("ok"):
            return last_offset

        for upd in res.get("result", []):
            last_offset = upd["update_id"] + 1
            pa = upd.get("poll_answer")
            if not pa:
                continue

            poll_id = pa.get("poll_id")
            if poll_id not in poll_correct_map:
                continue

            user = pa.get("user", {})
            uid = str(user.get("id"))
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Participant"

            if uid not in scores:
                scores[uid] = {"name": full_name, "correct": 0, "wrong": 0, "answered_polls": set()}

            if poll_id in scores[uid]["answered_polls"]:
                continue

            option_ids = pa.get("option_ids", [])
            if option_ids:
                scores[uid]["answered_polls"].add(poll_id)
                if option_ids[0] == poll_correct_map[poll_id]:
                    scores[uid]["correct"] += 1
                else:
                    scores[uid]["wrong"] += 1
    except Exception as e:
        print("Update error:", e)
    return last_offset

def build_leaderboard_text(title, total_q, scores):
    if not scores:
        return f"📊 <b>{title} — स्कोरकार्ड</b>\n\nइस क्विज़ में किसी भी प्रतिभागी का वोट दर्ज नहीं हुआ।"

    ranked = sorted(scores.values(), key=lambda x: (-x["correct"], x["wrong"]))
    medals = ["🥇", "🥈", "🥉"]

    lines = [f"🏆 <b>{title} — फाइनल लीडरबोर्ड</b> 🏆\n"]
    for idx, p in enumerate(ranked[:15]):
        rank_badge = medals[idx] if idx < 3 else f"<b>{idx + 1}.</b>"
        lines.append(
            f"{rank_badge} <b>{p['name']}</b>\n"
            f"    ✅ सही: {p['correct']}/{total_q}  |  ❌ गलत: {p['wrong']}"
        )
    return "\n".join(lines)

def run_single_quiz(ch_id, quiz):
    questions = quiz.get("questions", [])
    if not questions:
        return

    title = quiz.get("title", "Daily Quiz")
    desc = quiz.get("desc", "")
    custom_end_msg = quiz.get("end_msg", "").strip() or DEFAULT_END_MSG

    init_upd = requests.get(f"{API_URL}/getUpdates", params={"offset": -1}).json()
    last_offset = 0
    if init_upd.get("ok") and init_upd.get("result"):
        last_offset = init_upd["result"][-1]["update_id"] + 1

    poll_correct_map = {}
    scores = {}

    intro_text = f"🚀 <b>{title}</b> शुरू हो रहा है!\n"
    if desc:
        intro_text += f"📝 <i>{desc}</i>\n"
    intro_text += f"\nकुल प्रश्न: <b>{len(questions)}</b>\nतैयार हो जाइए! 👇"

    send_message(ch_id, intro_text)
    time.sleep(3)

    for idx, q in enumerate(questions, 1):
        q_text = f"Q{idx}. {q['question']}"
        opts = q["options"]
        correct_id = q.get("correct_option_id", 0)
        q_time = int(q.get("time", 15))

        poll_res = send_poll(ch_id, q_text, opts, correct_id, q_time)
        if poll_res.get("ok"):
            poll_id = poll_res["result"]["poll"]["id"]
            poll_correct_map[poll_id] = correct_id

        end_wait = time.time() + q_time + 2
        while time.time() < end_wait:
            last_offset = collect_poll_answers(last_offset, poll_correct_map, scores)
            time.sleep(1.5)

    time.sleep(3)
    last_offset = collect_poll_answers(last_offset, poll_correct_map, scores)

    leaderboard_msg = build_leaderboard_text(title, len(questions), scores)
    send_message(ch_id, leaderboard_msg)
    time.sleep(2)

    end_text = f"🏁 <b>{title} समाप्त हुआ!</b>\n\n{custom_end_msg}"
    send_message(ch_id, end_text)

def main():
    if not os.path.exists("quiz.json"):
        return

    with open("quiz.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if RUN_MODE == "original":
        # ओरिजिनल क्विज़ चलाएँ — चलने के बाद इसे डिलीट न करें
        orig_list = data.get("originals", {}).get(TARGET_CHANNEL, [])
        for quiz in orig_list:
            if quiz.get("id") == TARGET_QUIZ_ID:
                run_single_quiz(TARGET_CHANNEL, quiz)
                break
    else:
        # शेड्यूल्ड क्विज़ चलाएँ — चलने के बाद अलार्म और शेड्यूल्ड लिस्ट से हटाएँ (ओरिजिनल सुरक्षित रहेगा)
        sched_map = data.get("scheduled", {})
        if TARGET_CHANNEL not in sched_map:
            return

        remaining = []
        modified = False
        for quiz in sched_map[TARGET_CHANNEL]:
            if TARGET_QUIZ_ID and quiz.get("id") != TARGET_QUIZ_ID:
                remaining.append(quiz)
                continue

            run_single_quiz(TARGET_CHANNEL, quiz)
            delete_cron_alarm(quiz.get("cron_job_id"))
            modified = True

        if modified:
            data["scheduled"][TARGET_CHANNEL] = remaining
            with open("quiz.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
