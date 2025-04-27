import json
import random
import argparse
import logging
import time
from collections import Counter
from colorama import Fore, Style, init
import requests

# === Initialization ===
init()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

fun_quotes = [
    "Launching careers, one absurd question at a time...",
    "Careers decoded. Ducks and all.",
    "This quiz is 80% science, 20% chaos. Perfect odds.",
    "🌀 Matching vibes with job titles since 2025..."
]
print(random.choice(fun_quotes))
time.sleep(1)

# === Load Question Bank ===
with open("quiz.json", "r", encoding="utf-8") as f:
    full_question_bank = json.load(f)

for i, q in enumerate(full_question_bank):
    q["id"] = f"q{i+1}"

# === Utility Functions ===
def clean_tags(tags):
    return [tag.strip().capitalize() for tag in tags if isinstance(tag, str)]

def normalize_answer_tags(answer):
    skills = clean_tags(answer.get("skills", []))
    traits = clean_tags(answer.get("traits", []))
    return skills, traits

def divider(title):
    print(f"\n{'=' * 10} {title} {'=' * 10}")

def prompt_retake():
    choice = input("\n🔁 Would you like to retake the quiz? (y/n): ").strip().lower()
    return choice == 'y'

def save_to_file(summary, jobs):
    filename = "career_quiz_result.txt"
    with open(filename, "w") as f:
        f.write(summary + "\n\nRecommended Jobs:\n")
        for job in jobs:
            f.write(f"- {job}\n")
    print(f"\n💾 Results saved to {filename}")

def print_advice(profile):
    traits = profile["traits"]
    print("\n💡 Career Advice Based on Your Traits:")
    if "Curious" in traits:
        print(" - You're naturally inquisitive — roles in research or analysis might excite you.")
    if "Creative" in traits or "Expressive" in traits:
        print(" - Your creative side shines. Design, content, or innovation roles could be your jam.")
    if "Bold" in traits:
        print(" - Bold thinkers thrive in leadership, entrepreneurship, or disruptive innovation.")
    if "Supportive" in traits or "Empathetic" in traits:
        print(" - Empathetic people often shine in teaching, HR, or counseling roles.")

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
    ), top_traits, top_skills

# === Enhanced Job Matching with Fallback ===
def get_onet_jobs(profile, username, password, use_mock=False, focus=None):
    fallback_jobs = [
        "Creative Director", "Urban Planner", "UX Researcher", "Brand Strategist",
        "Data Analyst", "HR Specialist", "Product Designer", "Operations Manager",
        "Sustainability Analyst", "Learning Experience Designer"
    ]

    keywords = list(profile["skills"].keys())[:5] + list(profile["traits"].keys())[:5]
    keywords = [k for k in keywords if k and len(k) > 2]
    if focus:
        keywords = [k for k in keywords if focus.lower() in k.lower()]
    search_query = " ".join(keywords)

    if use_mock:
        logging.info("🔁 Using mock job list for demo/testing.")
        return fallback_jobs

    if not search_query.strip():
        logging.warning("⚠️ No valid keywords found, returning fallback jobs.")
        return fallback_jobs

    url = "https://services.onetcenter.org/ws/online/search"
    params = {"keyword": search_query}
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, params=params, headers=headers, auth=(username, password))
        if response.status_code == 200 and response.text.strip().startswith("{"):
            data = response.json()
            results = [item["title"] for item in data.get("occupation", [])]
            if not results:
                logging.warning("⚠️ API returned no jobs — using fallback job list.")
                return fallback_jobs
            return results
        else:
            logging.error("❌ O*NET API Error: %s %s", response.status_code, response.text)
            return fallback_jobs
    except requests.exceptions.RequestException as e:
        logging.error("❌ Request failed: %s", e)
        return fallback_jobs

# === Main Execution ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_questions", type=int, default=15, help="Number of questions to ask")
    parser.add_argument("--mock_api", action="store_true", help="Use mock jobs instead of calling O*NET API")
    parser.add_argument("--focus", type=str, help="Optional focus area (e.g., creative, analytical)")
    parser.add_argument("--save", action="store_true", help="Save result to text file")
    parser.add_argument("--max_retries", type=int, default=5, help="Max number of quiz attempts per session")
    args = parser.parse_args()

    attempts = 0
    while attempts < args.max_retries:
        logging.info(f"Starting quiz attempt {attempts + 1} of {args.max_retries}...")
        selected = get_random_questions(full_question_bank, n=args.num_questions)
        user_choices = ask_questions_terminal(selected)
        user_profile = build_profile(selected, user_choices)

        divider("Career Profile Summary")
        summary, top_traits, top_skills = generate_summary(user_profile)
        print(summary)

        print_advice(user_profile)

        ONET_USERNAME = "babson_college"
        ONET_PASSWORD = "3793pcu"

        logging.info("Connecting to O*NET for career suggestions...")
        recommended_jobs = get_onet_jobs(user_profile, ONET_USERNAME, ONET_PASSWORD, use_mock=args.mock_api, focus=args.focus)

        if recommended_jobs:
            divider("Top 5 Job Matches")
            for job in recommended_jobs[:5]:
                print(f" - {job}")
                
        else:
            print("\n⚠️ No jobs returned. Check your credentials or try different tags.")

        if args.save:
            save_to_file(summary, recommended_jobs[:5])

        attempts += 1
        if attempts >= args.max_retries or not prompt_retake():
            print("\n👋 Thanks for playing! Goodbye.")
            break
