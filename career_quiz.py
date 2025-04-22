import json
import random
from collections import Counter
import requests

# === Load Question Bank (UTF-8 Encoding) ===
with open("quiz.json", "r", encoding="utf-8") as f:
    full_question_bank = json.load(f)

# Assign unique IDs to each question
for i, q in enumerate(full_question_bank):
    q["id"] = f"q{i+1}"

# === Select Random Questions (No Repeats) ===
def get_random_questions(bank, n=10):
    if n > len(bank):
        raise ValueError(f"Cannot select {n} questions from a pool of {len(bank)}.")
    return random.sample(bank, n)

# === Ask Questions via Terminal ===
def ask_questions_terminal(selected_questions):
    user_answers = {}
    for question in selected_questions:
        print(f"\n{question['question']}")
        for idx, ans in enumerate(question['answers']):
            print(f"{idx + 1}. {ans['text']}")
        while True:
            try:
                choice = int(input("Choose an option (1-{}): ".format(len(question["answers"])))) - 1
                if 0 <= choice < len(question["answers"]):
                    user_answers[question['id']] = choice
                    break
                else:
                    print("Please enter a valid number.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    return user_answers

# === Normalize Skills and Traits ===
def normalize_answer_tags(answer):
    def split_and_strip(items):
        return [i.strip() for i in items] if isinstance(items, list) else [i.strip() for i in items.split(",")]
    skills = split_and_strip(answer.get("skills", []))
    traits = split_and_strip(answer.get("traits", []))
    return skills, traits

# === Build Profile from Answers ===
def build_profile(questions, user_answers):
    traits = Counter()
    skills = Counter()
    for q in questions:
        q_id = q["id"]
        selected_index = user_answers.get(q_id)
        if selected_index is not None:
            answer = q["answers"][selected_index]
            s_tags, t_tags = normalize_answer_tags(answer)
            traits.update(t_tags)
            skills.update(s_tags)
    return {"skills": dict(skills), "traits": dict(traits)}

# === Generate Summary Paragraph ===
def generate_summary(profile):
    top_traits = sorted(profile["traits"], key=profile["traits"].get, reverse=True)[:3]
    top_skills = sorted(profile["skills"], key=profile["skills"].get, reverse=True)[:3]

    trait_summary = ", ".join(top_traits)
    skill_summary = ", ".join(top_skills)

    return (
        f"\n🧠 Based on your responses, you show strong qualities of being {trait_summary.lower()} "
        f"and bring key skills such as {skill_summary.lower()}. You're likely someone who thrives in roles "
        f"that align with both emotional intelligence and practical execution."
    )

# === Get Jobs from O*NET Based on Traits/Skills ===
def get_onet_jobs(profile, username, password):
    url = "https://services.onetcenter.org/ws/online/search"
    keywords = list(profile["skills"].keys())[:3] + list(profile["traits"].keys())[:3]
    search_query = " ".join(keywords)

    params = {"keyword": search_query}
    headers = {
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, params=params, headers=headers, auth=(username, password))
        if response.status_code == 200 and response.text.strip().startswith("{"):
            data = response.json()
            return [item["title"] for item in data.get("occupation", [])]
        else:
            print("❌ O*NET API Error:", response.status_code, response.text)
            return []
    except requests.exceptions.RequestException as e:
        print("❌ Request failed:", e)
        return []

# === Run the Quiz & Match Jobs ===
if __name__ == "__main__":
    selected = get_random_questions(full_question_bank, n=10)
    user_choices = ask_questions_terminal(selected)
    user_profile = build_profile(selected, user_choices)

    # Print summary paragraph
    summary = generate_summary(user_profile)
    print(summary)

    # 🔐 Insert your O*NET API credentials here:
    ONET_USERNAME = "babson_college"      # Replace with your O*NET username
    ONET_PASSWORD = "3793pcu"  # Replace with your O*NET password

    print("\n🔗 Connecting to O*NET for career suggestions...")
    recommended_jobs = get_onet_jobs(user_profile, ONET_USERNAME, ONET_PASSWORD)

    if recommended_jobs:
        print("\n💼 Based on your strengths, here are 5 jobs to consider:")
        for job in recommended_jobs[:10]:  # LIMIT to 10 jobs
            print(f" - {job}")
    else:
        print("\n⚠️ No jobs returned. Check your credentials or try different tags.")
