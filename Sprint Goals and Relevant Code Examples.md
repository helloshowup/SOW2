### **Sprint Goals and Relevant Code Examples** {#sprint-goals-and-relevant-code-examples}

[**Sprint Goals and Relevant Code Examples	1**](#sprint-goals-and-relevant-code-examples)

[1\. Core Backend Setup	1](#1.-core-backend-setup)

[2\. Task Queue & Worker	6](#2.-task-queue-&-worker)

[3\. Web Scraper & Content Evaluation	10](#3.-web-scraper-&-content-evaluation)

[4\. Email Summary & Feedback Capture	15](#4.-email-summary-&-feedback-capture)

[5\. Configuration & Logging	21](#5.-configuration-&-logging)

[6\. Brand Configuration	25](#6.-brand-configuration)

Here's the breakdown with code examples for each sprint goal:

#### **1\. Core Backend Setup** {#1.-core-backend-setup}

**Goal:** Create a FastAPI application with /run-agent endpoint. Implement an APScheduler job to hit /run-agent every 10 minutes. Persist runs in a PostgreSQL table agent\_runs as described in README.

**Relevant Code:**

Python

```

# app/main.py
import os
import httpx
import uvicorn
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Field, SQLModel, create_engine, Session, select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from typing import Optional

# Load environment variables (ensure .env file is present)
from dotenv import load_dotenv
load_dotenv()

# --- Configuration & Logging ---
# (More comprehensive logging setup in the 'Configuration & Logging' section)
log = structlog.get_logger()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@host:5432/dbname") #
if not DATABASE_URL:
    log.critical("DATABASE_URL environment variable is not set. Exiting.")
    exit(1)

# --- Database Setup (SQLModel with PostgreSQL) ---
# Adapt this model to match your agent_runs table structure
class AgentRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str
    result: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSONB)) # For JSONB type in PostgreSQL
    error_message: Optional[str] = None

    # Example: Update method for convenience
    def update_status(self, session: Session, status: str, result: Optional[dict] = None, error_message: Optional[str] = None):
        self.status = status
        self.completed_at = datetime.now()
        if result:
            self.result = result
        if error_message:
            self.error_message = error_message
        session.add(self)
        session.commit()
        session.refresh(self)
        log.info("AgentRun updated", run_id=self.id, status=self.status)

# Create the engine
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    log.info("Creating database tables if they don't exist...")
    SQLModel.metadata.create_all(engine)
    log.info("Database tables created.")

def get_session():
    with Session(engine) as session:
        yield session

# --- APScheduler Setup ---
scheduler = AsyncIOScheduler()

async def trigger_run_agent_endpoint():
    """APScheduler job to hit the /run-agent endpoint."""
    log.info("APScheduler job triggered: Hitting /run-agent endpoint.")
    try:
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient() as client:
            # Adjust the URL if your FastAPI app runs on a different host/port
            response = await client.post("http://localhost:8000/run-agent")
            response.raise_for_status()
            log.info("Successfully triggered /run-agent", status_code=response.status_code, response=response.json())
    except httpx.HTTPStatusError as e:
        log.error("Failed to trigger /run-agent due to HTTP error", exc_info=e)
    except httpx.RequestError as e:
        log.error("Failed to trigger /run-agent due to request error", exc_info=e)
    except Exception as e:
        log.error("An unexpected error occurred while triggering /run-agent", exc_info=e)

# --- FastAPI Application Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    log.info("FastAPI app startup initiated.")
    create_db_and_tables()
    # Schedule the job to run every 10 minutes
    scheduler.add_job(trigger_run_agent_endpoint, IntervalTrigger(minutes=10), id='run_agent_job', replace_existing=True)
    scheduler.start()
    log.info("APScheduler started and job scheduled.")
    yield
    # On shutdown
    log.info("FastAPI app shutdown initiated.")
    if scheduler.running:
        scheduler.shutdown()
        log.info("APScheduler shut down.")

app = FastAPI(lifespan=lifespan)

# --- /run-agent Endpoint ---
@app.post("/run-agent")
async def run_agent(session: Session = Depends(get_session)):
    """
    Endpoint to trigger the AI agent's execution.
    This will enqueue a job and create a pending agent_run record.
    """
    log.info("Received request to /run-agent endpoint.")
    try:
        # Create a new AgentRun entry with 'pending' status
        new_run = AgentRun(status="pending")
        session.add(new_run)
        session.commit()
        session.refresh(new_run) # Refresh to get the generated ID

        # Enqueue the job to the RQ worker (details in next section)
        # For now, let's simulate enqueueing
        job_id = f"agent_run_{new_run.id}" # Example job ID
        log.info("Agent run enqueued (simulated)", run_id=new_run.id, job_id=job_id)

        # In a real scenario, you'd enqueue the task here:
        # from app.worker import q # Assuming q is your RQ queue instance
        # q.enqueue("app.worker.execute_agent_logic", new_run.id) # Pass run ID to worker

        return {"message": "Agent run initiated and enqueued.", "run_id": new_run.id, "job_id": job_id}
    except Exception as e:
        log.error("Failed to initiate agent run", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to initiate agent run: {e}")

# Example endpoint to get all runs (for testing/monitoring)
@app.get("/agent-runs", response_model=list[AgentRun])
async def get_agent_runs(session: Session = Depends(get_session)):
    runs = session.exec(select(AgentRun)).all()
    return runs

# To run this:
# 1. pip install fastapi uvicorn sqlmodel psycopg2-binary apscheduler httpx python-dotenv structlog
# 2. Set your DATABASE_URL in a .env file (e.g., DATABASE_URL="postgresql://user:password@localhost:5432/mydatabase")
# 3. uvicorn app.main:app --reload

```

**Explanation & Best Practices:**

* **app/main.py:** Central file for FastAPI app, database setup, and scheduler.  
* **SQLModel:** Used for ORM, simplifies AgentRun model definition and interaction with PostgreSQL. SQLModel.metadata.create\_all(engine) automatically creates tables on startup if they don't exist.  
* **PostgreSQL with JSONB:** The result field uses JSONB for flexible storage of agent results. Make sure psycopg2-binary is installed for PostgreSQL connectivity.  
* **DATABASE\_URL:** Loaded from environment variables using python-dotenv. Essential for "Fail Fast" to check for its presence.  
* **lifespan Context Manager:** Ensures create\_db\_and\_tables() runs on startup and APScheduler starts/stops gracefully with the FastAPI application.  
* **APScheduler:** Configured to run trigger\_run\_agent\_endpoint every 10 minutes. This function uses httpx to make an asynchronous POST request to the /run-agent endpoint. This internal loopback ensures the scheduler and API are tightly coupled within the same application instance, as per your README.md.

#### **2\. Task Queue & Worker** {#2.-task-queue-&-worker}

**Goal:** Configure Redis with RQ or Celery to queue jobs from the endpoint to a worker process. Worker executes agent logic and updates agent\_runs status/results.

**Relevant Code:**

Python

```

# app/worker.py
import os
import redis
import structlog
from rq import Worker, Queue, Connection
from sqlmodel import create_engine, Session, select
from datetime import datetime
from sqlalchemy import Column # Import Column for JSONB type
from sqlalchemy.dialects.postgresql import JSONB

# Ensure these are consistent with app/main.py
from app.main import AgentRun, DATABASE_URL # Import AgentRun and DATABASE_URL from main
# from app.scraper import scrape_content # Will be implemented later
# from app.openai_evaluator import evaluate_content # Will be implemented later
# from app.email_sender import send_summary_email # Will be implemented later

log = structlog.get_logger()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
if not REDIS_URL:
    log.critical("REDIS_URL environment variable is not set. Exiting worker.")
    exit(1)

# Establish Redis connection for RQ
redis_conn = redis.from_url(REDIS_URL)
q = Queue(connection=redis_conn)

# Database engine for the worker (needs its own connection)
worker_engine = create_engine(DATABASE_URL)

def execute_agent_logic(run_id: int):
    """
    This function will be executed by the RQ worker.
    It contains the core agent logic: scraping, evaluation, and emailing.
    """
    job = Connection(redis_conn).get_current_job() # Get current job for metadata updates
    log.info("RQ Worker: Starting agent logic execution", run_id=run_id, job_id=job.id)

    session = None # Initialize session to None
    try:
        # Get a database session for the worker
        session = Session(worker_engine)
        agent_run = session.get(AgentRun, run_id) # Fetch the pending run record

        if not agent_run:
            log.error("AgentRun record not found for ID", run_id=run_id)
            if job:
                job.meta['status'] = 'failed'
                job.meta['error'] = 'AgentRun record not found'
                job.save_meta()
            return

        # Update status to 'running'
        agent_run.update_status(session, "running")
        log.info("AgentRun status updated to 'running'", run_id=run_id)

        # --- STEP 1: Web Scraping ---
        # scraped_data = scrape_content() # Call your scraping function
        # For demonstration:
        scraped_data = {"title": "Sample Article", "content": "This is some sample content from a website."}
        log.info("Content scraped (simulated)", run_id=run_id)

        # --- STEP 2: OpenAI Content Evaluation ---
        # evaluated_results = evaluate_content(scraped_data['content']) # Call your OpenAI evaluation function
        # For demonstration:
        evaluated_results = {
            "category": "Technology",
            "sentiment": "positive",
            "summary": "This article discusses sample content."
        }
        log.info("Content evaluated with OpenAI (simulated)", run_id=run_id)

        # Sort and get top five results (assuming evaluated_results might be a list of items)
        # For demonstration, creating a dummy list of top 5
        top_five_results = [
            {"rank": 1, "item": "Result A", "score": 0.95},
            {"rank": 2, "item": "Result B", "score": 0.90},
            {"rank": 3, "item": "Result C", "score": 0.85},
            {"rank": 4, "item": "Result D", "score": 0.80},
            {"rank": 5, "item": "Result E", "score": 0.75},
        ]

        # Update AgentRun with success status and results
        agent_run.update_status(session, "completed", result={"scraped_data": scraped_data, "evaluated_results": evaluated_results, "top_five": top_five_results})
        log.info("Agent run completed successfully", run_id=run_id)

        # --- STEP 3: Email Summary ---
        # send_summary_email(top_five_results, run_id) # Call your email sending function
        log.info("Email summary sent (simulated)", run_id=run_id)

        if job: # Update RQ job meta
            job.meta['status'] = 'success'
            job.meta['result_summary'] = f"Completed run_id {run_id}"
            job.save_meta()

    except Exception as e:
        log.error("Error during agent logic execution", run_id=run_id, exc_info=e)
        if session and agent_run:
            agent_run.update_status(session, "failed", error_message=str(e))
        if job: # Update RQ job meta
            job.meta['status'] = 'failed'
            job.meta['error'] = str(e)
            job.save_meta()
    finally:
        if session:
            session.close()

# Main entry point for the RQ worker
if __name__ == '__main__':
    log.info("RQ Worker starting...")
    with Connection(redis_conn):
        worker = Worker([q])
        worker.work()

```

**Explanation & Best Practices:**

* **app/worker.py:** Separate script for the RQ worker. This allows it to run independently.  
* **Redis Connection:** redis.from\_url(REDIS\_URL) establishes the connection. REDIS\_URL should be an environment variable.  
* **RQ Queue and Worker:** The Queue (q) is used by FastAPI to enqueue tasks. The Worker consumes tasks from this queue.  
* **execute\_agent\_logic(run\_id):** This function is the core of your agent. It takes run\_id to retrieve and update the corresponding AgentRun record.  
* **Worker Database Session:** The worker needs its own create\_engine and Session management to interact with PostgreSQL.  
* **job.meta and job.save\_meta():** Crucial for storing intermediate status or results directly on the RQ job, which can be useful for monitoring the job's progress from the API side.  
* **Error Handling:** Comprehensive try...except...finally block to catch exceptions, update the AgentRun status to "failed", and log errors.  
* **Running the Worker:** You would run this from your terminal: python app/worker.py. This can be containerized separately.

#### **3\. Web Scraper & Content Evaluation** {#3.-web-scraper-&-content-evaluation}

**Goal:** Implement simple scraping (requests \+ BeautifulSoup) to gather daily content. Integrate OpenAI API for evaluation and categorization of scraped text, following prompt engineering best practices highlighted in research docs.

**Relevant Code:**

Python

````

# app/scraper.py
import requests
from bs4 import BeautifulSoup
import time
import random
import structlog

log = structlog.get_logger()

# Basic headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_html(url: str, retries: int = 3, delay_sec: float = 1.0) -> Optional[str]:
    """Fetches HTML content from a given URL with retries and delays."""
    for i in range(retries):
        try:
            log.info("Fetching URL", url=url, attempt=i+1)
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            log.info("Successfully fetched URL", url=url)
            return response.text
        except requests.exceptions.RequestException as e:
            log.warning("Failed to fetch URL", url=url, error=str(e), attempt=i+1)
            if i < retries - 1:
                time.sleep(delay_sec + random.uniform(0, 0.5)) # Add a small random delay
    log.error("Max retries exceeded for URL", url=url)
    return None

def parse_content(html_content: str, selector: str = "body") -> str:
    """Parses HTML content to extract text based on a CSS selector."""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Use a more specific selector if available, e.g., "article p", ".main-content"
    elements = soup.select(selector)
    # Concatenate text from all selected elements, stripping extra whitespace
    content = "\n".join([elem.get_text(separator=" ", strip=True) for elem in elements])
    log.info("Content parsed from HTML", selector=selector, content_length=len(content))
    return content

def scrape_content(url: str, selector: str = "body") -> Optional[dict]:
    """Orchestrates fetching and parsing for a given URL."""
    html = fetch_html(url)
    if html:
        text_content = parse_content(html, selector)
        return {"url": url, "raw_html": html, "text_content": text_content}
    return None

# app/openai_evaluator.py
import openai
import os
import structlog
import json # For structured output

log = structlog.get_logger()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    log.critical("OPENAI_API_KEY environment variable is not set. OpenAI API calls will fail.")
    # In a real app, you might want to exit or raise an error here.

openai.api_key = OPENAI_API_KEY

async def evaluate_content(text: str, brand_config: dict) -> Optional[dict]:
    """
    Evaluates and categorizes text using OpenAI's API,
    applying brand-specific keywords and tone.
    """
    if not OPENAI_API_KEY:
        log.error("OpenAI API key is missing. Cannot evaluate content.")
        return None

    # Apply prompt engineering best practices
    # 1. Clear and specific instructions
    # 2. Provide examples (optional, but good for few-shot)
    # 3. Specify the desired output format (JSON recommended for structured data)
    # 4. Use delimiters to clearly separate instructions from context

    brand_keywords = ", ".join(brand_config.get("keywords", []))
    brand_banned_words = ", ".join(brand_config.get("banned_words", []))
    brand_tone = brand_config.get("tone", "neutral and informative")

    prompt = f"""
    You are an AI assistant specialized in content evaluation for the brand "{brand_config.get('name', 'Unknown Brand')}".
    Analyze the provided text and perform the following tasks:

    1.  **Categorization:** Assign one or more relevant categories (e.g., 'News', 'Promotional', 'Review', 'General').
    2.  **Sentiment Analysis:** Determine the overall sentiment (e.g., 'Positive', 'Negative', 'Neutral').
    3.  **Summarization:** Provide a concise summary of the text, adhering to a {brand_tone} tone.
    4.  **Keyword Presence:** Check if any of the brand-specific keywords are present: "{brand_keywords}".
    5.  **Banned Word Check:** Identify if any of the brand-specific banned words are present: "{brand_banned_words}".

    Ensure your response is in JSON format, like this example:
    ```json
    {{
        "categories": ["Category1", "Category2"],
        "sentiment": "SentimentType",
        "summary": "Concise summary.",
        "keywords_present": ["keyword1", "keyword2"],
        "banned_words_found": ["banned_word1"]
    }}
    ```

    ---
    **Text to evaluate:**
    "{text}"
    ---
    """

    messages = [
        {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        log.info("Calling OpenAI API for content evaluation...", text_length=len(text))
        # Use a model that supports JSON mode if available and appropriate, or guide it to JSON output
        response = await openai.ChatCompletion.acreate( # Use acreate for async
            model="gpt-3.5-turbo-0125", # Or gpt-4-turbo, gpt-4o for better results
            messages=messages,
            response_format={"type": "json_object"}, # Specific for JSON output with newer models
            temperature=0.7, # Control creativity; lower for more deterministic output
        )
        # Parse the JSON string from the response
        evaluation_result = json.loads(response.choices[0].message.content)
        log.info("OpenAI evaluation successful", result=evaluation_result)
        return evaluation_result
    except openai.error.OpenAIError as e:
        log.error("OpenAI API error during content evaluation", exc_info=e)
        return None
    except json.JSONDecodeError as e:
        log.error("Failed to parse OpenAI response as JSON", exc_info=e, response_content=response.choices[0].message.content)
        return None
    except Exception as e:
        log.error("An unexpected error occurred during OpenAI evaluation", exc_info=e)
        return None

````

**Explanation & Best Practices:**

* **app/scraper.py:**  
  * **requests and BeautifulSoup:** Standard libraries for web scraping.  
  * **User-Agent & Delays:** Essential for ethical scraping to avoid being blocked. Random delays mimic human Browse.  
  * **Error Handling & Retries:** Robust fetch\_html with retries ensures resilience against transient network issues.  
  * **Specific Selectors:** Emphasized using more specific CSS selectors (soup.select(selector)) for precise content extraction.  
* **app/openai\_evaluator.py:**  
  * **OpenAI API Key:** Loaded from environment variables. Crucial for "Fail Fast."  
  * **Prompt Engineering:** The prompt is crafted following best practices:  
    * Clear instructions at the beginning.  
    * Specification of desired output format (JSON is excellent for structured data).  
    * Use of delimiters (\---) to separate instructions from the content.  
    * Incorporation of brand\_config for dynamic keywords, banned words, and tone.  
  * **Asynchronous API Calls:** openai.ChatCompletion.acreate is used to align with FastAPI's async nature.  
  * **temperature:** Set to 0.7 (or lower for more deterministic output) to control the creativity of the model.  
  * **response\_format={"type": "json\_object"}:** Ensures the model attempts to return valid JSON, improving reliability.  
  * **Robust Error Handling:** Catches OpenAI API errors and JSON parsing errors.

#### **4\. Email Summary & Feedback Capture** {#4.-email-summary-&-feedback-capture}

**Goal:** Use smtplib and email modules to send an email summary of the top five results, as recommended in the workflow doc. Implement a minimal Flask (or FastAPI) endpoint to collect yes/no feedback via links in the email, storing feedback in SQLite for later model refinement.

**Relevant Code:**

Python

```

# app/email_sender.py
import os
import smtplib
import ssl
import structlog
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = structlog.get_logger()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "recipient@example.com") # Default for testing

# Validate email configuration for fail-fast
if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, RECEIVER_EMAIL]):
    log.critical("Email configuration missing. SMTP functions will not work.",
                 smtp_server=bool(SMTP_SERVER), smtp_username=bool(SMTP_USERNAME),
                 smtp_password=bool(SMTP_PASSWORD), sender_email=bool(SENDER_EMAIL),
                 receiver_email=bool(RECEIVER_EMAIL))
    # Consider exiting or raising an error here in a production setup

def send_summary_email(top_five_results: list[dict], run_id: int):
    """
    Sends an email summary of the top five results with feedback links.
    """
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, RECEIVER_EMAIL]):
        log.error("Email configuration is incomplete. Skipping email sending.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Agent Daily Summary - Run {run_id}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    # Create the HTML content for the email
    html_content = f"""\
    <html>
        <body>
            <h2>AI Agent Daily Summary - Run {run_id}</h2>
            <p>Here are the top 5 results from the latest agent run:</p>
            <ul>
    """
    for i, result in enumerate(top_five_results):
        html_content += f"<li><strong>{i+1}. {result.get('item', 'N/A')}</strong> (Score: {result.get('score', 'N/A'):.2f})</li>"
    html_content += """
            </ul>
            <h3>Was this summary helpful?</h3>
            <p>
                <a href="http://localhost:8000/feedback?run_id={run_id}&feedback=yes">Yes, it was helpful!</a> |
                <a href="http://localhost:8000/feedback?run_id={run_id}&feedback=no">No, it was not helpful.</a>
            </p>
        </body>
    </html>
    """
    part1 = MIMEText(html_content, "html")
    msg.attach(part1)

    context = ssl.create_default_context() # Secure connection
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context) # Upgrade to a secure connection
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Email summary sent successfully", run_id=run_id, recipient=RECEIVER_EMAIL)
    except Exception as e:
        log.error("Failed to send email summary", exc_info=e, run_id=run_id)

# app/feedback.py (New module for feedback endpoint)
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Field, SQLModel, create_engine, Session, select
from datetime import datetime
from typing import Optional
import os
import structlog

log = structlog.get_logger()

# SQLite specific database setup for feedback (separate from main PostgreSQL DB)
FEEDBACK_DB_FILE = os.getenv("FEEDBACK_DB_FILE", "feedback.db")
FEEDBACK_DATABASE_URL = f"sqlite:///{FEEDBACK_DB_FILE}"
log.info(f"Using SQLite database for feedback: {FEEDBACK_DATABASE_URL}")

feedback_engine = create_engine(FEEDBACK_DATABASE_URL, echo=True)

class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int
    feedback: str # 'yes' or 'no'
    timestamp: datetime = Field(default_factory=datetime.now)

def create_feedback_db_and_tables():
    log.info("Creating feedback database tables if they don't exist...")
    SQLModel.metadata.create_all(feedback_engine)
    log.info("Feedback database tables created.")

def get_feedback_session():
    with Session(feedback_engine) as session:
        yield session

# Initialize feedback router
feedback_router = APIRouter()

# Call this once on startup of your main app
# In app/main.py's lifespan: create_feedback_db_and_tables() and app.include_router(feedback_router)
# For simplicity, calling it here in app/feedback.py to ensure table creation if this file is run standalone
create_feedback_db_and_tables()

@feedback_router.get("/feedback")
async def collect_feedback(
    run_id: int,
    feedback: str, # Expects 'yes' or 'no'
    session: Session = Depends(get_feedback_session)
):
    """
    Endpoint to collect yes/no feedback via URL links in the email.
    Stores feedback in a SQLite database.
    """
    if feedback.lower() not in ["yes", "no"]:
        log.warning("Invalid feedback received", run_id=run_id, feedback=feedback)
        raise HTTPException(status_code=400, detail="Feedback must be 'yes' or 'no'.")

    try:
        new_feedback = Feedback(run_id=run_id, feedback=feedback.lower())
        session.add(new_feedback)
        session.commit()
        session.refresh(new_feedback)
        log.info("Feedback recorded successfully", run_id=run_id, feedback=feedback)
        # Return a simple HTML response for the user
        return {"message": "Thank you for your feedback!", "feedback_id": new_feedback.id}
    except Exception as e:
        log.error("Failed to record feedback", exc_info=e, run_id=run_id, feedback=feedback)
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {e}")

# To integrate with main.py:
# In app/main.py:
# from app.feedback import feedback_router, create_feedback_db_and_tables
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     create_db_and_tables() # For agent_runs (PostgreSQL)
#     create_feedback_db_and_tables() # For feedback (SQLite)
#     # ... scheduler setup ...
#     app.include_router(feedback_router) # Include the feedback router
#     yield

```

**Explanation & Best Practices:**

* **app/email\_sender.py:**  
  * **EmailMessage and MIMEMultipart:** Used for constructing well-formed email messages, especially for HTML content.  
  * **smtplib with ssl:** Standard way to send emails securely over TLS. Environment variables are used for credentials.  
  * **Feedback Links:** HTML links in the email point to the feedback endpoint with run\_id and feedback as query parameters. The URL http://localhost:8000/feedback should be replaced with your deployed URL.  
  * **Fail-Fast Email Config:** Checks if all necessary SMTP environment variables are set.  
* **app/feedback.py:**  
  * **Separate SQLite DB:** Using SQLite (feedback.db) for feedback is simple and suitable for this minimal requirement, keeping it distinct from the main PostgreSQL database.  
  * **FastAPI APIRouter:** Organizes the feedback endpoint.  
  * **@feedback\_router.get("/feedback"):** Defines the endpoint to capture feedback via GET requests (simplest for email links).  
  * **Query Parameters:** run\_id and feedback are extracted from the URL query string.  
  * **Data Validation:** Checks if feedback is 'yes' or 'no'.  
  * **create\_feedback\_db\_and\_tables():** Ensures the SQLite table is created on startup. This should be called once from your main FastAPI app's lifespan function.

#### **5\. Configuration & Logging** {#5.-configuration-&-logging}

**Goal:** Load configuration from environment variables (python-dotenv), per README recommendations. Add structured logging with structlog.

**Relevant Code:**

Python

```

# app/config.py (New file for configuration management)
import os
from dotenv import load_dotenv
import structlog
import logging
from structlog.processors import JSONRenderer

# Load .env file at the earliest possible point
load_dotenv()

# --- Structured Logging Setup (structlog) ---
# Define common processors
# For console output during development:
def configure_logging_dev():
    structlog.configure(
        processors=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer() # Pretty printing for console
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    # Configure the standard logging to pipe through structlog
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        handlers=[logging.StreamHandler()])
    logging.getLogger("uvicorn").handlers = [] # Prevent duplicate logs from uvicorn
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING) # Reduce SQLAlchemy noise
    logging.getLogger("apscheduler").setLevel(logging.INFO) # Keep APScheduler info

# For JSON output in production/ELK stack:
def configure_logging_prod():
    structlog.configure(
        processors=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            JSONRenderer() # JSON format for ELK stack
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    # Configure the standard logging to pipe through structlog
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        handlers=[logging.StreamHandler()])
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)

# Determine logging configuration based on environment
if os.getenv("ENVIRONMENT") == "production":
    configure_logging_prod()
else:
    configure_logging_dev()

# Global logger instance
log = structlog.get_logger()

# --- Configuration Loading ---
class AppConfig:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    RECEIVER_EMAIL: str = os.getenv("RECEIVER_EMAIL", "recipient@example.com")
    FEEDBACK_DB_FILE: str = os.getenv("FEEDBACK_DB_FILE", "feedback.db")
    # Add any other configurations like brand_repo.yaml path
    BRAND_REPO_PATH: str = os.getenv("BRAND_REPO_PATH", "dev-research/brand_repo.yaml")

    def validate_config(self):
        """Ensures critical environment variables are set (Fail Fast)."""
        required_vars = {
            "DATABASE_URL": self.DATABASE_URL,
            "REDIS_URL": self.REDIS_URL,
            "OPENAI_API_KEY": self.OPENAI_API_KEY,
            "SMTP_SERVER": self.SMTP_SERVER,
            "SMTP_USERNAME": self.SMTP_USERNAME,
            "SMTP_PASSWORD": self.SMTP_PASSWORD,
            "SENDER_EMAIL": self.SENDER_EMAIL,
            "RECEIVER_EMAIL": self.RECEIVER_EMAIL,
        }
        missing_vars = [key for key, value in required_vars.items() if not value]
        if missing_vars:
            log.critical("Missing critical environment variables.", missing=missing_vars)
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        log.info("All required environment variables loaded and validated.")

config = AppConfig()
try:
    config.validate_config()
except ValueError as e:
    # This will typically exit the application early due to the critical log and raise
    log.critical("Application cannot start due to missing configuration.", error=str(e))
    exit(1) # Ensure the application exits if critical config is missing

```

**Explanation & Best Practices:**

* **app/config.py:** A dedicated module for all configuration.  
* **python-dotenv:** load\_dotenv() is called at the very beginning to load variables from .env.  
* **structlog Setup:**  
  * Includes separate configurations for development (console renderer) and production (JSON renderer for ELK stacks).  
  * structlog.stdlib.add\_logger\_name and add\_log\_level enrich logs.  
  * logging.basicConfig routes standard library logging through structlog.  
  * Reduces verbosity for uvicorn and sqlalchemy logs to keep output clean.  
* **AppConfig Class:** Centralizes all configuration variables, making them easily accessible throughout the application. Uses os.getenv with default values.  
* **validate\_config() (Fail Fast):** Explicitly checks for the presence of critical environment variables and raises an error if missing. This adheres to your README.md's "Fail Fast" principle.

#### **6\. Brand Configuration** {#6.-brand-configuration}

**Goal:** Parse dev-research/brand\_repo.yaml to load brand-specific keywords, banned words, and tone. Use this data to tailor search queries and summarization style.

**Relevant Code:**

Python

```

# dev-research/brand_repo.yaml (Example content for structure)
# Make sure this path exists relative to your project root or adjust BRAND_REPO_PATH
brands:
  Debonairs:
    keywords:
      - pizza deals
      - online order
      - triple-decker
      - delivery
    banned_words:
      - old
      - stale
      - bad service
    tone:
      - enthusiastic
      - friendly
      - hunger-inducing
    search_terms_prefix: "Debonairs Pizza"
    # ... other brand-specific settings ...

  AnotherBrand:
    keywords:
      - coffee
      - latte
    banned_words:
      - bitter
    tone:
      - sophisticated
      - calm
    search_terms_prefix: "Another Brand Coffee"

```

Python

```

# app/brand_parser.py (New module)
import yaml
import os
import structlog

log = structlog.get_logger()

# Assuming BRAND_REPO_PATH is defined in app/config.py
from app.config import config

def load_brand_config(brand_name: str) -> Optional[dict]:
    """
    Loads and parses the brand-specific configuration from brand_repo.yaml.
    """
    brand_repo_path = config.BRAND_REPO_PATH
    if not os.path.exists(brand_repo_path):
        log.critical("Brand repository YAML file not found", path=brand_repo_path)
        return None

    try:
        with open(brand_repo_path, 'r') as file:
            brand_data = yaml.safe_load(file) # Safely load YAML
            log.info("Brand repository YAML loaded successfully", path=brand_repo_path)
            
            brands = brand_data.get('brands', {})
            specific_brand_config = brands.get(brand_name)

            if not specific_brand_config:
                log.error("Brand not found in repository", brand_name=brand_name)
                return None
            
            log.info("Brand configuration loaded", brand_name=brand_name, config_keys=list(specific_brand_config.keys()))
            return specific_brand_config

    except yaml.YAMLError as e:
        log.error("Error parsing brand repository YAML", exc_info=e, path=brand_repo_path)
        return None
    except Exception as e:
        log.error("An unexpected error occurred while loading brand config", exc_info=e, path=brand_repo_path)
        return None

# Example usage within app/worker.py's execute_agent_logic:
# from app.brand_parser import load_brand_config
# ...
# def execute_agent_logic(run_id: int):
#     # ...
#     brand_config = load_brand_config("Debonairs") # Load Debonairs config as per README
#     if not brand_config:
#         log.error("Failed to load brand configuration. Cannot proceed with evaluation.")
#         return # Or raise an error

#     # Now pass brand_config to your evaluation function
#     # evaluated_results = evaluate_content(scraped_data['content'], brand_config)
#     # ...

```

**Explanation & Best Practices:**

* **dev-research/brand\_repo.yaml:** Example structure for your YAML file. It's crucial that this file follows a consistent structure for easy parsing.  
* **app/brand\_parser.py:**  
  * **pyyaml (yaml.safe\_load)**: Used for parsing YAML files. safe\_load is recommended for security.  
  * **Dynamic Loading:** The load\_brand\_config function takes a brand\_name to retrieve specific brand settings.  
  * **Integration with openai\_evaluator:** The brand\_config dictionary is passed to the evaluate\_content function.  
  * **Tailoring Search Queries & Summarization:**  
    * **Search Queries:** The search\_terms\_prefix from brand\_config can be prepended to your scraping URLs or used in advanced search engine queries (though direct search engine scraping is often discouraged due to terms of service). For this project's scope, it might influence the *type* of URLs you scrape.  
    * **Summarization Style:** The tone and keywords/banned\_words from brand\_config are directly injected into the OpenAI prompt, effectively guiding the AI's output to match the brand's desired style and focus. This is a direct application of prompt engineering.  
* **Fail-Fast for YAML:** Checks if the brand\_repo.yaml file exists before attempting to load it.

This comprehensive set of code examples and explanations should provide a solid foundation for your sprint, keeping the project within scope and adhering to modern Python best practices. Remember to install all necessary libraries (pip install fastapi uvicorn sqlmodel psycopg2-binary apscheduler httpx python-dotenv structlog redis rq beautifulsoup4 openai pyyaml).

* I will incorporate these by including configuration validation and clear error handling in the code examples.  
* **Modularity:** Keep functions and modules focused. The examples will reflect this by separating concerns (e.g., database, scraping, email).  
* **Type Hinting:** Use Python type hints for better code readability and maintainability, especially with FastAPI and SQLModel.  
* **Asynchronous Operations:** Leverage FastAPI's asynchronous nature (async/await) for I/O-bound operations (database, HTTP requests, external APIs) to avoid blocking the event loop.  
* **Environment Variables:** Strictly adhere to loading configurations from environment variables using python-dotenv.  
* **Structured Logging:** Implement structlog from the outset for better observability.