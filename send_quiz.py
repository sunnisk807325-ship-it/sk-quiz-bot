import os
import json
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Error: BOT_TOKEN secret nahi mila!")

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
    time.sleep(3)  # बैनर के बाद 3 सेकंड रुकें

    # 2. सवाल भेजना (टाइमर + 2 सेकंड का सटीक गैप)
    for idx, q in enumerate(quizzes):
        poll_duration = int(q.get('time', 15))  # जो टाइमर आपने ऐप में सेट किया (10s, 15s या 30s)

        payload = {
            "chat_id": chat_id,
            "question": f"{idx + 1}. {q['question']}",
            "options": json.dumps(q['options']),
            "type": "quiz",
            "correct_option_id": q.get('correct_option_id', 0),
            "is_anonymous": False,
            "open_period": poll_duration
        }
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll", json=payload)
        print(f"चैनल {chat_id} -> सवाल {idx + 1} भेजा गया:", res.json().get("ok"))

        # जब तक आख़िरी सवाल न हो, तब तक इंतज़ार करें:
        if idx < len(quizzes) - 1:
            total_wait = poll_duration + 2
            print(f"टाइमर ({poll_duration}s) + 2 सेकंड = कुल {total_wait}s बाद अगला सवाल आएगा...")
            time.sleep(total_wait)

    # आख़िरी सवाल का टाइमर ख़त्म होने का इंतज़ार
    last_wait = int(quizzes[-1].get('time', 15)) + 2
    time.sleep(last_wait)

    # 3. समापन संदेश
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

    target_channels = quizzes[0].get("target_channels", ["@alakhaandeyClass"])
    title = quizzes[0].get("title", "Mega Quiz Series")
    desc = quizzes[0].get("desc", "")

    if isinstance(target_channels, str):
        target_channels = [target_channels]

    for ch_id in target_channels:
        print(f"\n--- Broadcasting to: {ch_id} ---")
        send_to_channel(ch_id, quizzes, title, desc)
        time.sleep(2)

if __name__ == "__main__":
    main()
