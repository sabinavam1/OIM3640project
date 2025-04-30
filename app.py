from flask import Flask, render_template, redirect, url_for, session, request
import json
import random
import requests
from requests.auth import HTTPBasicAuth

# Initialize Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

# Load question bank
with open("quiz.json", "r", encoding="utf-8") as f:
    full_question_bank = json.load(f)

# Define adventure stages
stages = [
    "🌊 Job Market Ocean",
    "🏝️ Intern Island",
    "⛰️ Negotiation Mountains",
    "🌳 Skills Jungle",
    "🏔️ Strategy Summit",
    "🌋 Boardroom Volcano",
    "🏢 Golden Corner Office (Treasure!)"
]

# Constants
TOTAL_QUESTIONS = 15

# O*NET credentials
ONET_USERNAME = "babson_college"
ONET_PASSWORD = "3793pcu"

# Helper function for real job matches
def get_onet_jobs(profile, username, password, focus=None):
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

    if not search_query.strip():
        return fallback_jobs

    url = "https://services.onetcenter.org/ws/online/search"
    params = {"keyword": search_query}
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, params=params, headers=headers, auth=HTTPBasicAuth(username, password))
        if response.status_code == 200 and response.text.strip().startswith("{"):
            data = response.json()
            results = [item["title"] for item in data.get("occupation", [])]
            return results if results else fallback_jobs
        else:
            return fallback_jobs
    except requests.exceptions.RequestException:
        return fallback_jobs

# Routes

@app.route('/')
def start():
    session.clear()
    selected_questions = random.sample(full_question_bank, TOTAL_QUESTIONS)
    session['questions'] = selected_questions
    session['current_question'] = 0
    session['answers'] = []
    return render_template('start.html', stages=stages, show_progress=False)

@app.route('/question', methods=['GET', 'POST'])
def question():
    if 'questions' not in session or 'current_question' not in session:
        return redirect(url_for('start'))

    if request.method == 'POST':
        answer = request.form.get('answer')
        if answer:
            session['answers'].append(answer)
            session['current_question'] += 1

    if session['current_question'] >= TOTAL_QUESTIONS:
        return redirect(url_for('result'))

    question_data = session['questions'][session['current_question']]
    current_stage_index = min(session['current_question'] * (len(stages) - 1) // TOTAL_QUESTIONS, len(stages) - 1)
    current_stage = stages[current_stage_index]

    return render_template('question.html', stage=current_stage, question=question_data, stages=stages)

@app.route('/result')
def result():
    if 'answers' not in session or 'questions' not in session:
        return redirect(url_for('start'))

    user_answers = session['answers']
    user_questions = session['questions']

    traits_counter = {}
    skills_counter = {}

    for i, selected_text in enumerate(user_answers):
        if i < len(user_questions):
            question = user_questions[i]
            for answer in question["answers"]:
                if answer["text"] == selected_text:
                    skills = answer.get("skills", [])
                    traits = answer.get("traits", [])
                    for skill in skills:
                        skill = skill.strip().capitalize()
                        skills_counter[skill] = skills_counter.get(skill, 0) + 1
                    for trait in traits:
                        trait = trait.strip().capitalize()
                        traits_counter[trait] = traits_counter.get(trait, 0) + 1

    top_traits = sorted(traits_counter, key=traits_counter.get, reverse=True)[:3]

    profile_for_api = {
        "skills": skills_counter,
        "traits": traits_counter
    }

    recommended_jobs = get_onet_jobs(profile_for_api, ONET_USERNAME, ONET_PASSWORD)
    recommended_jobs = recommended_jobs[:5]

    return render_template('result.html', traits=top_traits, jobs=recommended_jobs, stages=stages, user_answers=user_answers)

if __name__ == "__main__":
    app.run(debug=True)
