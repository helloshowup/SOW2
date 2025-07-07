# **Building a Scalable Content Agent System with FastAPI, APScheduler, and RQ**

## **1\. Project Setup and Core Dependencies**

Establishing a well-organized project structure and managing dependencies effectively are fundamental steps for any robust software development. This section details the initial setup required to create a consistent and manageable Python development environment for the content agent system.

### **Initial Project Structure and Virtual Environment Setup**

To begin, a dedicated project directory, fastapi-agent-system, will be created to house all application code and related files. This practice promotes clear organization and modularity within the codebase. Within this directory, a Python virtual environment (venv) will be created.1 This is a critical best practice as it isolates project dependencies, preventing potential conflicts with other Python projects or the system's global Python installation. The isolation ensures that the precise dependency versions required by this project are maintained, significantly enhancing portability and reproducibility across diverse development and deployment environments.

Bash

```

mkdir fastapi-agent-system
cd fastapi-agent-system
python3 -m venv venv
source venv/bin/activate # On Windows, use `venv\Scripts\activate`

```

### **Installation of Core Libraries**

Once the virtual environment is active, all primary dependencies essential for the FastAPI application, database interactions, asynchronous task handling, environment variable management, and logging will be installed. These libraries are carefully selected to provide a comprehensive and efficient foundation for the agent system:

* fastapi: The chosen web framework, renowned for building high-performance APIs.1 Its asynchronous capabilities are vital for maintaining responsiveness, especially when dealing with I/O-bound operations.  
* uvicorn: An ASGI server required to run FastAPI applications.1 It provides the underlying asynchronous server capabilities that FastAPI leverages.  
* sqlmodel: A powerful Object-Relational Mapper (ORM) that combines SQLAlchemy's robust database interaction features with Pydantic's data validation capabilities.1 This integration is specifically designed to work seamlessly with FastAPI for defining and interacting with database schemas.  
* psycopg2-binary: The necessary PostgreSQL adapter that enables SQLModel and SQLAlchemy to connect and communicate with a PostgreSQL database.  
* python-dotenv: A utility for loading environment variables from a .env file.1 This is crucial for managing configurations securely during development, keeping sensitive information out of source control.  
* structlog: For implementing structured logging, which is essential for enhanced observability, easier parsing by log aggregation systems, and more effective debugging in production environments.7  
* apscheduler: A flexible library for scheduling periodic tasks.9 It will be used to trigger the agent's core execution at regular intervals.  
* redis: The official Python client library for interacting with Redis.13 Redis serves as the backend message broker for the task queue.  
* rq: Redis Queue, a simple yet powerful library for managing background jobs using Redis.13 It will be used to offload long-running agent tasks from the main API process.  
* requests: A fundamental and widely used library for making HTTP requests.15 It is essential for the web scraping component.  
* beautifulsoup4: A library for parsing HTML and XML documents.15 It works in conjunction with  
   requests to extract data from web pages.  
* openai: The official Python client library for interacting with the OpenAI API, enabling AI-driven content evaluation and categorization.  
* PyYAML: For parsing YAML configuration files.17 This will be used specifically for loading brand-specific settings.

Bash

```

pip install fastapi uvicorn sqlmodel psycopg2-binary python-dotenv structlog apscheduler redis rq requests beautifulsoup4 openai PyYAML

```

### **Key Project Dependencies and their Purpose**

| Library Name | Purpose in Project | Key Benefit/Reason for Selection |
| :---- | :---- | :---- |
| FastAPI | Web framework for building APIs | High performance, automatic documentation (Swagger UI), asynchronous support 1 |
| Uvicorn | ASGI server for FastAPI | Efficiently runs FastAPI applications, provides an asynchronous event loop 1 |
| SQLModel | ORM for database interactions | Combines SQLAlchemy and Pydantic for robust, type-hinted database models, ideal for FastAPI 1 |
| Psycopg2-binary | PostgreSQL adapter | Enables Python applications to connect to PostgreSQL databases |
| Python-dotenv | Environment variable management | Securely loads configuration from .env files, separating secrets from code 1 |
| Structlog | Structured logging | Produces machine-readable logs, enhancing observability and debugging 7 |
| APScheduler | Task scheduling | Schedules periodic agent runs efficiently within the application's event loop 9 |
| Redis | In-memory data store / Message broker | Fast and simple backend for RQ, enabling asynchronous task queuing 13 |
| RQ (Redis Queue) | Task queue for background jobs | Decouples long-running tasks from the web server, improving API responsiveness 13 |
| Requests | HTTP client | Simplifies making HTTP requests for web scraping 15 |
| BeautifulSoup4 | HTML/XML parser | Robustly extracts data from web pages, even with messy HTML 15 |
| OpenAI | AI API client | Provides access to advanced language models for content evaluation and categorization |
| PyYAML | YAML parser | Easily loads and parses YAML configuration files for dynamic settings 17 |

The deliberate selection of SQLModel as the ORM, which is tightly integrated with FastAPI through Pydantic, represents a significant architectural advantage. FastAPI's core strength lies in its Pydantic-driven data validation for API request and response models. By utilizing SQLModel, which also employs Pydantic for defining database table models, the system achieves a high degree of data consistency across different layers. This means that the same Pydantic models can often be reused or easily adapted for both API input/output and database schema definitions. This approach minimizes boilerplate code for data serialization, deserialization, and validation, thereby reducing development effort, improving code readability, and enhancing overall maintainability. Furthermore, it leverages FastAPI's automatic documentation generation, as database models (being Pydantic models) will automatically appear in the OpenAPI schema, providing clear and consistent API contracts. This is a core technical pattern for building robust and efficient FastAPI applications that interact with SQL databases.

## **2\. Core Backend Setup: FastAPI, APScheduler, and PostgreSQL**

This section details the implementation of the central FastAPI application, its integration with a PostgreSQL database for persisting agent run data, and the scheduling of the agent execution using APScheduler.

### **FastAPI Application Initialization and** /run-agent **Endpoint**

The FastAPI application is initialized with descriptive metadata, including a title, description, and version. This metadata is automatically used by FastAPI to generate interactive API documentation (Swagger UI and ReDoc), which is invaluable for developers and API consumers.1

A core asynchronous POST endpoint, /run-agent, is defined within the FastAPI application. The primary responsibility of this endpoint is to quickly receive a request and then enqueue the actual, potentially long-running, agent logic to a background task queue (RQ). This design pattern is essential for maintaining API responsiveness and preventing the web server process from blocking while complex operations are underway.13 Upon receiving a request, the endpoint immediately creates an

