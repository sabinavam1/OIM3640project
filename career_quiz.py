import json
import random
import argparse
import logging
from collections import Counter
from colorama import Fore, Style, init
import requests

# === Initialization ===
init()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# === Load Question Bank (UTF-8 Encoding) ===
with open("quiz.json", "r", encoding="utf-8") as f:
    full_question_bank = json.load(f)

# Assign unique IDs to each question
for i, q in enumerate(full_question_bank):
    q["id"] = f"q{i+1}"

# === Utility Functions ===
def clean_tags(tags):
    return [tag.strip().capitalize() for tag in tags if isinstance(tag, str)]

def normalize_answer_tags(answer):
    skills = clean_tags(answer.get("skills", []))
    traits = clean_tags(answer.get("traits", []))
    return skills, traits

# === Quiz Logic ===
def get_random_questions(bank, n=10):
    if n > len(bank):
        raise ValueError(f"Cannot select {n} questions from a pool of {len(bank)}.")
    return random.sample(bank, n)

def ask_questions_terminal(selected_questions):
    user_answers = {}
    for question in selected_questions:
        print(f"\n{Fore.CYAN}{question['question']}{Style.RESET_ALL}")
        for idx, ans in enumerate(question['answers']):
            print(f"{Fore.YELLOW}{idx + 1}.{Style.RESET_ALL} {ans['text']}")
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

def get_onet_jobs(profile, username, password, use_mock=False):
    if use_mock:
        logging.info("Using mock job list for demo/testing.")
        return ["Creative Director", "Urban Planner", "Systems Analyst"]

    url = "https://services.onetcenter.org/ws/online/search"
    keywords = list(profile["skills"].keys())[:3] + list(profile["traits"].keys())[:3]
    search_query = " ".join(keywords)

    params = {"keyword": search_query}
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, params=params, headers=headers, auth=(username, password))
        if response.status_code == 200 and response.text.strip().startswith("{"):
            data = response.json()
            return [item["title"] for item in data.get("occupation", [])]
        else:
            logging.error("O*NET API Error: %s %s", response.status_code, response.text)
            return []
    except requests.exceptions.RequestException as e:
        logging.error("Request failed: %s", e)
        return []

# === Main Execution ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_questions", type=int, default=10, help="Number of questions to ask")
    parser.add_argument("--mock_api", action="store_true", help="Use mock jobs instead of calling O*NET API")
    args = parser.parse_args()

    logging.info("Starting the career quiz...")
    selected = get_random_questions(full_question_bank, n=args.num_questions)
    user_choices = ask_questions_terminal(selected)
    user_profile = build_profile(selected, user_choices)

    summary = generate_summary(user_profile)
    print(summary)

    ONET_USERNAME = "babson_college"
    ONET_PASSWORD = "3793pcu"

    logging.info("Connecting to O*NET for career suggestions...")
    recommended_jobs = get_onet_jobs(user_profile, ONET_USERNAME, ONET_PASSWORD, use_mock=args.mock_api)

    if recommended_jobs:
        print("\n💼 Based on your strengths, here are 5 jobs to consider:")
        for job in recommended_jobs[:5]:
            print(f" - {job}")
    else:
        print("\n⚠️ No jobs returned. Check your credentials or try different tags.")
