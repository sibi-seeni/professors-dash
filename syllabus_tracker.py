import os
import json
import re
import PyPDF2
from docx import Document
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import models

# --- NEW IMPORTS for LLM ---
from openai import OpenAI
from dotenv import load_dotenv

# --- NEW: Load .env file and initialize client ---
load_dotenv()
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_API_BASE"),
)


# -------------------------
# 1. Extract text from uploaded syllabus (Unchanged)
# -------------------------
def extract_text(file_path: str) -> str:
    if file_path.lower().endswith(".pdf"):
        text_content = ""
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content += text + "\n"
        return text_content

    elif file_path.lower().endswith(".docx"):
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    else:
        raise ValueError("Unsupported file type. Please upload PDF or DOCX.")

# -------------------------
# 2. Parse syllabus text with LLM (REPLACES old function)
# -------------------------

def _extract_json_from_response(content: str) -> list:
    """
    Helper function to safely extract JSON from LLM output.
    (Based on your notebook Cell 5)
    """
    try:
        return json.loads(content)
    except Exception:
        # Fallback to regex if markdown fences are present
        match = re.search(r'(\\[{.*}\\])|(\\{.*\\})', content, re.DOTALL)
        if match:
            raw_json = match.group(0)
            return json.loads(raw_json)
        else:
            print(f"ERROR: Could not find valid JSON roadmap in output: {content}")
            raise ValueError("Could not find valid JSON roadmap in LLM output.")

def parse_syllabus_with_llm(syllabus_text: str) -> list:
    """
    Parses syllabus text into a structured day-by-day roadmap using an LLM.
    (Based on your notebook Cell 4)
    """
    print("Starting LLM-based syllabus roadmap generation...")
    
    # The detailed prompt from your notebook
    detailed_prompt = f"""
    You are a senior academic planner for university-level courses.
    Your job is to analyze the following syllabus and build a day-by-day instructional roadmap in strict JSON format.
    You must create a JSON array, where each element is a distinct instructional class day (skip entries about only policies, admin, grading, honor code, office hours, schedule/overview unless they are taught as actual content).

    For each instructional day in your output, include:
    - 'day': sequential integer starting at 1 (infer if not listed, and skip numbering admin/policy entries)
    - 'date': string date if provided in syllabus, else null/""
    - 'main_topic': the real curriculum subject taught that day (NOT policies or admin items)
    - 'subtopics': list of detailed lesson modules, sections, demos for that day
    - 'objectives': measurable learning goals/skills/competencies students should gain
    - 'activities': list of labs, group work, in-class exercises, demonstrations, class discussions, etc.
    - 'reading': all assigned chapters, papers, articles, links
    - 'assignments': homework, quizzes, projects, presentations, milestones due for that day
    - 'assessment_type': formal check (exam, quiz, project, peer review, etc) on this day, or blank if none
    - 'resources': external links, software, slides, files, tools if in syllabus
    - 'learning_outcomes': explicit or inferred learning outcomes (use objectives if not separated)

    Strict instructions:
    - Only count/number actual content/instructional days. Ignore any admin/policy-only entries unless they are truly being taught as material.
    - If days are not clearly listed or numbering is mixed, infer a sequential order from syllabus structure, date headings, or context.
    - NEVER merge or group multiple days. Output one entry per class day.
    - If multiple subjects are taught in one day, use subtopics but keep one day entry.
    - Always include "Midterm Exam" or "Final Exam" days as entries, even if missing other details.
    - DO NOT output any text except a single, syntactically correct JSON array. No markdown, comments, explanations, or code -- just the plain JSON.

    Here is the syllabus to analyze:
    {syllabus_text}
    """

    response = client.chat.completions.create(
        model="llama-3.1-70b-instruct", # Using model from your notebook
        messages=[
            {"role": "system", "content": "You generate only valid, detailed academic planning JSON for each class day. Never produce non-JSON output."},
            {"role": "user", "content": detailed_prompt}
        ]
    )
    
    output = response.choices[0].message.content
    course_roadmap = _extract_json_from_response(output)
    print("LLM roadmap generation complete.")
    return course_roadmap