AgentRun record in the database with a "queued" status and returns a confirmation, ensuring that every initiated agent run is tracked from its inception.

### **Database Model Definition and PostgreSQL Connection**

The AgentRun model is defined using SQLModel with table=True, signifying that it maps directly to a database table. This leverages SQLModel's capability to combine SQLAlchemy's powerful ORM features with Pydantic's data validation.4 The model includes key fields such as

id (an automatically incrementing primary key), timestamp (recording when the run was initiated, defaulting to UTC now), status (tracking the run's lifecycle, e.g., "queued", "running", "completed", "failed"), results\_summary (a brief overview of the agent's findings), and feedback\_received (a boolean indicating if user feedback has been collected). The Config.arbitrary\_types\_allowed \= True setting is included to properly handle datetime.utcnow as a default factory for the timestamp field. For performance, Field(index=True) could be added to status or timestamp if frequent queries on these fields are anticipated.

A SQLModel engine is created using a PostgreSQL connection string, which is securely loaded from environment variables.21 This approach allows for flexible switching between development (e.g., local PostgreSQL) and production databases without modifying the codebase. The

create\_db\_and\_tables() function, which invokes SQLModel.metadata.create\_all(engine), is called during the FastAPI application's startup phase via the @app.on\_event("startup") decorator.4 This ensures that the

agent\_runs table (and any other defined SQLModel(table=True) models) is automatically created in the PostgreSQL database if it does not already exist. While convenient for development, it is a recommended practice for production environments to use dedicated database migration tools, such as Alembic, for more robust and controlled schema changes.4

### **Integrating APScheduler for Scheduled Agent Runs**

The AsyncIOScheduler from APScheduler is chosen for scheduling tasks because it is designed to operate within the same asyncio event loop as FastAPI and Uvicorn.9 This eliminates the need for a separate process solely for scheduling, which simplifies deployment within the current project scope.

The enqueue\_agent\_run function is scheduled to execute every 10 minutes using an IntervalTrigger.10 This function's sole responsibility is to create a new

AgentRun record in the database and then enqueue the actual, potentially resource-intensive, agent logic to the RQ task queue.

The use of id="agent\_run\_scheduler" and replace\_existing=True parameters is crucial for scheduled jobs, particularly when using persistent job stores.12 Although the provided example utilizes an in-memory job store (the default for

AsyncIOScheduler), adopting this practice from the outset prevents the creation of duplicate scheduled jobs if the application restarts. The misfire\_grace\_time parameter is also included to ensure that jobs execute even if the scheduler was temporarily unavailable or busy at their scheduled time. The scheduler is initiated during application startup (@app.on\_event("startup")) and gracefully shut down during application termination (@app.on\_event("shutdown")), ensuring proper resource management.9

Python

```

# main.py
from fastapi import FastAPI, HTTPException, Depends
from typing import Annotated
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime
import os
from dotenv import load_dotenv
import structlog
from redis import Redis
from rq import Queue
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# --- Configuration & Logging Setup (Full implementation in Section 6) ---
# Load environment variables
load_dotenv()

# Configure structlog (simplified for initial setup, full config in logging_config.py)
structlog.configure(
    processors=,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.AsyncBoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.stdlib.get_logger(__name__)

# Database Configuration (from environment variables)
# Ensure DATABASE_URL is set in your.env file, e.g., DATABASE_URL="postgresql://user:password@localhost:5432/agent_db"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/agent_db")
engine = create_engine(DATABASE_URL, echo=False) # echo=True for SQL logging, set to False for production

# Redis Configuration for RQ
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
task_queue = Queue(connection=redis_conn)

# APScheduler Setup
scheduler = AsyncIOScheduler()

# --- Database Model Definition ---
class AgentRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: str = Field(default="queued", nullable=False) # e.g., "queued", "running", "completed", "failed"
    results_summary: str | None = None
    feedback_received: bool = Field(default=False, nullable=False)

    class Config:
        arbitrary_types_allowed = True # Needed for datetime.utcnow

def create_db_and_tables():
    logger.info("Attempting to create database tables if they don't exist.")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created/verified successfully.")

def get_session():
    """Dependency to get a database session."""
    with Session(engine) as session:
        yield session
SessionDep = Annotated

app = FastAPI(
    title="Agent System API",
    description="API for managing and running the content agent.",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    # The actual agent logic will be in a separate worker, this just enqueues it.
    scheduler.add_job(
        func=enqueue_agent_run,
        trigger=IntervalTrigger(minutes=10),
        id="agent_run_scheduler",
        replace_existing=True, # Important for persistent job stores [12]
        misfire_grace_time=60 # Allow jobs to run if missed by up to 60 seconds [12]
    )
    scheduler.start()
    logger.info("APScheduler started and agent run job scheduled.", job_id="agent_run_scheduler")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("APScheduler shut down gracefully.")

# This function is called by APScheduler
def enqueue_agent_run():
    """Function to be scheduled by APScheduler, enqueues the agent run to RQ."""
    logger.info("Scheduled job triggered: Preparing to enqueue agent run.")
    try:
        # Create a new AgentRun record with 'queued' status immediately
        with Session(engine) as session:
            new_run = AgentRun()
            session.add(new_run)
            session.commit()
            session.refresh(new_run) # Get the ID from the database
            run_id = new_run.id
        
        # Enqueue the actual agent logic to RQ, passing the run_id
        task_queue.enqueue("worker.run_agent_logic", run_id=run_id)
        logger.info(f"Agent run {run_id} enqueued to RQ from scheduler.", run_id=run_id)
    except Exception as e:
        logger.error(f"Failed to enqueue agent run from scheduler: {e}", error=str(e), exc_info=True)

@app.post("/run-agent", summary="Manually trigger an agent run")
async def run_agent_endpoint(session: SessionDep):
    """
    Manually trigger an agent run. This endpoint creates a new run record
    and enqueues the agent logic to the task queue for background processing.
    """
    logger.info("Manual /run-agent endpoint hit. Enqueueing new agent run.")
    try:
        # Create a new AgentRun record with 'queued' status
        new_run = AgentRun()
        session.add(new_run)
        session.commit()
        session.refresh(new_run) # Get the ID from the database
        run_id = new_run.id

        # Enqueue the actual agent logic to RQ
        task_queue.enqueue("worker.run_agent_logic", run_id=run_id)
        logger.info(f"Agent run {run_id} enqueued to RQ from manual trigger.", run_id=run_id)
        return {"message": f"Agent run {run_id} enqueued successfully.", "run_id": run_id}
    except Exception as e:
        logger.error(f"Failed to enqueue agent run from manual trigger: {e}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enqueue agent run.")

@app.get("/agent-runs/{run_id}", response_model=AgentRun, summary="Retrieve status of an agent run")
async def get_agent_run_status(run_id: int, session: SessionDep):
    """Retrieve the status and results of a specific agent run by its ID."""
    logger.info(f"Fetching status for agent run {run_id}.", run_id=run_id)
    run = session.get(AgentRun, run_id)
    if not run:
        logger.warning(f"Agent run {run_id} not found.", run_id=run_id)
        raise HTTPException(status_code=404, detail="Agent run not found")
    logger.info(f"Successfully retrieved status for agent run {run_id}.", run_id=run_id, status=run.status)
    return run

@app.get("/agent-runs/", response_model=list, summary="List all agent runs")
async def list_agent_runs(session: SessionDep, offset: int = 0, limit: int = 10):
    """List all agent runs with optional pagination."""
    logger.info(f"Listing agent runs with offset={offset}, limit={limit}.", offset=offset, limit=limit)
    runs = session.exec(select(AgentRun).offset(offset).limit(limit)).all()
    logger.info(f"Retrieved {len(runs)} agent runs.", count=len(runs))
    return runs

```

