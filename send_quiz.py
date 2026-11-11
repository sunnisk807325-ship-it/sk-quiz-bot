import os
import json
import time
from datetime import datetime, timezone
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def load_quiz_data():
    if not os.path.exists('quiz.json'):
        return {}
    with open('quiz.json', 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def run_channel_quiz(channel_id, channel_data):
    questions = channel_data.get('questions', [])
    quiz_title = channel_data.get('title', 'Daily Live Quiz')
    if not questions:
        return

    # 1. स्टार्ट बैनर
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": channel_id,
        "text": f"🔥 <b>{quiz_title}</b> शुरू हो रहा है!\n\n⚠️ <i>लाइव लीडरबोर्ड चालू है, तेजी से और सही उत्तर दें!</i>",
        "parse_mode": "HTML"
    })
    time.sleep(3)

    scores = {}
    last_update_id = 0

    for idx, q in enumerate(questions):
        options = q['options']
        correct_id = q['correct_option_id']
        # सवाल का व्यक्तिगत टाइमर (10s, 15s या 30s)
        timer = int(q.get('time', 15))

        poll_res = requests.post(f"{BASE_URL}/sendPoll", json={
            "chat_id": channel_id,
            "question": f"[{idx + 1}/{len(questions)}] {q['question']}",
            "options": options,
            "type": "quiz",
            "correct_option_id": correct_id,
            "open_period": timer,
            "is_anonymous": False
        }).json()

        if not poll_res.get('ok'):
            continue

        poll_id = poll_res['result']['poll']['id']
        q_start = time.time()
        q_end = q_start + timer + 2

        # लाइव जवाब ट्रैक करना
        while time.time() < q_end:
            updates = requests.get(f"{BASE_URL}/getUpdates", params={
                "offset": last_update_id + 1,
                "timeout": 1
            }).json()

            if updates.get('ok'):
                for item in updates.get('result', []):
                    last_update_id = item['update_id']
                    if 'poll_answer' in item:
                        ans = item['poll_answer']
                        if ans.get('poll_id') == poll_id:
                            user = ans['user']
                            uid = user['id']
                            uname = user.get('first_name', 'Student')
                            selected = ans['option_ids'][0] if ans['option_ids'] else None

                            if uid not in scores:
                                scores[uid] = {"name": uname, "correct": 0, "total_time": 0.0}

                            time_spent = round(time.time() - q_start, 1)
                            scores[uid]['total_time'] += time_spent
                            if selected == correct_id:
                                scores[uid]['correct'] += 1

            time.sleep(0.5)

        time.sleep(2)  # अगले सवाल से पहले 2 सेकंड ब्रेक

    # 2. रिजल्ट गणना
    ranked = sorted(scores.values(), key=lambda x: (-x['correct'], x['total_time']))

    if not ranked:
        result_text = f"🏁 <b>{quiz_title} समाप्त हुआ!</b>\n\nकिसी छात्र ने उत्तर सबमिट नहीं किया।"
    else:
        result_text = f"🏆 <b>क्विज़ परिणाम: {quiz_title}</b> 🏆\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, u in enumerate(ranked[:10]):
            icon = medals[i] if i < 3 else f"{i + 1}."
            result_text += f"{icon} <b>{u['name']}</b> — {u['correct']}/{len(questions)} सही ({u['total_time']}s)\n"
        result_text += "\n👏 <i>शानदार प्रदर्शन! अगले टेस्ट के लिए तैयार रहें।</i>"

    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": channel_id,
        "text": result_text,
        "parse_mode": "HTML"
    })

def main():
    all_data = load_quiz_data()
    if not all_data:
        print("कोई क्विज़ डेटा नहीं मिला।")
        return

    # अगर डेटा पुराना ऐरे फॉर्मेट है, तो सुरक्षित रूप से चलाएँ
    if isinstance(all_data, list):
        run_channel_quiz("@alakhaandeyClass", {"questions": all_data, "title": "Daily Quiz"})
        return

    # वर्तमान UTC समय (घंटा और मिनट)
    now_utc = datetime.now(timezone.utc)
    cur_m = now_utc.minute
    cur_h = now_utc.hour

    is_manual_trigger = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    for ch_id, ch_info in all_data.items():
        cron = ch_info.get('cron')
        should_run = False

        if is_manual_trigger:
            should_run = True
        elif cron:
            parts = cron.split()
            if len(parts) >= 2:
                cron_m = int(parts[0])
                cron_h = int(parts[1])
                # ±5 मिनट की विंडो (GitHub Actions कतार के लोड को संभालने के लिए)
                if cron_h == cur_h and abs(cron_m - cur_m) <= 5:
                    should_run = True

        if should_run:
            print(f"Running quiz for {ch_id}")
            run_channel_quiz(ch_id, ch_info)

if __name__ == '__main__':
    main()
