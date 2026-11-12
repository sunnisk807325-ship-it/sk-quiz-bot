import os
import json
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "").strip()
TARGET_QUIZ_ID = os.getenv("TARGET_QUIZ_ID", "").strip()
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    res = requests.post(url, json=payload)
    return res.json()

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
    res = requests.post(url, json=payload)
    return res.json()

def run_single_quiz(ch_id, quiz):
    questions = quiz.get("questions", [])
    if not questions:
        return

    title = quiz.get("title", "Daily Quiz")
    desc = quiz.get("desc", "")
    
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

        send_poll(ch_id, q_text, opts, correct_id, q_time)
        time.sleep(q_time + 2)

    end_text = f"🏁 <b>{title}</b> समाप्त हुआ!\nभाग लेने के लिए सभी का धन्यवाद! 🎉"
    send_message(ch_id, end_text)

def main():
    if not os.path.exists("quiz.json"):
        print("quiz.json नहीं मिली!")
        return

    with open("quiz.json", "r", encoding="utf-8") as f:
        all_quizzes = json.load(f)

    if not all_quizzes:
        print("कोई क्विज़ डेटा नहीं है।")
        return

    channels_to_check = [TARGET_CHANNEL] if (TARGET_CHANNEL and TARGET_CHANNEL in all_quizzes) else list(all_quizzes.keys())

    for ch_id in channels_to_check:
        channel_data = all_quizzes.get(ch_id)
        if not channel_data:
            continue

        # नए मल्टी-क्विज़ लिस्ट फॉर्मेट को हैंडल करना
        quiz_list = channel_data if isinstance(channel_data, list) else [channel_data]

        for quiz in quiz_list:
            if TARGET_QUIZ_ID and quiz.get("id") != TARGET_QUIZ_ID:
                continue
            run_single_quiz(ch_id, quiz)

if __name__ == "__main__":
    main()