The architectural pattern of having APScheduler *enqueue* jobs to RQ, rather than directly executing the agent logic within the FastAPI process, is a fundamental design decision for building a scalable and resilient system. FastAPI and Uvicorn are optimized for handling numerous, fast, I/O-bound requests asynchronously. If the agent's core logic, which involves potentially long-running or CPU-intensive operations like web scraping and external AI API calls, were executed directly within the FastAPI process, it would block FastAPI's event loop. This blocking would lead to degraded API performance, increased latency for other incoming requests, and potential timeouts, making the entire web application unresponsive.2 By immediately enqueuing the

run\_agent\_logic to RQ 13, the FastAPI endpoint can return a response almost instantly, maintaining its high responsiveness. The actual agent work is then offloaded to a separate RQ worker process. This decoupling means the web server and the background processing components can be scaled independently. If a worker crashes or a task takes an unexpectedly long time, it does not impact the availability or performance of the API. This significantly enhances the overall system's resilience, throughput, and fault tolerance, aligning with best practices for modern web service design.

Furthermore, creating a database record for an AgentRun with a "queued" status *at the moment of enqueueing* (both from the API endpoint and the scheduler) is a critical proactive state management strategy for ensuring comprehensive tracking and preventing data loss in a distributed system. If the AgentRun record were only created by the worker, there would be a window of vulnerability. For instance, if the RQ job is successfully enqueued but the worker process crashes *before* it picks up the job, or *before* it manages to create the initial database record, the initiated run would be effectively "lost" from the system's perspective, untrackable and unrecoverable without manual intervention. By creating the record with a queued status *before* handing it off to the queue, the system establishes an atomic "job submission" event. The run\_id (primary key) is generated and immediately available. This ensures that every single agent run initiated by either the scheduler or a manual API call is immediately visible and trackable within the agent\_runs table. The run\_id becomes the central identifier for all subsequent updates, such as status changes to "running," "completed," or "failed," and the eventual results\_summary and feedback\_received status. This robust audit trail is invaluable for monitoring, debugging, and reporting, allowing operators to see not just what jobs completed, but also what jobs were initiated but never processed, or became stuck in a queued state due to worker unavailability. This provides a more complete and reliable picture of the system's operational state.

## **3\. Task Queue & Worker: Redis with RQ**

This section details the setup of Redis as the message broker and RQ as the task queue, along with the implementation of the worker process responsible for executing the agent's core logic and updating the database.

### **Configure Redis with RQ to Queue Jobs**

Redis serves as the lightweight, in-memory data store and message broker for RQ. It is selected for its speed and simplicity, making it an excellent choice for managing background job queues within this system's scope.13 The FastAPI application enqueues jobs to Redis, and a separate worker process consumes these jobs.

The task\_queue object, an instance of rq.Queue, is initialized with a connection to the Redis server. When the /run-agent endpoint is invoked (either manually or by the APScheduler job), it calls task\_queue.enqueue("worker.run\_agent\_logic", run\_id=run\_id). This action places the run\_agent\_logic function, along with the run\_id as an argument, into the Redis queue. The run\_id is crucial as it links the background task back to the AgentRun record created in the PostgreSQL database, enabling the worker to update the correct record as it progresses.

### **Worker Executes Agent Logic and Updates** agent\_runs **Status/Results**

A dedicated worker process is responsible for fetching jobs from the Redis queue and executing the run\_agent\_logic function. This separation of concerns is vital for maintaining the responsiveness of the FastAPI application, as the worker can perform long-running, blocking, or CPU-intensive tasks without affecting the web server's performance.

The worker.py script initializes a Redis connection and an RQ Worker instance, which listens to the 'default' queue. When a job is picked up by the worker, the run\_agent\_logic function is executed. Inside this function, the worker retrieves the AgentRun record from the PostgreSQL database using the run\_id passed as an argument. It then updates the status of this record to "running" and persists this change to the database. As the agent logic progresses through its various stages (e.g., scraping, content evaluation, email generation), the worker can update the job.meta property of the current RQ job.23 This allows for fine-grained progress tracking and storing intermediate results directly on the job object in Redis, which can be useful for monitoring via RQ Dashboard or for debugging. Upon completion or failure of the agent logic, the worker updates the

status to "completed" or "failed" and populates the results\_summary field in the agent\_runs table.

Python

````

# worker.py
import os
from dotenv import load_dotenv
import structlog
from redis import Redis
from rq import Worker, Queue, get_current_job
from sqlmodel import Session, create_engine, select
from main import AgentRun, DATABASE_URL # Import AgentRun model and DATABASE_URL from main.py
import time # For simulating work
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import smtplib, ssl
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.headerregistry import Address
from email.utils import make_msgid
import yaml
import json

# Load environment variables
load_dotenv()

