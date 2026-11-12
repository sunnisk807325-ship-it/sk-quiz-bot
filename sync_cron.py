import os
import json
import requests

CRON_API_KEY = os.getenv("CRON_API_KEY")
GH_TOKEN = os.getenv("GH_PAT")
REPO_NAME = os.getenv("REPO_NAME", "sunnisk807325-ship-it/sk-quiz-bot")

CRON_HEADERS = {
    "Authorization": f"Bearer {CRON_API_KEY}",
    "Content-Type": "application/json"
}

def get_all_existing_cron_jobs():
    res = requests.get("https://api.cron-job.org/jobs", headers=CRON_HEADERS)
    if res.status_code == 200:
        return res.json().get("jobs", [])
    return []

def delete_cron_job(job_id):
    if not job_id:
        return
    requests.delete(f"https://api.cron-job.org/jobs/{job_id}", headers=CRON_HEADERS)

def create_or_update_cron_job(ch_id, sched_id, title, ist_time, existing_job_id=None):
    hour, minute = map(int, ist_time.split(":"))
    payload = {
        "job": {
            "url": f"https://api.github.com/repos/{REPO_NAME}/actions/workflows/schedule.yml/dispatches",
            "enabled": True,
            "title": f"{ch_id} | {title} ({ist_time} IST)",
            "saveResponses": False,
            "schedule": {
                "timezone": "Asia/Kolkata",
                "expiresAt": 0,
                "hours": [hour],
                "mdays": [-1],
                "minutes": [minute],
                "months": [-1],
                "wdays": [-1]
            },
            "requestMethod": 1,
            "extendedData": {
                "headers": {
                    "Authorization": f"Bearer {GH_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Quiz-Studio-Bot",
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "ref": "main",
                    "inputs": {
                        "target_channel": ch_id,
                        "target_quiz_id": sched_id,
                        "run_mode": "scheduled"
                    }
                })
            }
        }
    }

    if existing_job_id:
        res = requests.patch(f"https://api.cron-job.org/jobs/{existing_job_id}", headers=CRON_HEADERS, json=payload)
        if res.status_code == 200:
            return existing_job_id

    res = requests.put("https://api.cron-job.org/jobs", headers=CRON_HEADERS, json=payload)
    if res.status_code == 200:
        return res.json().get("jobId")
    else:
        print("Cron Error:", res.text)
        return existing_job_id

def main():
    if not os.path.exists("quiz.json"):
        return

    with open("quiz.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    scheduled_map = data.get("scheduled", {})
    active_job_ids = set()

    for ch_id, sched_list in scheduled_map.items():
        if not isinstance(sched_list, list):
            continue
        for item in sched_list:
            ist_time = item.get("ist_time")
            old_job_id = item.get("cron_job_id")
            if ist_time:
                new_id = create_or_update_cron_job(ch_id, item["id"], item.get("title", "Quiz"), ist_time, old_job_id)
                item["cron_job_id"] = new_id
                if new_id:
                    active_job_ids.add(new_id)

    for job in get_all_existing_cron_jobs():
        jid = job.get("jobId")
        if jid and jid not in active_job_ids and "IST)" in job.get("title", ""):
            delete_cron_job(jid)

    with open("quiz.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
    with open("quiz.json", "r", encoding="utf-8") as f:
        all_data = json.load(f)

    active_job_ids = set()

    for ch_id, quizzes in all_data.items():
        if not isinstance(quizzes, list):
            continue
        for quiz in quizzes:
            ist_time = quiz.get("ist_time")
            old_job_id = quiz.get("cron_job_id")
            if ist_time:
                new_id = create_or_update_cron_job(ch_id, quiz["id"], quiz.get("title", "Quiz"), ist_time, old_job_id)
                quiz["cron_job_id"] = new_id
                if new_id:
                    active_job_ids.add(new_id)
            else:
                if old_job_id:
                    delete_cron_job(old_job_id)
                    quiz["cron_job_id"] = None

    for job in get_all_existing_cron_jobs():
        jid = job.get("jobId")
        if jid and jid not in active_job_ids and "IST)" in job.get("title", ""):
            delete_cron_job(jid)

    with open("quiz.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
