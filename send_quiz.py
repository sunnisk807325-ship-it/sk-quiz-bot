import os
import json
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "@alakhaandeyClass"

def send_quizzes():
    with open('quiz.json', 'r', encoding='utf-8') as f:
        quizzes = json.load(f)

    # स्टार्टिंग बैनर
    start_msg = f"⚡ <b>Mega Quiz शुरू हो रहा है!</b>\n📊 कुल प्रश्न: {len(quizzes)}\n\n👇 <i>तैयार रहें...</i>"
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": start_msg, "parse_mode": "HTML"}
    )
    time.sleep(3)

    # 10 सेकंड गैप पर सवाल भेजना
    for idx, q in enumerate(quizzes):
        payload = {
            "chat_id": CHAT_ID,
            "question": f"{idx + 1}. {q['question']}",
            "options": json.dumps(q['options']),
            "type": "quiz",
            "correct_option_id": q['correct_option_id'],
            "is_anonymous": False,
            "open_period": q.get('time', 15)
        }
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll", json=payload)
        print(f"सवाल {idx + 1} भेजा गया:", res.json().get("ok"))

        if idx < len(quizzes) - 1:
            time.sleep(10)

    # रिजल्ट मैसेज
    end_msg = "🏁 <b>क्विज़ समाप्त!</b>\n\nऊपर दिए गए पोल पर क्लिक करके अपना स्कोर देखें।"
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": end_msg, "parse_mode": "HTML"}
    )

if __name__ == "__main__":
    send_quizzes()