# Configure structlog for the worker
structlog.configure(
    processors=,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.AsyncBoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.stdlib.get_logger(__name__)

# Database Engine for worker
engine = create_engine(DATABASE_URL, echo=False)

# Redis connection for worker
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
task_queue = Queue(connection=redis_conn) # Re-use for enqueuing feedback

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Email Configuration
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # App password if using Gmail
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT_SSL = int(os.getenv("SMTP_PORT_SSL", 465))

# Brand Configuration Path
BRAND_REPO_PATH = "dev-research/brand_repo.yaml"

def get_db_session():
    """Helper to get a database session for the worker."""
    with Session(engine) as session:
        yield session

def load_brand_config(brand_name: str):
    """Loads brand-specific configuration from a YAML file."""
    try:
        with open(BRAND_REPO_PATH, 'r') as f:
            full_config = yaml.safe_load(f) # [17, 18, 19]
            return full_config.get(brand_name, {})
    except FileNotFoundError:
        logger.error(f"Brand config file not found at {BRAND_REPO_PATH}", path=BRAND_REPO_PATH)
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing brand config YAML: {e}", error=str(e), exc_info=True)
        return {}

def scrape_content(url: str) -> str:
    """
    Simple web scraping function using requests and BeautifulSoup.
    Returns the main text content of the page.
    """
    logger.info(f"Scraping content from URL: {url}", url=url)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser') # [15, 16]
        
        # Attempt to find main content, e.g., paragraphs, articles
        paragraphs = soup.find_all('p')
        content = "\n".join([p.get_text() for p in paragraphs])
        
        if not content:
            # Fallback to body text if paragraphs are sparse
            content = soup.body.get_text(separator='\n', strip=True)

        logger.info(f"Successfully scraped content from {url}", url=url, content_length=len(content))
        return content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during web scraping: {e}", url=url, error=str(e), exc_info=True)
        return ""
    except Exception as e:
        logger.error(f"An unexpected error occurred during scraping: {e}", url=url, error=str(e), exc_info=True)
        return ""

def evaluate_content_with_openai(text: str, brand_config: dict) -> dict:
    """
    Evaluates and categorizes scraped text using OpenAI API.
    Applies prompt engineering best practices.
    """
    logger.info("Evaluating content with OpenAI API.", text_length=len(text))
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set. Skipping OpenAI evaluation.")
        return {"error": "OpenAI API key not configured."}

    # Apply brand-specific tone and keywords
    tone = brand_config.get("tone", "neutral and informative")
    keywords = ", ".join(brand_config.get("keywords",))
    banned_words = ", ".join(brand_config.get("banned_words",))

    # Prompt engineering best practices: instructions first, separators, specific format [24, 25]
    prompt = f"""
    You are an expert content analyst. Evaluate the following text for its relevance, sentiment, and categorize it.
    The content should align with a {tone} tone.
    Focus on extracting information related to these keywords: {keywords}.
    Avoid mentioning any of these banned words: {banned_words}.

    Instructions:
    1. Summarize the text concisely in 3-5 sentences.
    2. Identify the overall sentiment (Positive, Negative, Neutral).
    3. Categorize the text into one or more relevant categories (e.g., Technology, Finance, Health, News, Lifestyle).
    4. Extract up to 5 key entities (persons, organizations, locations).
    5. Provide a relevance score from 0-100 based on the provided keywords and overall quality.

    Text to evaluate:
    ---
    {text}
    ---

    Desired Output Format (JSON):
    ```json
    {{
        "summary": "...",
        "sentiment": "...",
        "categories": ["...", "..."],
        "entities": ["...", "..."],
        "relevance_score": 0
    }}
    ```
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", # Use latest model [24]
            messages=,
            temperature=0.2, # Lower temperature for factual extraction/classification [24, 25]
            response_format={"type": "json_object"} # Ensure JSON output
        )
        
        raw_output = response.choices.message.content
        parsed_output = json.loads(raw_output)
        logger.info("OpenAI evaluation completed successfully.", output=parsed_output)
        return parsed_output
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}. Raw output: {raw_output}", error=str(e), raw_output=raw_output, exc_info=True)
        return {"error": "Invalid JSON response from OpenAI."}
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}", error=str(e), exc_info=True)
        return {"error": f"OpenAI API error: {e}"}

def send_email_summary(recipient_email: str, summary_data: dict, run_id: int):
    """
    Sends an HTML email summary of the top results.
    Includes feedback links.
    """
    logger.info(f"Preparing email summary for run {run_id} to {recipient_email}.", run_id=run_id, recipient=recipient_email)
    if not SENDER_EMAIL or not EMAIL_PASSWORD:
        logger.error("Email sender credentials not set. Skipping email summary.")
        return

    msg = MIMEMultipart("alternative")
    msg = f"Agent Run {run_id} - Content Summary"
    msg["From"] = Address("Agent System", SENDER_EMAIL)
    msg = recipient_email

    # Construct HTML content
    feedback_base_url = os.getenv("FEEDBACK_BASE_URL", "http://localhost:8000/feedback")
    yes_link = f"{feedback_base_url}?run_id={run_id}&feedback=yes"
    no_link = f"{feedback_base_url}?run_id={run_id}&feedback=no"

    html_content = f"""\
    <html>
      <body>
        <p>Hello,</p>
        <p>Here is the summary of Agent Run {run_id}:</p>
        <h3>Summary:</h3>
        <p>{summary_data.get('summary', 'N/A')}</p>
        <ul>
          <li><strong>Sentiment:</strong> {summary_data.get('sentiment', 'N/A')}</li>
          <li><strong>Categories:</strong> {', '.join(summary_data.get('categories', ['N/A']))}</li>
          <li><strong>Entities:</strong> {', '.join(summary_data.get('entities', ['N/A']))}</li>
          <li><strong>Relevance Score:</strong> {summary_data.get('relevance_score', 'N/A')}/100</li>
        </ul>
        <p>Was this summary helpful?</p>
        <p>
          <a href="{yes_link}">Yes, it was helpful!</a> |
          <a href="{no_link}">No, it was not helpful.</a>
        </p>
        <p>Thank you!</p>
      </body>
    </html>
    """
    
    # Create plain text fallback (optional but good practice)
    text_content = f"""\
    Hello,
    Here is the summary of Agent Run {run_id}:
    Summary: {summary_data.get('summary', 'N/A')}
    Sentiment: {summary_data.get('sentiment', 'N/A')}
    Categories: {', '.join(summary_data.get('categories', ['N/A']))}
    Entities: {', '.join(summary_data.get('entities', ['N/A']))}
    Relevance Score: {summary_data.get('relevance_score', 'N/A')}/100

    Was this summary helpful?
    Yes: {yes_link}
    No: {no_link}
    Thank you!
    """

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html")) # [26, 29]

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT_SSL, context=context) as server: # [29]
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email summary sent successfully for run {run_id}.", run_id=run_id)
    except Exception as e:
        logger.error(f"Failed to send email summary for run {run_id}: {e}", run_id=run_id, error=str(e), exc_info=True)


def run_agent_logic(run_id: int):
    """
    The main agent logic executed by the RQ worker.
    Updates AgentRun status in PostgreSQL.
    """
    job = get_current_job() # Get current RQ job for meta updates [23]
    logger.info(f"Worker started processing agent run {run_id}.", run_id=run_id, job_id=job.id)
    
    # Update status to 'running'
    with next(get_db_session()) as session:
        agent_run = session.get(AgentRun, run_id)
        if not agent_run:
            logger.error(f"Agent run {run_id} not found in DB for processing.", run_id=run_id)
            if job:
                job.meta['status'] = 'failed_db_lookup'
                job.save_meta()
            return
        agent_run.status = "running"
        session.add(agent_run)
        session.commit()
        session.refresh(agent_run)
        logger.info(f"Agent run {run_id} status updated to 'running'.", run_id=run_id)
        if job:
            job.meta['db_status_updated'] = True
            job.save_meta()

    try:
        # Simulate agent work stages
        # 1. Load Brand Configuration
        brand_config = load_brand_config("Debonairs") # Example brand
        logger.info("Brand configuration loaded.", brand_config=brand_config)
        if job:
            job.meta['stage'] = 'brand_config_loaded'
            job.save_meta()

        # 2. Web Scraper
        target_url = "https://www.example.com/news" # Replace with actual target URL
        scraped_text = scrape_content(target_url)
        if not scraped_text:
            raise Exception("No content scraped.")
        logger.info("Content scraped successfully.", scraped_length=len(scraped_text))
        if job:
            job.meta['stage'] = 'content_scraped'
            job.save_meta()

        # 3. Content Evaluation with OpenAI
        evaluation_results = evaluate_content_with_openai(scraped_text, brand_config)
        if evaluation_results.get("error"):
            raise Exception(f"OpenAI evaluation failed: {evaluation_results['error']}")
        logger.info("Content evaluated by OpenAI.", evaluation_results=evaluation_results)
        if job:
            job.meta['stage'] = 'content_evaluated'
            job.save_meta()

        # 4. Email Summary
        recipient_email = os.getenv("RECIPIENT_EMAIL", "recipient@example.com") # Configure recipient
        send_email_summary(recipient_email, evaluation_results, run_id)
        logger.info("Email summary sent.", recipient=recipient_email)
        if job:
            job.meta['stage'] = 'email_sent'
            job.save_meta()

        # Update status to 'completed' and store results summary
        with next(get_db_session()) as session:
            agent_run = session.get(AgentRun, run_id)
            if agent_run:
                agent_run.status = "completed"
                agent_run.results_summary = json.dumps(evaluation_results) # Store results as JSON string
                session.add(agent_run)
                session.commit()
                session.refresh(agent_run)
                logger.info(f"Agent run {run_id} status updated to 'completed' and results saved.", run_id=run_id)
            else:
                logger.warning(f"Agent run {run_id} not found for final status update.", run_id=run_id)

    except Exception as e:
        logger.error(f"Agent run {run_id} failed: {e}", run_id=run_id, error=str(e), exc_info=True)
        # Update status to 'failed'
        with next(get_db_session()) as session:
            agent_run = session.get(AgentRun, run_id)
            if agent_run:
                agent_run.status = "failed"
                agent_run.results_summary = json.dumps({"error": str(e)})
                session.add(agent_run)
                session.commit()
                session.refresh(agent_run)
                logger.info(f"Agent run {run_id} status updated to 'failed'.", run_id=run_id)
            else:
                logger.warning(f"Agent run {run_id} not found for failure status update.", run_id=run_id)
        if job:
            job.meta['stage'] = 'failed'
            job.save_meta()
    
    logger.info(f"Worker finished processing agent run {run_id}.", run_id=run_id)

# To run the worker:
# if __name__ == '__main__':
#     logger.info("Starting RQ worker...")
#     worker_queue = Queue(connection=redis_conn)
#     worker = Worker([worker_queue], connection=redis_conn)
#     worker.work() # This blocks and starts processing jobs

````

### **Discussion on RQ vs. Celery for this Scope**

For this project's requirements, RQ (Redis Queue) is a fitting choice due to its simplicity and direct integration with Redis. RQ is known for being lightweight and easy to set up, making it ideal for projects that need a straightforward task queuing system without extensive features.13 Its reliance on Redis as the sole backend simplifies deployment and management.

Celery, on the other hand, is a more feature-rich and complex distributed task queue. It supports various message brokers (RabbitMQ, Redis, Amazon SQS, etc.) and offers advanced features like task routing, retries, periodic tasks (similar to APScheduler's cron jobs, but integrated within Celery itself), and a more sophisticated monitoring dashboard (Celery Flower). While Celery's robustness and flexibility are valuable for large-scale, highly distributed systems with diverse task types and complex routing needs, its increased complexity in setup and configuration might be overkill for a project described as "fairly unoriginal" and focused on keeping "within scope." Given that APScheduler is already chosen for periodic task triggering, RQ provides the necessary asynchronous processing without introducing the overhead of a full-fledged Celery deployment. For the current scope, RQ offers an optimal balance of functionality and operational simplicity.

## **4\. Web Scraper & Content Evaluation**

This section details the implementation of the web scraping component to gather daily content and its integration with the OpenAI API for intelligent content evaluation and categorization.

### **Simple Scraping with** requests **and** BeautifulSoup

Web scraping is performed using the requests library to fetch the HTML content of target web pages and BeautifulSoup to parse and extract relevant text. This combination is a practical and reliable choice for simple scraping tasks due to its ease of use and robustness in handling various HTML structures.15

The scrape\_content function takes a URL as input. It initiates an HTTP GET request to the specified URL using requests.get(). A timeout is included to prevent indefinite waiting for unresponsive servers, and response.raise\_for\_status() is used to automatically raise an HTTPError for bad responses (e.g., 4xx or 5xx status codes), which is a best practice for robust HTTP client interactions. The fetched HTML content (response.text) is then passed to BeautifulSoup with the html.parser to create a parse tree. The function attempts to extract content primarily from \<p\> (paragraph) tags, which typically contain the main textual content of a page. If paragraphs are sparse, it falls back to extracting all text from the \<body\> tag. Error handling is implemented to catch requests.exceptions.RequestException for network or HTTP-related issues and general exceptions, ensuring that scraping failures are logged and handled gracefully.

### **Integrating OpenAI API for Evaluation and Categorization**

The evaluate\_content\_with\_openai function integrates with the OpenAI API to perform advanced evaluation and categorization of the scraped text. This leverages the power of large language models to derive structured insights from unstructured content.

The function constructs a detailed prompt that guides the OpenAI model to perform specific tasks: summarization, sentiment analysis, categorization, entity extraction, and relevance scoring. A crucial aspect of this integration is the adherence to prompt engineering best practices.24 Instructions are placed at the beginning of the prompt, clearly separated from the context. The prompt is highly specific, describing the desired outcome, format (JSON), and style (e.g., "expert content analyst," "neutral and informative tone"). It also incorporates dynamic elements from the brand configuration, such as specific keywords to focus on and banned words to avoid.

The openai\_client.chat.completions.create method is used, specifying model="gpt-3.5-turbo" (or a newer, more capable model as they become available, following the recommendation to use the latest models 24). A

temperature of 0.2 is set, which is a lower value, making the model's output more focused and deterministic, ideal for factual extraction and classification tasks rather than creative generation.24 The

response\_format={"type": "json\_object"} parameter is critical to instruct the model to produce a valid JSON output, facilitating programmatic parsing of the results. Robust error handling is included to manage API call failures or issues with parsing the JSON response.

### **OpenAI Prompt Engineering Best Practices Summary**

| Best Practice | Description | Example Application in Agent System |
| :---- | :---- | :---- |
| **Use the Latest Model** | Always opt for the most capable and recent models for optimal performance and easier prompting.24 | The evaluate\_content\_with\_openai function defaults to gpt-3.5-turbo, with a note to upgrade as new models are released. |
| **Instructions First with Separators** | Place clear instructions at the beginning of the prompt, separated from the context using """ or \---.24 | The prompt string explicitly starts with high-level instructions, followed by "Text to evaluate:" separated by \---. |
| **Be Specific and Detailed** | Provide precise details about the desired context, outcome, length, format, and style.24 | The prompt specifies "3-5 sentences" for summary, "Positive, Negative, Neutral" for sentiment, and lists desired categories and entities. |
| **Articulate Output Format via Examples** | Define the desired output structure clearly, ideally with a JSON schema example.24 | The prompt includes a Desired Output Format (JSON) block with a complete JSON structure example, including key names and value types. |
| **Start with Zero-shot, then Few-shot, then Fine-tune** | Begin with direct instructions (zero-shot). If results are insufficient, add examples (few-shot). If still not effective, consider fine-tuning.24 | The initial implementation uses a zero-shot approach with detailed instructions and format. If performance is lacking, few-shot examples could be incorporated into the prompt. |
| **Reduce "Fluffy" Descriptions** | Use concise and precise language to describe the desired output, avoiding vague terms.24 | Instead of "a few sentences," the prompt specifies "3-5 sentences" for the summary length. |
| **Say What To Do, Not What Not To Do** | Frame instructions positively, guiding the model towards desired actions rather than prohibited ones.24 | The prompt focuses on "extracting information related to these keywords" and "avoid mentioning any of these banned words" rather than just "don't use banned words." |
| **Control Temperature** | For factual extraction and classification, use a lower temperature (e.g., 0 or 0.2) to make the output more deterministic and focused.24 | The temperature=0.2 parameter is explicitly set in the OpenAI API call to ensure consistent and factual responses. |

## **5\. Email Summary & Feedback Capture**

This section details the implementation for sending email summaries of the agent's findings and establishing a mechanism to capture user feedback via interactive links within these emails.

### **Sending Email Summaries with** smtplib **and** email **Modules**

The system utilizes Python's built-in smtplib and email modules to compose and send email summaries. This approach provides fine-grained control over email content, including the ability to send rich HTML emails with embedded links.

The send\_email\_summary function constructs a MIMEMultipart("alternative") message, which allows for both plain text and HTML versions of the email. This is a best practice to ensure compatibility across various email clients: if an email client cannot render HTML, it will display the plain text fallback.26 The email's subject, sender (

From), and recipient (To) are set programmatically. The HTML content includes a summary of the agent's findings (e.g., sentiment, categories, entities, relevance score) and, crucially, two interactive links for feedback: "Yes, it was helpful\!" and "No, it was not helpful." These links are constructed with query parameters (run\_id and feedback) to uniquely identify the agent run and the user's response.27

