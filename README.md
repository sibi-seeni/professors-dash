# Professor's AI Analytics Dashboard

An **AI-powered backend service** designed to provide university professors with deep, actionable insights into their lectures.

This system:

* Transcribes lecture audio
* Uses **Large Language Models (LLMs)** to analyze and structure the content
* Cross-references that content against the official course syllabus to track progress and coverage
* Exposes a clean, fast API to power a frontend dashboard.

---

## 🚀 Core Features

### 🎧 Async Lecture Processing

Upload lecture audio/video files and get an immediate response.
All heavy processing (transcription, AI analysis) happens in the background.

### 🧠 AI-Powered Transcription

Uses **OpenAI’s Whisper-large-v3** for highly accurate lecture transcriptions.

### 🧩 Dual AI Analysis

**Dashboard Analytics**

* LLM generates structured JSON for key metrics:
  topics covered, key points, questions asked, examples used, and a high-level summary.

**Pedagogical Notes**

* A second, detailed LLM call (from `Voice_Text_Transcript_summary_analytics_Note_VF_1.ipynb`) generates rich, publication-quality class notes in JSON.

### 📘 AI Syllabus Parsing

Upload a course syllabus (PDF or DOCX) — an LLM reads and parses it into a **day-by-day JSON “course roadmap”** (from `Course_road_map_.ipynb`).

### 📊 Syllabus Coverage Tracking

Automatically compares **actual topics** from lectures vs **planned topics** from the syllabus.
Outputs a detailed coverage report (e.g., `90% covered, 2 topics missing`).

### 📡 Analytics API

Full suite of API endpoints to power the frontend dashboard:
`/analytics/dashboard`, `/analytics/questions`, and more.

### 🔍 NLP Topic Modeling

Includes **Gensim/NLTK** to perform LDA topic modeling on transcripts as an alternative analysis layer.

---

## 🧱 Tech Stack

| Layer            | Technologies                              |
| ---------------- | ----------------------------------------- |
| **Backend**      | FastAPI, Uvicorn                          |
| **Database**     | SQLAlchemy, SQLite                        |
| **Validation**   | Pydantic                                  |
| **AI & ML**      | OpenAI (Whisper, Llama 3.3), Gensim, NLTK |
| **File Parsing** | PyPDF2, python-docx                       |
| **Async**        | BackgroundTasks (FastAPI)                 |

---

## ⚙️ Setup & Installation

```bash
# 1. Clone the repository
git clone https://github.com/sibi-seeni/professors-dash.git
cd professors-dash

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 🔑 Create Your Environment File

Create a file named `.env` in the root directory and add your keys:

```bash
OPENAI_API_KEY="sk-..."
OPENAI_API_BASE="https_your_proxy_url_com"
```

### ▶️ Run the Application

```bash
uvicorn main:app --reload
```

Your API will be live at:
👉 `http://127.0.0.1:8000`
Interactive Docs:
👉 `http://127.0.0.1:8000/docs`

---

## 🧩 Key API Endpoints

| Method   | Endpoint                      | Description                                                        |
| -------- | ----------------------------- | ------------------------------------------------------------------ |
| **POST** | `/upload/`                    | Upload a lecture audio/video file (triggers background processing) |
| **POST** | `/upload_syllabus/`           | Upload a syllabus PDF/DOCX (triggers AI parsing & coverage)        |
| **GET**  | `/lecture/{lecture_id}`       | Retrieve lecture data (transcript, analytics, notes, etc.)         |
| **GET**  | `/lecture/{lecture_id}/notes` | Get clean JSON of pedagogical class notes                          |
| **GET**  | `/analytics/dashboard`        | Get combined analytics for dashboard UI                            |
| **GET**  | `/syllabus_result/`           | Get latest syllabus coverage report with AI-generated roadmap      |

---

## 🪄 Next Steps: The Road to Canvas Automation

The current workflow requires manual uploads.
The next phase integrates with the **Canvas API** to make the process fully automated — turning this into a hands-free **Teaching Assistant**.

### 1. 🔐 Authentication

* Add `canvasapi` to `requirements.txt`
* Add to `.env`:

  ```bash
  CANVAS_API_URL="https://ufl.instructure.com"
  CANVAS_API_KEY="your_key_here"
  ```
* Create a helper function to initialize the Canvas object.

---

### 2. ⬇️ Pull from Canvas (Automated Ingestion)

#### Replace `POST /upload_syllabus/`

New endpoint:

```http
POST /sync_syllabus/{course_id}
```

* Uses `canvas.get_course(course_id)` to locate the syllabus file.
* Downloads it and passes it to `syllabus_tracker.process_syllabus_file`.

#### Replace `POST /upload/`

New endpoint:

```http
POST /sync_lectures/{course_id}
```

* Lists files in a Canvas folder (e.g., “Lecture Recordings”).
* Detects new files and queues them for background processing with `processing.process_lecture_file`.

---

### 3. ⬆️ Push to Canvas (Automated Publishing)

After background tasks complete:

#### 📝 Auto-Publish Class Notes

* Format `notes_json` into HTML.
* Use `course.create_page()` to publish new “Lecture Notes” pages for students.

#### ❓ Auto-Create Draft Quizzes

* Convert `quiz_json` into `QuizQuestion` format.
* Use `course.create_quiz()` to build new unpublished quizzes for professors to review.

#### 📈 Update Professor’s Dashboard

* Use `syllabus_tracker`’s coverage data.
* Create or update a private **“Instructor Dashboard”** page (`published=False`) inside Canvas.

---

## 🧭 Vision

By integrating with Canvas, this project evolves from a manual dashboard to an **autonomous analytics companion** for educators —
tracking lecture content, syllabus progress, and learning outcomes seamlessly.

---
