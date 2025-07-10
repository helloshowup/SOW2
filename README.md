# AI Agent Workflow Backend

An automated backend for running AI agents on a schedule. It scrapes the web using configurable queries, evaluates findings with OpenAI, and emails a concise summary. Originally a simple brand monitor, the project now also surfaces broader market intelligence so you can track industry trends alongside brand health.

## Table of Contents

* [Tech Stack](#tech-stack)
* [Prerequisites](#prerequisites)
* [Configuration](#configuration)
* [Architecture](#architecture)
* [Data Model](#data-model)
* [Workflow](#workflow)
* [Running the Scheduler](#running-the-scheduler)
* [Logging & Monitoring](#logging--monitoring)
* [Data Acquisition Strategy](#data-acquisition-strategy)
* [Email Summary Report Structure](#email-summary-report-structure)
* [Coding Practices](#coding-practices)
* [License](#license)
## Tech Stack

* **Language & Framework:** Python 3.10 + FastAPI
* **ORM & Database:** SQLAlchemy + PostgreSQL (with JSONB)
* **Cache & Queue:** Redis (via RQ or Celery)
* **Scheduler:** APScheduler (in-app) or system cron
* **Email Delivery:** SMTP (e.g., SendGrid or local Postfix)
* **Configuration:** python-dotenv + environment variables
* **Containerization:** Docker & Docker Compose
* **Logging:** structlog (with file rotation or ELK integration)

## Prerequisites

* Linux server (Ubuntu 20.04+ recommended)
* Docker & Docker Compose installed
* Access to a PostgreSQL and Redis instance
* SMTP credentials for email delivery

## Configuration

All configuration values are read from environment variables. Typical variables include `DATABASE_URL`, `LOG_LEVEL`, `REDIS_URL`, `AGENT_RUN_INTERVAL_MINUTES`, and `OPENAI_API_KEY`. The `AGENT_RUN_INTERVAL_MINUTES` setting is defined in `app/config.py` and controls how often the scheduler triggers the agent. If not set, it defaults to 600 minutes. To customize scraping queries, copy `search_config.json.example` to `search_config.json` and adjust the `brand_health_queries` and `market_intelligence_queries` lists. When present, this file is automatically loaded by the worker to override dynamically generated search terms.

When deploying to Render, be sure to provide the following environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `OPENAI_API_KEY` - your OpenAI API key
- `SERPAPI_API_KEY` - SerpAPI key for Google searches
- `APP_BASE_URL` - public base URL of the application
- `EMAIL_SENDER_ADDRESS` - address used in the "from" field of summary emails
- `EMAIL_RECIPIENTS` - comma-separated list of recipients

## Architecture

```plantuml
@startuml
hide circle

component "Scheduler" as Scheduler
component "API & Runner" as Runner
component "Redis (Cache & Queue)" as Redis
component "PostgreSQL" as DB
component "Email Service (SMTP)" as Email

Scheduler -> Runner : trigger /run-agent
Runner --> Redis : enqueue tasks
Runner --> DB    : create agent_runs entry
Runner --> Redis : cache intermediate data
Worker    --> Runner : execute tasks from Redis
Worker    --> DB    : update agent_runs status + result
Worker    --> Email : send summary email

@enduml
```

Diagram: scheduling, task queuing, persistence, and email notification.

## Data Model

```sql
CREATE TABLE agent_runs (
  id            SERIAL PRIMARY KEY,
  started_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at  TIMESTAMP,
  status        VARCHAR(20) NOT NULL,
  result        JSONB,
  error_message TEXT
);
```

* **agent\_runs**: records each run’s timestamps, status, JSON results, and any errors.

## Workflow

1. **Scheduler** triggers the `/run-agent` endpoint on the interval defined by `AGENT_RUN_INTERVAL_MINUTES` (default 600 minutes).
2. **API runner** enqueues a task in Redis and inserts a new `agent_runs` row (`pending`).
3. **Worker** fetches the task, runs the agent logic, then updates `agent_runs` with `status`, `completed_at`, and the `result` JSON.
4. On success, the worker sends an email with the top five results.

## Running the Scheduler

The scheduler runs inside the FastAPI process using **APScheduler**. In `app/main.py`, a job is scheduled that posts to `/run-agent` every `AGENT_RUN_INTERVAL_MINUTES` minutes. This value comes from `app/config.py`, which loads it from the environment and defaults to 600 minutes (10 hours).

* **Cron job** (alternative):

  ```cron
  */10 * * * * curl -X POST http://localhost:8000/run-agent
  ```

The API also exposes a `/health` endpoint that simply returns `{"status": "ok"}`.
This can be used by Docker or orchestration tools to confirm the service is running.

## Logging & Monitoring

* Structured logs via `structlog` (JSON output for ELK).
* Log rotation: `logging.handlers.RotatingFileHandler`.
* Optional: forward logs to Elasticsearch/Kibana.

## Data Acquisition Strategy
The system now primarily collects data from Google Search Engine Results Page (SERP) snippets. This shift enhances ethical data collection by reducing direct load on external websites and helps avoid "Too Many Requests" errors. Search term generation and downstream analysis remain unchanged.

## Email Summary Report Structure

The automated summary email sent after each agent run contains four sections:
1. **On brand specific links** - links that explicitly mention the brand. Each item includes "Yes, it was helpful! | No, it was not helpful." feedback options.
2. **Brand relevant but not brand specific links** - industry news or tangential mentions that may still be valuable.
3. **Prompt Engineering Metadata** - shows the exact prompts and search terms used so you can trace how the AI was instructed.
4. **Content Scraped Since last email** - logs scraping activity including the number of search calls, the timestamps of each search, and summaries of the pages visited.

Example:
```
Hi there,

Below are links that the AI thinks are on brand specific
http://brand.com (Yes, it was helpful! | No, it was not helpful.)

Below are 3 links that AI thinks are brand relevant but not brand specific
http://relevant.com

Prompt Engineering Metadata
Brand System Prompt: ...
Market System Prompt: ...
User Prompt: ...
Search Terms Generated: pizza, culture

Content Scraped Since last email
Number of search calls: 2
Searches run at: 11:01, 11:05
Summaries: summary text here
```



### **Fail Fast**

1. Validate configuration at startup  
   Check that all required environment variables (database URL, Redis connection, email credentials) are present before the application does any work. If any are missing, exit immediately with a clear error message. This prevents confusing runtime failures and makes setup issues obvious.  
2. Raise errors early  
   Instead of silently continuing when a step fails—such as when the web scraper cannot reach a site—raise an exception and log the problem. The README already recommends structured logging with `structlog`, so capturing errors early ensures they appear in the logs.  
3. Keep functions short and descriptive  
   Break logic into small, well-named functions. Each should do one thing so that even a non-coder can read the names and understand what the program is trying to do.  
4. Use clear, user-friendly logging  
   Combine fail-fast checks with simple log messages that explain what to fix (“SMTP credentials missing” or “Redis not reachable”). Avoid overly technical jargon so that it’s easy to diagnose problems without digging into the code.  
5. Document how to run and test
   Provide step-by-step instructions in the README for starting the scheduler and how to see logs when something goes wrong. This supports a non-coder who may need to troubleshoot issues.
6. Consult dev-research links when relevant
   The `dev-research` folder lists articles and repositories that demonstrate best practices. These sites have been whitelisted in the Codex environment, so reference them whenever they directly support project objectives.


## License

MIT © Your Organization