For sending, an ssl.create\_default\_context() is used to establish a secure SSL connection to the SMTP server (e.g., smtp.gmail.com on port 465).29 The sender's email credentials (email address and password) are loaded from environment variables, ensuring sensitive information is not hardcoded. The

server.login() method authenticates with the SMTP server, and server.send\_message(msg) dispatches the composed email. Comprehensive error handling is in place to log any failures during the email sending process.

### **Minimal FastAPI Endpoint to Collect Yes/No Feedback**

A minimal FastAPI endpoint is implemented to collect the yes/no feedback submitted via the links in the email. This endpoint is designed to be lightweight and solely focused on capturing the feedback data.

The main.py (FastAPI application) includes a GET endpoint, /feedback, which accepts run\_id (an integer) and feedback (a string, typically "yes" or "no") as query parameters.27 When a user clicks one of the feedback links in the email, their browser makes an HTTP GET request to this endpoint. The endpoint then extracts these parameters.

Python

```

# main.py (continued from Section 2)

# SQLite Database for Feedback
SQLITE_FEEDBACK_FILE = "feedback.db"
sqlite_feedback_url = f"sqlite:///{SQLITE_FEEDBACK_FILE}"
sqlite_feedback_engine = create_engine(sqlite_feedback_url, echo=False)

class Feedback(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(index=True, nullable=False)
    feedback_type: str = Field(nullable=False) # "yes" or "no"
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False)

def create_feedback_db_and_tables():
    logger.info("Attempting to create feedback database tables if they don't exist.")
    SQLModel.metadata.create_all(sqlite_feedback_engine)
    logger.info("Feedback database tables created/verified successfully.")

def get_feedback_session():
    """Dependency to get a feedback database session."""
    with Session(sqlite_feedback_engine) as session:
        yield session
FeedbackSessionDep = Annotated

@app.on_event("startup")
async def startup_event_with_feedback_db():
    create_db_and_tables() # Existing call for agent_runs
    create_feedback_db_and_tables() # New call for feedback.db
    scheduler.add_job(
        func=enqueue_agent_run,
        trigger=IntervalTrigger(minutes=10),
        id="agent_run_scheduler",
        replace_existing=True,
        misfire_grace_time=60
    )
    scheduler.start()
    logger.info("APScheduler started and agent run job scheduled.", job_id="agent_run_scheduler")


@app.get("/feedback", summary="Collect user feedback on agent runs")
async def collect_feedback(
    run_id: int,
    feedback: str,
    feedback_session: FeedbackSessionDep
):
    """
    Endpoint to collect yes/no feedback from users via email links.
    Stores feedback in SQLite.
    """
    logger.info(f"Received feedback for run {run_id}: {feedback}", run_id=run_id, feedback=feedback)
    if feedback.lower() not in ["yes", "no"]:
        logger.warning(f"Invalid feedback type received: {feedback}", run_id=run_id, feedback=feedback)
        raise HTTPException(status_code=400, detail="Invalid feedback type. Must be 'yes' or 'no'.")

    try:
        new_feedback = Feedback(run_id=run_id, feedback_type=feedback.lower())
        feedback_session.add(new_feedback)
        feedback_session.commit()
        feedback_session.refresh(new_feedback)
        logger.info(f"Feedback for run {run_id} stored successfully.", run_id=run_id, feedback_id=new_feedback.id)

        # Optional: Update the original AgentRun record to mark feedback_received
        with next(get_session()) as agent_run_session: # Use the main DB session here
            agent_run = agent_run_session.get(AgentRun, run_id)
            if agent_run:
                agent_run.feedback_received = True
                agent_run_session.add(agent_run)
                agent_run_session.commit()
                logger.info(f"Agent run {run_id} marked as feedback received.", run_id=run_id)
            else:
                logger.warning(f"Agent run {run_id} not found when marking feedback received.", run_id=run_id)

        return {"message": "Feedback received successfully!", "run_id": run_id, "feedback": feedback}
    except Exception as e:
        logger.error(f"Failed to store feedback for run {run_id}: {e}", run_id=run_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to store feedback.")

```