# --- (The old parse_syllabus_to_topics function is now deleted) ---


# -------------------------
# 3. Compare with lecture topics from database (Unchanged)
# -------------------------
def calculate_syllabus_coverage(db: Session, syllabus_topics: list):
    """
    Compares the extracted syllabus topics with all lecture topics_json fields.
    Returns coverage statistics.
    (This function is unchanged and now consumes the flattened list)
    """
    print(f"Calculating coverage against {len(syllabus_topics)} syllabus topics...")
    # Fetch topics from all processed lectures
    query = text("""
        SELECT topics_json FROM lectures WHERE status = 'DONE';
    """)
    rows = db.execute(query).fetchall()

    covered_topics = set()
    for row in rows:
        try:
            lecture_topics = json.loads(row[0])
            for t in lecture_topics:
                covered_topics.add(t["topic"].strip().lower())
                for s in t.get("subtopics", []):
                    covered_topics.add(s.strip().lower())
        except Exception:
            continue

    syllabus_set = {t.strip().lower() for t in syllabus_topics}
    matched = [t for t in syllabus_topics if t.strip().lower() in covered_topics]
    missing = [t for t in syllabus_topics if t.strip().lower() not in covered_topics]

    coverage = (len(matched) / len(syllabus_topics) * 100) if syllabus_topics else 0

    return {
        "total_topics": len(syllabus_topics),
        "covered_topics": len(matched),
        "coverage_percentage": round(coverage, 2),
        "missing_topics": missing,
        "matched_topics": matched
    }

# -------------------------
# 4. FastAPI integration (UPDATED)
# -------------------------

def flatten_roadmap_for_coverage(roadmap: list) -> list:
    """
    Helper function to extract all main_topics and subtopics
    from the new JSON roadmap into a simple list of strings
    that calculate_syllabus_coverage expects.
    """
    topics = []
    for day in roadmap:
        if topic := day.get("main_topic"):
            topics.append(topic)
        topics.extend(day.get("subtopics", []))
    return list(set(topics)) # Return unique list

def process_syllabus_file(file_path: str, db: Session):
    """
    High-level wrapper (UPDATED to use LLM).
    """
    # 1. Extract text
    syllabus_text = extract_text(file_path)
    
    # 2. Call LLM to get rich roadmap
    syllabus_roadmap = parse_syllabus_with_llm(syllabus_text)
    
    # 3. Flatten roadmap for old coverage logic
    syllabus_topics_list = flatten_roadmap_for_coverage(syllabus_roadmap)
    
    # 4. Calculate coverage stats
    coverage_stats = calculate_syllabus_coverage(db, syllabus_topics_list)
    
    # 5. Combine both into one result object
    final_result = {
        "coverage_stats": coverage_stats,
        "course_roadmap": syllabus_roadmap
    }
    
    return final_result

# -------------------------
# 5. Save and retrieve results (Unchanged)
# -------------------------
# (These functions will work perfectly, as they just save/load a dict)

RESULTS_DIR = "temp_uploads/syllabus_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

def save_coverage_result(result: dict, filename: str):
    """
    Saves the coverage result JSON for later retrieval.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(filename)[0]
    save_path = os.path.join(RESULTS_DIR, f"{base_name}_{timestamp}.json")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    return save_path


def get_latest_coverage_result():
    """
    Fetches the most recently generated syllabus coverage JSON.
    """
    files = sorted(
        [f for f in os.listdir(RESULTS_DIR) if f.endswith(".json")],
        key=lambda f: os.path.getmtime(os.path.join(RESULTS_DIR, f)),
        reverse=True,
    )

    if not files:
        return None

    latest_file = os.path.join(RESULTS_DIR, files[0])
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # The frontend will now get a 'data' object containing
    # both 'coverage_stats' and 'course_roadmap'
    return {"filename": files[0], "data": data}