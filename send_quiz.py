import os
import json
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Error: BOT_TOKEN secret nahi mila! GitHub Secrets check karein.")

def send_to_channel(chat_id, quizzes, title, desc):
    start_msg = f"⚡ <b>{title}</b>\n"
    if desc:
        start_msg += f"📝 {desc}\n"
    start_msg += f"\n📊 कुल प्रश्न: {len(quizzes)}\n👇 <i>तैयार रहें...</i>"

    # 1. बैनर भेजना
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": start_msg, "parse_mode": "HTML"}
    )
    time.sleep(2)

    # 2. सवाल भेजना (ठीक 2 सेकंड का अंतराल)
    for idx, q in enumerate(quizzes):
        payload = {
            "chat_id": chat_id,
            "question": f"{idx + 1}. {q['question']}",
            "options": json.dumps(q['options']),
            "type": "quiz",
            "correct_option_id": q.get('correct_option_id', 0),
            "is_anonymous": False,
            "open_period": q.get('time', 15)
        }
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll", json=payload)
        print(f"चैनल {chat_id} -> सवाल {idx + 1}:", res.json().get("ok"))

        if idx < len(quizzes) - 1:
            time.sleep(2)

    # 3. क्विज़ समाप्त संदेश
    end_msg = "🏁 <b>क्विज़ समाप्त!</b>\n\nऊपर दिए गए पोल पर क्लिक करके अपना स्कोर देखें।"
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": end_msg, "parse_mode": "HTML"}
    )

def main():
    with open('quiz.json', 'r', encoding='utf-8') as f:
        quizzes = json.load(f)

    if not quizzes:
        print("Quiz data khali hai.")
        return

    # JSON से टारगेट चैनल निकालना
    target_channels = quizzes[0].get("target_channels", ["@alakhaandeyClass"])
    title = quizzes[0].get("title", "Mega Quiz Series")
    desc = quizzes[0].get("desc", "")

    if isinstance(target_channels, str):
        target_channels = [target_channels]

    # हर चैनल पर 2 सेकंड के अंतराल पर भेजना
    for ch_id in target_channels:
        print(f"\n--- Broadcasting to: {ch_id} ---")
        send_to_channel(ch_id, quizzes, title, desc)
        time.sleep(2)

if __name__ == "__main__":
    main()