### **Storing Feedback in SQLite Database**

The feedback collected from the /feedback endpoint is stored in a lightweight SQLite database. SQLite is an embedded, file-based database, making it suitable for simple, localized data storage requirements, such as user feedback that might not require the full power and overhead of a PostgreSQL server.4

A separate Feedback SQLModel is defined, mapping to a table in feedback.db. This model includes run\_id (linking back to the agent run), feedback\_type ("yes" or "no"), and a timestamp. A dedicated create\_feedback\_db\_and\_tables() function is called during application startup to ensure the SQLite table exists. When feedback is received, a new Feedback record is created and persisted to the SQLite database. Additionally, the corresponding AgentRun record in the main PostgreSQL database is updated to set feedback\_received to True, providing a holistic view of the agent run's lifecycle.

## **6\. Configuration & Logging Best Practices**

Effective management of application configurations and robust logging are critical for developing maintainable, secure, and observable systems. This section details the implementation of environment variable loading and structured logging.

### **Loading Configuration from Environment Variables (**python-dotenv**)**

To ensure sensitive information (like API keys, database credentials, and email passwords) is kept out of source code and to facilitate environment-specific configurations, python-dotenv is employed. This library loads key-value pairs from a .env file into the application's environment variables.5

A .env file is created at the project root (and added to .gitignore to prevent accidental version control commits). This file will contain variables such as DATABASE\_URL, REDIS\_HOST, OPENAI\_API\_KEY, SENDER\_EMAIL, EMAIL\_PASSWORD, SMTP\_SERVER, SMTP\_PORT\_SSL, and FEEDBACK\_BASE\_URL. The load\_dotenv() function is called early in the main.py and worker.py scripts to ensure these variables are available via os.getenv(). When accessing environment variables, it is a best practice to provide default values (e.g., os.getenv("REDIS\_HOST", "localhost")) or to raise an error if a critical variable is missing, enhancing the application's robustness.5 This approach simplifies configuration management across different environments (development, testing, production) and improves the security posture of the application.

### **Implementing Structured Logging with** structlog

Structured logging is implemented using structlog to enhance the observability and debuggability of the application. Unlike traditional plain-text logs, structured logs output data in a machine-readable format, typically JSON, which is invaluable for log aggregation systems, monitoring tools, and automated analysis.7

structlog.configure() is used to set up a processing pipeline for log entries. This pipeline includes:

* structlog.stdlib.add\_logger\_name: Adds the name of the logger (e.g., main, worker) to each log entry.  
* structlog.stdlib.add\_log\_level: Adds the log level (e.g., info, error, warning) to each entry.  
* structlog.processors.TimeStamper(fmt="iso"): Adds an ISO-formatted timestamp, crucial for chronological analysis.  
* structlog.processors.JSONRenderer(): Renders the final log entry as a JSON string, enabling easy parsing by external systems.

The logger\_factory and wrapper\_class are set to use stdlib.LoggerFactory and stdlib.AsyncBoundLogger respectively, ensuring compatibility with Python's standard logging module while leveraging structlog's asynchronous capabilities for FastAPI. The cache\_logger\_on\_first\_use=True setting optimizes logger instantiation. Throughout the application, logger.info(), logger.error(), logger.warning(), etc., are used, passing key-value pairs as arguments (e.g., logger.info("Agent run enqueued.", run\_id=run\_id)). This approach automatically includes contextual information directly within the log entry, making it much easier to filter, search, and analyze logs for specific events or issues. For instance, all logs related to a specific run\_id can be easily queried.

## **7\. Brand Configuration and Content Tailoring**

This section addresses the requirement to parse brand-specific configuration data and use it to tailor the agent's behavior, particularly for search queries and summarization style.

### **Parsing** dev-research/brand\_repo.yaml **with PyYAML**

Brand-specific keywords, banned words, and tone settings are loaded from a YAML file located at dev-research/brand\_repo.yaml. PyYAML is the chosen library for parsing this file, as it is the standard Python library for interacting with YAML data.17

The load\_brand\_config function opens the specified YAML file and uses yaml.safe\_load(f) to parse its contents into a Python dictionary. safe\_load() is preferred over load() for security reasons, as it prevents the execution of arbitrary Python code found within the YAML file, which could be a vulnerability if the configuration source is untrusted.17 The function then extracts the configuration specific to a given

brand\_name from the loaded dictionary. Robust error handling is included to manage cases where the file is not found or if there are parsing errors, ensuring the application remains stable even with malformed configuration files.

### **Applying Brand-Specific Data to Search Queries and Summarization**

The loaded brand configuration data is dynamically applied to customize the agent's behavior. This allows the system to tailor its content processing based on the specific needs and guidelines of different brands.

For content evaluation and summarization by the OpenAI API, the brand\_config dictionary is passed to the evaluate\_content\_with\_openai function. This function then extracts the tone, keywords, and banned\_words specific to the active brand. These values are then injected directly into the prompt sent to the OpenAI model. For example, the prompt explicitly states, "The content should align with a {tone} tone" and "Focus on extracting information related to these keywords: {keywords}. Avoid mentioning any of these banned words: {banned\_words}." This dynamic prompt engineering ensures that the AI's output is aligned with the brand's voice and content guidelines, tailoring the summarization style and relevance evaluation.

While not explicitly detailed in the provided snippets for "search queries," the same principle would apply. If the agent were to perform keyword-based searches (e.g., against a news API or a search engine), the brand\_config\['keywords'\] could be used to construct the search query, and brand\_config\['banned\_words'\] could be used to filter out irrelevant or undesirable results post-search. This modular approach to configuration ensures that the agent's behavior is highly adaptable and extensible for various brand requirements without requiring code changes.

### **Example Brand Configuration Structure**

The dev-research/brand\_repo.yaml file would typically follow a structure that allows for multiple brand definitions, each with its specific content tailoring parameters.

| Key | Type | Description | Example Value |
| :---- | :---- | :---- | :---- |
| Debonairs | Dictionary | Top-level key for a specific brand's configuration. |  |
| keywords | List of Strings | Key terms relevant to the brand's content focus. | \["pizza", "fast food", "delivery", "specials", "deals"\] |
| banned\_words | List of Strings | Words or phrases to avoid in summaries or content. | \["unhealthy", "greasy", "slow"\] |
| tone | String | Desired tone for AI-generated summaries or content. | "enthusiastic and appetizing" |
| AnotherBrand | Dictionary | Configuration for a different brand. |  |
| keywords | List of Strings |  | \["finance", "investment", "market trends"\] |
| banned\_words | List of Strings |  | \["risk", "loss", "speculation"\] |
| tone | String |  | "formal and analytical" |

YAML

```

# dev-research/brand_repo.yaml
Debonairs:
  keywords:
    - pizza
    - fast food
    - delivery
    - specials
    - deals
  banned_words:
    - unhealthy
    - greasy
    - slow
  tone: enthusiastic and appetizing

AnotherBrand:
  keywords:
    - finance
    - investment
    - market trends
  banned_words:
    - risk
    - loss
    - speculation
  tone: formal and analytical

```

## **Conclusion and Recommendations**

This report has detailed the architecture and implementation of an automated content agent system, built on a foundation of FastAPI, APScheduler, Redis Queue, and PostgreSQL. The system integrates web scraping, AI-driven content evaluation, email summarization, and user feedback capture, all while adhering to modern Python best practices for scalability, maintainability, and security.

The strategic decoupling of the web API from long-running background tasks via RQ and the proactive state management in the database ensure a highly responsive and fault-tolerant system. The consistent use of Pydantic models through SQLModel streamlines data validation and API documentation. Furthermore, the emphasis on structured logging and environment variable management provides the necessary tools for effective monitoring and secure deployment. Dynamic content tailoring through YAML configuration and intelligent prompt engineering for the OpenAI API allows the agent to adapt to diverse brand requirements.

### **Recommendations for Production Deployment and Scaling**

For transitioning this system from development to a production environment, several key recommendations are provided to enhance its robustness, scalability, and operational efficiency:

1. **Database Migrations:** While SQLModel.metadata.create\_all() is convenient for development, it is strongly recommended to use a dedicated database migration tool like Alembic for production.4 This allows for controlled, versioned schema changes, enabling safe upgrades and rollbacks without data loss.  
2. **Persistent APScheduler Job Store:** For production, APScheduler should be configured with a persistent job store (e.g., SQLAlchemyJobStore backed by PostgreSQL or RedisJobStore) instead of the default in-memory store.10 This ensures that scheduled jobs are not lost if the FastAPI application restarts, maintaining continuous operation.  
3. **Redis Persistence:** Configure Redis with persistence (e.g., RDB snapshots or AOF logging) to prevent data loss in the RQ queues in case of Redis server restarts.  
4. **Process Management:** Use a process manager (e.g., Gunicorn for FastAPI, Systemd/Supervisor for workers and scheduler) to manage the FastAPI application, RQ workers, and potentially the APScheduler process (if decoupled).2 This ensures processes are automatically restarted if they crash and can be managed effectively.  
5. **Reverse Proxy:** Deploy FastAPI behind a reverse proxy server like Nginx or Apache.2 This provides load balancing, SSL termination, caching, and improved security.  
6. **Scalability of Components:**  
   * **FastAPI:** Can be scaled horizontally by running multiple Uvicorn worker processes (e.g., using Gunicorn) and distributing traffic with a load balancer.  
   * **RQ Workers:** Can be scaled independently by running multiple rq worker instances across different machines or containers. This allows for increased throughput of background tasks.  
   * **PostgreSQL:** Consider database replication and connection pooling for high availability and performance under heavy load.  
7. **Security Hardening:**  
   * **Environment Variables:** Beyond .env files, use production-grade secret management solutions (e.g., AWS Secrets Manager, HashiCorp Vault) for sensitive credentials in deployment environments.5  
   * **HTTPS:** Ensure all API communication is secured with HTTPS.  
   * **Input Validation:** While FastAPI and Pydantic provide strong validation, ensure all external inputs are thoroughly validated and sanitized to prevent injection attacks.  
8. **Monitoring and Alerting:** Leverage the structured logging with structlog by integrating with a centralized logging system (e.g., ELK Stack, Splunk, Datadog). Set up alerts for critical errors, failed agent runs, or performance anomalies. RQ Dashboard can provide real-time visibility into job queues and worker status.14  
9. **Error Handling and Retries:** Implement more sophisticated retry mechanisms for external API calls (e.g., OpenAI, web scraping) and database operations, potentially with exponential backoff. RQ offers built-in retry logic that can be configured.13 Consider a Dead Letter Queue (DLQ) for failed jobs that require manual inspection.  
10. **Containerization:** Containerize the application (e.g., using Docker and Docker Compose) to ensure consistent environments across development, testing, and production. This simplifies dependency management and deployment.

By addressing these recommendations, the automated content agent system can evolve into a robust, scalable, and operationally mature solution capable of reliably supporting ongoing content processing needs.

592. 

