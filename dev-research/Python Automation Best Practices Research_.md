

# **Comprehensive AI Agent Workflow: Best Practices for Web Scraping, AI Evaluation, Email Automation, and Data Management**

## **Executive Summary**

This report outlines a robust and efficient AI agent workflow, integrating automated daily web scraping, AI-powered content evaluation and dynamic categorization, Python-based email workflows for summaries and structured feedback, and efficient local SQLite database storage. The architecture emphasizes Python, BeautifulSoup, and the OpenAI API, avoiding local LLM setups to streamline deployment and maintenance. Key strategies for error handling, dynamic content management, ethical scraping, and flexible prompt configuration are detailed, providing a comprehensive guide for technical leads and senior software engineers aiming to implement sophisticated, data-driven automation solutions.

## **1\. Automated Daily Web Scraping and Content Acquisition**

Automated daily web scraping forms the foundational layer of an AI agent workflow, providing the raw data necessary for subsequent evaluation and analysis. Building a resilient and efficient scraping system requires careful consideration of common challenges and adherence to established best practices.

### **1.1. Robust Scraping with Python and BeautifulSoup**

The core of web scraping in Python typically relies on the requests library for handling HTTP communications and BeautifulSoup for parsing the HTML or XML content retrieved from web pages.1 These libraries are favored for their simplicity and effectiveness in extracting static data, making them excellent choices for initial scraping endeavors.

#### **Error Handling and Retry Logic**

Web scraping operations are inherently susceptible to various disruptions, necessitating robust error handling and intelligent retry mechanisms. Common issues include connection timeouts, "404 Not Found" errors, server-side blocking, and inconsistencies arising from changes in website structure.1 The

BeautifulSoup library itself can introduce AttributeError when attempting to access non-existent tags or encounter parsing errors with malformed XML.4

To mitigate these challenges, implementing try-except blocks is a fundamental practice. For instance, requests.exceptions.HTTPError should be caught to manage server-side issues, often triggered proactively by response.raise\_for\_status().4 Network-related failures, such as temporary disconnections or unreachable domains, are best handled by catching

requests.exceptions.ConnectionError.4 When interacting with

BeautifulSoup, it is crucial to verify that a find() or find\_all() operation has returned a valid object (i.e., not None) before attempting to access its attributes, thereby preventing AttributeError.4

Beyond simple error catching, a sophisticated daily scraping agent must incorporate retry logic, particularly with an exponential backoff strategy.1 This approach involves progressively increasing the delay between retry attempts for transient issues, such as temporary server overloads or brief network glitches. This not only avoids overwhelming the target server but also allows it sufficient time to recover, thereby improving the success rate of data retrieval. It is equally important to set a definitive limit on the number of retries to prevent the scraper from entering an endless loop if a persistent issue arises.1 Comprehensive logging of all events—including successful requests, errors encountered, and retry attempts—is indispensable for debugging, monitoring performance, and gaining actionable insights into the scraper's operation.1

The continuous, unattended nature of daily automation underscores the critical role of robust error handling and retry mechanisms. Without these safeguards, even minor, transient issues could halt the entire scraping process, demanding manual intervention and undermining the very purpose of automation. The ability for the system to gracefully recover from common failures is not merely a beneficial feature but a prerequisite for achieving reliable, low-maintenance daily operations. Consequently, the investment in meticulously designed error handling and retry logic directly contributes to the operational efficiency and overall stability of the AI agent workflow.

#### **Handling Dynamic Content and Pagination**

While requests and BeautifulSoup are highly effective for static HTML content, modern web applications frequently employ JavaScript to load content dynamically via AJAX calls or operate as Single Page Applications (SPAs).2 This dynamic rendering poses a significant challenge for traditional scrapers, as the desired data may not be present in the initial HTML response. Similarly, many pagination schemes rely on JavaScript interactions rather than simple URL changes.

For such dynamic content, the use of a headless browser automation tool like Selenium is recommended.2 Selenium can simulate a full browser environment, capable of executing JavaScript, interacting with web elements (e.g., clicking buttons, filling forms), and then providing the fully rendered page source for

BeautifulSoup to parse.2 Selenium becomes indispensable when data appears only after a delay, the website is heavily dependent on JavaScript for content display, or when JavaScript-based checks are employed to block conventional HTTP clients.2

Setting up Selenium typically involves installing the selenium Python package and acquiring a compatible WebDriver (e.g., ChromeDriver).2 The process involves initializing a headless Chrome browser instance, navigating to the target URL, allowing time for dynamic content to load, and then extracting the

driver.page\_source for parsing with BeautifulSoup.2 Advanced capabilities of Selenium's API extend to executing arbitrary JavaScript, submitting forms, and locating elements using sophisticated CSS selectors or XPath expressions.2

However, it is essential to acknowledge the resource implications of using Selenium. Each headless Chrome instance can consume substantial memory (e.g., 300-400MB per instance) and requires a dedicated CPU core.2 This resource intensity significantly limits the degree of concurrency achievable and necessitates adequate underlying hardware. This highlights a crucial trade-off between functionality and performance in scraping tool selection. While Selenium provides a solution for complex, dynamic websites, its overhead means that it should not be the default choice. An efficient scraping strategy prioritizes lightweight tools like

requests and BeautifulSoup for static content, reserving Selenium only for scenarios where dynamic content or JavaScript interaction is strictly unavoidable. This tiered approach optimizes resource utilization and contributes to the overall system performance.

#### **Ethical Considerations and robots.txt**

Beyond technical capabilities, ethical and legal considerations are paramount for any sustainable web scraping operation. A fundamental step before initiating any scraping activity is to inspect the target website's robots.txt file.2 This file serves as a set of guidelines, indicating which parts of the website are permissible to crawl and which are explicitly off-limits. Adhering to these directives is not only an ethical obligation but also a crucial legal best practice, helping to prevent potential legal disputes or IP bans.

Furthermore, a thorough understanding and compliance with a website's terms of service are essential.2 These terms often contain clauses regarding automated access and data usage. Implementing polite delays between requests and rotating user-agents are also critical practices. These measures help to avoid overwhelming the target server, mimic human browsing patterns, and reduce the likelihood of IP blocking or other server-side detection mechanisms.1 A sustainable daily web scraping solution inherently integrates these ethical considerations—such as parsing

robots.txt, implementing polite delays, and managing user-agent strings—as core design principles, rather than mere afterthoughts. This proactive approach ensures the long-term viability and legality of the data acquisition process.

### **1.2. Leveraging OpenAI API for Content Acquisition (where applicable)**

While the primary focus of content acquisition often lies in web scraping, the OpenAI API can serve as a powerful complementary tool, particularly for refining and extracting insights from already acquired text. It is not designed for fetching raw HTML like traditional scrapers but excels at processing textual content. For instance, if the scraped content is extensive, OpenAI models can be leveraged to generate concise summaries, extracting key information efficiently.6

Projects like jarif87/daily-email-report demonstrate this principle by using AI (specifically Grok AI in that case, but the concept applies to OpenAI) for automated email summarization, transforming raw email content into digestible reports.7 This illustrates a pipeline where raw data, once acquired through scraping, is immediately fed into an AI model for further processing, such as summarization or entity extraction. This transformation converts raw data into structured, actionable intelligence, bypassing the need for complex local Natural Language Processing (NLP) setups. The AI agent workflow benefits significantly from viewing web scraping and AI processing as integrated, sequential stages in a data pipeline, where the output of the scraper directly informs and enables the AI's analytical capabilities.

## **2\. AI-Powered Content Evaluation and Dynamic Categorization**

The integration of AI models, particularly the OpenAI API, offers sophisticated capabilities for evaluating the quality of scraped content and dynamically categorizing it. This moves beyond simple data extraction to automated intelligence generation.

### **2.1. Content Evaluation Criteria and Prompt Engineering with OpenAI API**

Evaluating content quality, especially for open-ended generation tasks like summarization, often presents challenges for traditional automated metrics such as ROUGE or BERTScore, which may not always align well with human judgment.8 In contrast, large language models (LLMs) like GPT-4 can be employed effectively as an "LLM-as-a-judge" to assess content against human-defined criteria, yielding more nuanced and human-aligned scores.8

Effective content evaluation typically hinges on a set of well-defined criteria. These commonly include:

* **Relevance:** Ensuring the summary or extracted content includes only important information and avoids redundancies.  
* **Coherence:** Assessing the logical flow and organization of the content.  
* **Consistency:** Verifying factual alignment between the generated content and its source document.  
* **Fluency:** Evaluating the grammatical correctness and readability of the text.8

The efficacy of AI-driven evaluation is heavily dependent on the precision and structure of the prompts provided to the model. This discipline, known as prompt engineering, essentially dictates the AI's "logic" and desired output.

Key principles for designing effective prompts for scoring and quality assessment include:

* **Clarity and Specificity:** Prompts must explicitly state the objective, target audience, desired length, tone, and any constraints, leaving no room for ambiguity in the AI's interpretation.9  
* **Structured Instructions:** It is a best practice to place instructions at the beginning of the prompt and use clear separators (e.g., \#\#\# or """) to delineate instructions from the actual content or context to be evaluated.9  
* **Chain-of-Thought (CoT) Prompting:** Guiding the model through a step-by-step reasoning process to arrive at a score significantly improves the consistency and transparency of the AI's judgment. For example, for relevancy, the model can be instructed to first read both the source and the summary, then identify the main points of the original article, subsequently assess how well the summary covers these points while identifying irrelevant information, and finally assign a numerical score.8  
* **Explicit Output Format:** Defining the desired output format explicitly, preferably in JSON, is crucial for programmatic parsing and integration into downstream systems. For scoring tasks, the prompt should guide the model to output a specific numeric score (e.g., 1-5) for each criterion.8  
* **Examples (Few-Shot Prompting):** Providing concrete examples of both desired (positive) and undesired (negative) outputs within the prompt helps to "train" the model on the expected structure, tone, and style. This is particularly effective for aligning AI output with specific quality standards and reducing variability.9  
* **System Messages:** Utilizing system messages allows for setting the overall tone, guidelines, and persona for the AI assistant, which then persists across multiple interactions within a session.12

The quality and consistency of AI-driven evaluation are primarily determined by the precision and structure of the prompts, rather than solely by the underlying model's capabilities (assuming a capable model like GPT-4). This paradigm shift elevates prompt engineering to a critical development activity, akin to writing code, as it directly dictates the AI's operational logic and output behavior. Consequently, for AI agent workflows, prompt engineering should be approached with the same rigor as traditional software development, involving iterative refinement, version control, and comprehensive documentation. This foundational importance underscores the necessity of external prompt configuration, as discussed in Section 5\.

#### **Table: OpenAI API Prompt Design for Evaluation**

| Metric/Category | Prompt Structure Example (User Message) | System Message Example (Guiding AI) | Desired JSON Output | Value and Application |
| :---- | :---- | :---- | :---- | :---- |
| **Relevance** | Source: """\[document\]""" Summary: """\[summary\]""" Evaluate the relevance of the summary to the source on a scale of 1-5. Explain your reasoning step-by-step. | You are an expert content evaluator. Your task is to rate summaries for relevance. Relevance: Evaluates if the summary includes only important information and excludes redundancies. Follow these steps: 1\. Read source and summary. 2\. Identify main points of article. 3\. Assess how well summary covers main points and irrelevant info. 4\. Assign score 1-5. Output JSON: {"score": int, "explanation": "string"} 8 | {"score": 4, "explanation": "Summary covers most key points but includes a minor redundancy."} | Provides a structured, repeatable method for evaluating content quality against specific criteria. The step-by-step reasoning (Chain-of-Thought) makes the AI's judgment transparent and debuggable, which is crucial for refining prompts and understanding AI behavior. This shifts evaluation from subjective human review or limited traditional metrics to scalable, AI-assisted quality assurance. |
| **Coherence** | Summary: """\[summary\]""" Evaluate the coherence of this summary on a scale of 1-5. Explain your reasoning. | You are a language expert. Your task is to rate summaries for coherence. Coherence: Assesses the logical flow and organization of the summary. It should build from sentence to a coherent body of information. Follow these steps: 1\. Read the summary. 2\. Check if it presents points in a clear and logical order. 3\. Assign score 1-5. Output JSON: {"score": int, "explanation": "string"} 8 | {"score": 5, "explanation": "The summary flows logically and ideas are well-connected."} | Enables automated quality checks on the readability and structural integrity of generated or extracted content. This is particularly useful for summarization tasks where output quality is critical for human consumption and subsequent processing. |
| **Categorization** | Text: """\[content\_text\]""" Categorize this text into one of the following:. Respond in JSON. | You are a content categorizer. Your task is to assign the most appropriate category to the provided text. The categories are: \[list of categories\]. The value for 'category' should be one of the provided categories. Output JSON: {"category": "string", "explanation": "string"} 6 | {"category": "Category B", "explanation": "Text primarily discusses topics related to Category B."} | Facilitates dynamic and flexible content organization without requiring pre-trained models for each new category. This supports agile content management for daily scraping, allowing for rapid adaptation to new topics or classification needs. The JSON output ensures easy programmatic integration into structured data systems. |

### **2.2. Dynamic Categorization using OpenAI API**

The OpenAI API provides robust capabilities for dynamic content categorization, allowing the AI agent to classify text into predefined or inferred categories. This is a significant advancement over traditional methods that often require extensive training data and model retraining for each new category.

The API offers a text classification endpoint that can assign labels to a piece of text based on its content.6 This functionality supports two powerful classification paradigms:

* **Zero-Shot Classification:** In this approach, the model classifies text without requiring any explicit examples within the training data. It leverages its vast pre-training and inherent understanding of language and concepts, guided solely by a well-structured prompt.6 This method is highly efficient for rapidly adapting to new categories or evolving content landscapes without the overhead of data labeling and model fine-tuning.  
* **Few-Shot Classification:** When more specific guidance is needed, providing a small number of examples directly within the prompt significantly enhances the model's ability to classify text according to particular patterns, desired tone, or specific output styles. This technique, also known as in-context learning, is especially valuable for specialized or technical domains, or when strict output formatting is required.6

The effectiveness of categorization, much like evaluation, relies heavily on precise prompt structure. Prompts should clearly define the AI assistant's role, specify the desired output format (e.g., JSON containing category labels), and impose any necessary constraints on the output values.12 For instance, a system message might instruct the model to act as a "content categorizer" and output a JSON object with a

category key whose value must be one of a predefined list of categories.

Traditional content categorization often involves time-consuming processes of training custom machine learning models, which can be rigid and slow to adapt. The ability of OpenAI models to perform zero-shot and few-shot classification means that categories can be dynamically defined or adjusted directly within the prompt itself, eliminating the need for model retraining. This inherent flexibility provides immense agility for daily web scraping workflows, where content topics or classification criteria may frequently evolve. This dynamic categorization capability allows the AI agent to respond swiftly to changing information landscapes or evolving business requirements, making the workflow highly adaptable and resilient compared to static, rule-based, or pre-trained classification systems.

## **3\. Python-Based Email Workflows for Summaries and Feedback**

Automated email workflows are crucial for disseminating AI-generated summaries and for collecting structured feedback, closing the loop in the AI agent's operational cycle. Python's standard library provides robust tools for these tasks.

### **3.1. Sending Automated Summaries (HTML Content and Attachments)**

Python's built-in smtplib and email.mime modules form the bedrock for sending automated emails, including those with rich HTML content and various attachments.19

To compose emails with rich formatting, the email.mime.text.MIMEText class is utilized by specifying subtype='html'. This allows for the inclusion of custom HTML structures, enabling visually appealing layouts, embedded images (managed using add\_related and make\_msgid for Content-ID referencing within the HTML), and clickable hyperlinks.19 For attaching files, the

email.mime.multipart.MIMEMultipart container is employed to combine different parts of the email (e.g., text, HTML, attachments). The email.mime.application.MIMEApplication class facilitates the attachment of various file types, such as PDF reports or CSV data, ensuring that comprehensive information can be delivered.19

Sending these emails requires configuring an SMTP (Simple Mail Transfer Protocol) server, which involves specifying the server address (e.g., smtp.gmail.com) and port (e.g., 587 for TLS, 465 for SSL).20 Authentication credentials must be provided, and a secure connection is established using methods like

server.starttls() or smtplib.SMTP\_SSL to encrypt the communication.

The value of an AI agent is significantly amplified when its generated insights are communicated effectively. Relying solely on plain-text emails can limit the impact and readability of complex reports. By leveraging HTML emails with embedded summaries, dynamic content, and attached files, the agent can deliver highly readable, visually engaging, and comprehensive reports. This approach not only enhances user engagement but also increases the perceived value and utility of the automated workflow. Therefore, designing email outputs as rich, interactive reports, rather than just raw text, is a best practice for maximizing the impact and usability of the AI agent's daily operations.

### **3.2. Receiving Structured Feedback via Clickable Forms or Embedded Links**

To establish a mechanism for receiving structured feedback, automated emails can incorporate clickable forms or embedded links that direct users to a dedicated web endpoint. This approach simplifies the feedback process and enhances data collection efficiency.

#### **Generating Unique Feedback Links/Tokens**

The use of unique links is pivotal for tracking individual feedback submissions back to a specific report or user without requiring explicit login credentials, thereby streamlining the user experience and improving data integrity. Python's uuid module is an excellent tool for generating universally unique identifiers (UUIDs).24 Specifically,

uuid.uuid4() generates a random UUID, which is suitable for privacy-sensitive applications as it does not rely on MAC addresses or timestamps.24 These generated UUIDs can be seamlessly embedded as query parameters within the feedback URL, allowing for a distinct identifier for each feedback request.27

For scenarios demanding heightened security or to enforce single-use links, unique tokens can be combined with time-limited serialization. Libraries such as itsdangerous.URLSafeTimedSerializer in a Flask context can generate tokens that expire after a set duration, as demonstrated in examples for email confirmation tokens.28 This adds a crucial layer of security, preventing the misuse of feedback links and ensuring the authenticity of submissions. The design of the feedback mechanism must strike a balance between a low-friction user experience and robust data integrity. While unique, pre-populated links significantly reduce user effort and encourage participation, they must be secure and traceable. Implementing unique, and potentially time-limited, tokens ensures that feedback is accurately attributed and protects against malicious or unintended submissions, thereby preserving the integrity of the collected data.

#### **Simple Flask Backend for Receiving Feedback**

A lightweight web framework like Flask in Python is ideally suited for creating simple web endpoints to receive HTTP requests, making it an excellent choice for a dedicated feedback collection backend.29

Flask provides straightforward methods for accessing incoming data. For GET requests, request.args.get() is used to extract query parameters, such as the unique feedback token embedded in the URL.29 For POST requests,

request.form is employed to retrieve data submitted through HTML forms.29 Upon receiving feedback, the Flask application can then connect to the local SQLite database to store the collected data.33 A critical security consideration during data insertion is the exclusive use of parameterized queries. This practice prevents SQL injection vulnerabilities by separating SQL code from user-supplied data, ensuring the integrity and security of the database.33

A typical Flask application structure for this purpose would involve defining a specific route (e.g., /feedback/\<token\>) that listens for incoming requests. This route's handler function would extract the unique token and any associated feedback data, subsequently storing this structured information in the SQLite database.33 For a focused task like feedback collection, a full-fledged web application framework might introduce unnecessary complexity and overhead. Flask, as a microframework, offers precisely the necessary functionality to set up a simple yet effective API endpoint for structured data ingestion. This minimalist approach reduces development complexity, minimizes system overhead, and narrows the potential attack surface, making it an efficient solution for a single-purpose data collection task. Therefore, choosing a lightweight framework like Flask for the feedback backend aligns perfectly with the goals of efficiency and maintainability, facilitating rapid deployment and concentrated development on the core task of data ingestion.

## **4\. Efficient Feedback Data Storage with Local SQLite**

The efficient storage and retrieval of feedback data are crucial for analyzing AI agent performance and driving continuous improvement. A local SQLite database offers a practical and performant solution for this purpose.

### **4.1. SQLite Database Schema Design for Structured Feedback**

SQLite stands out as an embedded, serverless, and self-contained SQL database engine, making it exceptionally portable and requiring no complex configuration.35 These characteristics render it an ideal choice for local data storage within Python applications, particularly for managing structured feedback.

A meticulously designed database schema is paramount for ensuring data integrity and facilitating efficient data retrieval.37 For feedback data, a comprehensive schema might include the following key columns:

* id (INTEGER PRIMARY KEY AUTOINCREMENT): A unique identifier for each feedback entry, automatically incrementing for new records.38  
* timestamp (TEXT or INTEGER): Records the exact time the feedback was submitted. Using TEXT for ISO 8601 formatted strings or INTEGER for Unix timestamps offers flexibility.  
* feedback\_token (TEXT UNIQUE): The unique token embedded in the email link, serving as a traceable identifier for the specific feedback request.40 This column should enforce uniqueness to prevent duplicate entries for the same token.  
* source\_url (TEXT): The URL of the content that was evaluated, providing context for the feedback.  
* user\_id (TEXT or INTEGER): An identifier for the user who provided the feedback, if available and appropriate for the system's privacy model.  
* category (TEXT): The AI-assigned category of the content, reflecting the dynamic categorization output.  
* score (INTEGER or REAL): The AI-assigned evaluation score (e.g., on a scale of 1-5), indicating the AI's assessment of content quality.  
* user\_rating (INTEGER or REAL): The user's explicit rating (e.g., 1-5), capturing direct human judgment.  
* user\_comment (TEXT): The user's free-form textual feedback, allowing for qualitative input.  
* ai\_explanation (TEXT): The AI's generated explanation for its categorization or score, providing transparency.  
* processed\_status (TEXT): A workflow status indicator (e.g., 'new', 'reviewed', 'actioned'), useful for managing feedback processing.

When defining the schema, selecting appropriate data types (TEXT, INTEGER, REAL, BLOB) for each column is crucial for data integrity and optimal performance.37 Furthermore, implementing constraints such as

NOT NULL, UNIQUE, and FOREIGN KEY is essential to enforce data consistency and prevent invalid entries. For instance, the feedback\_token column should be constrained as UNIQUE to ensure each feedback submission is distinct.37

Database normalization is a key practice to reduce data redundancy and enhance integrity, especially if the feedback data naturally relates to other entities within the system (e.g., users or scraped\_content records). Foreign keys are instrumental in establishing and maintaining these relationships between tables.37 Additionally, creating indexes on columns that are frequently used in

WHERE clauses or JOIN conditions (e.g., feedback\_token, timestamp, user\_id) significantly accelerates query performance.37

The feedback data collected is not merely raw input; it represents a vital source for refining and improving the AI agent's performance. A thoughtfully structured schema directly influences the ease with which this data can be queried, analyzed, and transformed into actionable intelligence. For example, a well-designed schema facilitates identifying patterns in low-scoring content, correlating user feedback with AI evaluations, or tracking the impact of prompt changes. Without a robust and flexible schema, extracting meaningful value from the feedback becomes a substantial challenge, impeding the iterative improvement cycle of the AI agent. Therefore, prioritizing a well-structured SQLite schema for feedback data is a strategic investment in the continuous enhancement of the AI agent, enabling data-driven refinement of its scraping, evaluation, and categorization logic.

#### **Table: SQLite Feedback Schema Example**

| Column Name | Data Type | Constraints | Description |
| :---- | :---- | :---- | :---- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier for each feedback record. |
| timestamp | TEXT | NOT NULL | ISO 8601 timestamp of feedback submission. |
| feedback\_token | TEXT | NOT NULL, UNIQUE | Unique token from email link, for traceability. |
| source\_url | TEXT | NOT NULL | URL of the scraped content being evaluated. |
| user\_id | TEXT | NULLABLE | Identifier for the user providing feedback (if applicable). |
| ai\_category | TEXT | NULLABLE | AI-assigned category of the content. |
| ai\_score | INTEGER | NULLABLE | AI-assigned evaluation score (e.g., 1-5). |
| user\_rating | INTEGER | NULLABLE | User's explicit rating (e.g., 1-5). |
| user\_comment | TEXT | NULLABLE | User's free-form text comment. |
| ai\_explanation | TEXT | NULLABLE | AI's explanation for its categorization/score. |
| processed\_status | TEXT | DEFAULT 'new' | Workflow status: 'new', 'reviewed', 'actioned'. |

**Value and Application:** This schema provides a comprehensive structure for capturing all relevant aspects of feedback, from automated AI evaluations to direct user input. The feedback\_token ensures traceability back to the original email and content. The inclusion of both AI-generated and user-generated data points allows for direct comparison and analysis, which is critical for identifying discrepancies and areas for AI model improvement. The processed\_status column supports a workflow for reviewing and acting upon feedback. This structured approach transforms raw feedback into an analyzable dataset, directly supporting the iterative refinement of the AI agent's performance.

### **4.2. CRUD Operations for Feedback Data**

Performing Create, Read, Update, and Delete (CRUD) operations on the SQLite database is fundamental for managing feedback data. Python's built-in sqlite3 module provides a straightforward interface for these interactions.

**Connecting to the Database:** The first step for any database operation is establishing a connection. The sqlite3.connect() function creates a connection to a specified database file (e.g., feedback.db), implicitly creating it if it doesn't exist.35 It is a best practice to manage connections using a context manager (

with sqlite3.connect(...)) to ensure proper closing, even if errors occur.39

**Creating Tables:** Once a connection is established, tables are created using the CREATE TABLE SQL statement executed via a cursor object's execute() method.35 This is typically done once during the application's initialization or setup.

Python

import sqlite3

DATABASE\_PATH \= 'feedback.db'

def init\_db():  
    with sqlite3.connect(DATABASE\_PATH) as conn:  
        cursor \= conn.cursor()  
        cursor.execute("""  
            CREATE TABLE IF NOT EXISTS feedback (  
                id INTEGER PRIMARY KEY AUTOINCREMENT,  
                timestamp TEXT NOT NULL,  
                feedback\_token TEXT NOT NULL UNIQUE,  
                source\_url TEXT NOT NULL,  
                user\_id TEXT,  
                ai\_category TEXT,  
                ai\_score INTEGER,  
                user\_rating INTEGER,  
                user\_comment TEXT,  
                ai\_explanation TEXT,  
                processed\_status TEXT DEFAULT 'new'  
            );  
        """)  
        conn.commit()  
        print("Feedback table ensured to exist.")

\# Call this function once to set up the database  
\# init\_db()

35

**Inserting Data (Create):** New feedback records are inserted using the INSERT INTO SQL statement. Crucially, parameterized queries (using ? placeholders) must always be employed to bind Python values to SQL statements.40 This is a critical security measure to prevent SQL injection attacks. After executing an

INSERT statement, conn.commit() must be called to persist the changes to the database.42

Python

def insert\_feedback(feedback\_data):  
    with sqlite3.connect(DATABASE\_PATH) as conn:  
        cursor \= conn.cursor()  
        sql \= """  
            INSERT INTO feedback (  
                timestamp, feedback\_token, source\_url, user\_id,  
                ai\_category, ai\_score, user\_rating, user\_comment,  
                ai\_explanation, processed\_status  
            ) VALUES (?,?,?,?,?,?,?,?,?,?)  
        """  
        values \= (  
            feedback\_data.get('timestamp'),  
            feedback\_data.get('feedback\_token'),  
            feedback\_data.get('source\_url'),  
            feedback\_data.get('user\_id'),  
            feedback\_data.get('ai\_category'),  
            feedback\_data.get('ai\_score'),  
            feedback\_data.get('user\_rating'),  
            feedback\_data.get('user\_comment'),  
            feedback\_data.get('ai\_explanation'),  
            feedback\_data.get('processed\_status', 'new')  
        )  
        cursor.execute(sql, values)  
        conn.commit()  
        return cursor.lastrowid \# Returns the ID of the last inserted row

42

**Retrieving Data (Read):** Data is retrieved using SELECT statements. Similar to insertions, parameters should be used for WHERE clauses to prevent SQL injection.40 The

cursor.fetchall() method retrieves all matching rows, while cursor.fetchone() retrieves a single row.35 It can be beneficial to configure

conn.row\_factory \= sqlite3.Row to retrieve rows as dictionary-like objects, which are more convenient to work with than tuples.33

Python

def get\_feedback\_by\_token(token):  
    with sqlite3.connect(DATABASE\_PATH) as conn:  
        conn.row\_factory \= sqlite3.Row \# Access columns by name  
        cursor \= conn.cursor()  
        cursor.execute("SELECT \* FROM feedback WHERE feedback\_token \=?", (token,))  
        return cursor.fetchone()

def get\_all\_feedback():  
    with sqlite3.connect(DATABASE\_PATH) as conn:  
        conn.row\_factory \= sqlite3.Row  
        cursor \= conn.cursor()  
        cursor.execute("SELECT \* FROM feedback ORDER BY timestamp DESC")  
        return cursor.fetchall()

33

**Updating Data (Update):** Records are modified using the UPDATE statement, again with parameterized queries.35

Python

def update\_feedback\_status(feedback\_id, new\_status):  
    with sqlite3.connect(DATABASE\_PATH) as conn:  
        cursor \= conn.cursor()  
        cursor.execute("UPDATE feedback SET processed\_status \=? WHERE id \=?", (new\_status, feedback\_id))  
        conn.commit()

35

**Deleting Data (Delete):** Records are removed using the DELETE statement.

Python

def delete\_feedback(feedback\_id):  
    with sqlite3.connect(DATABASE\_PATH) as conn:  
        cursor \= conn.cursor()  
        cursor.execute("DELETE FROM feedback WHERE id \=?", (feedback\_id,))  
        conn.commit()

### **4.3. Best Practices for SQLite Performance and Data Integrity**

While SQLite is known for its simplicity, optimizing its performance and ensuring data integrity are crucial for a robust feedback system, especially as data volume grows.

**Performance Optimization:**

* **Write-Ahead Logging (WAL):** Enabling WAL mode can significantly improve write performance, especially under concurrent read/write operations, by appending mutations to a log before compacting them into the main database.41  
* **Batching Insertions:** For multiple insertions, wrapping them within a single transaction using conn.commit() after a series of execute() calls (or executemany()) is far more efficient than committing each insertion individually.41 This reduces disk I/O overhead.  
* **Indexing:** As previously mentioned, creating indexes on frequently queried columns (e.g., feedback\_token, timestamp, user\_id) accelerates data retrieval by allowing the database to quickly locate relevant rows without scanning the entire table.37 However, excessive indexing can negatively impact write performance, so judicious application is advised.  
* **Efficient Queries:** Writing SQL queries that retrieve only the necessary rows and columns (SELECT specific\_columns instead of SELECT \*) and pushing computational work to the SQLite engine (e.g., using COUNT(), SUM(), DISTINCT, GROUP\_CONCAT) instead of performing operations in Python code can drastically improve performance.41  
* **Parameterization:** Always use parameterized queries for variables to prevent SQL injection and allow SQLite to optimize query plans.40

**Data Integrity:**

* **Constraints:** Leveraging SQL constraints like PRIMARY KEY, NOT NULL, UNIQUE, CHECK, and FOREIGN KEY directly within the schema definition (as shown in Section 4.1) ensures data consistency and validity at the database level.37 This is generally more efficient and reliable than enforcing validation solely in application code.41  
* **Normalization:** Adhering to database normalization principles (e.g., 1NF, 2NF, 3NF) reduces data redundancy and improves data integrity by ensuring each piece of data is stored in only one place, thereby preventing update anomalies and inconsistencies.37  
* **Error Logging:** While the SQLite database handles data storage, logging database interaction errors (e.g., connection failures, query execution errors) in the application's log files (as discussed in Section 1.1) is crucial for debugging and maintaining the system's health.47

SQLite's nature as a local, embedded database means that its performance is directly tied to the host system's disk I/O and CPU. Therefore, applying these best practices is not merely about marginal gains; it is about ensuring that the feedback system remains responsive and reliable even as the volume of collected data increases. A well-optimized SQLite database ensures that the valuable feedback data can be efficiently accessed and analyzed, directly contributing to the continuous improvement and operational effectiveness of the AI agent.

## **5\. External Prompt Configuration Management**

In AI agent workflows, where prompts are central to defining the behavior and output of large language models, externalizing prompt configurations is a critical best practice. This approach enhances maintainability, facilitates version control, and enables dynamic updates without requiring code redeployment.

### **5.1. Storing Prompts in JSON Files**

JSON (JavaScript Object Notation) is a lightweight, human-readable data interchange format widely supported in Python.48 Its structured nature makes it an excellent choice for storing complex AI prompts, especially those with multiple components (e.g., system messages, user message templates, few-shot examples, desired output formats).

**Advantages of JSON for Prompts:**

* **Structured Data:** JSON allows for hierarchical organization of prompt elements, making it easy to define complex prompt structures, including nested objects and arrays for different roles (system, user, assistant) or multiple examples.48  
* **Readability:** Despite its structured nature, JSON remains relatively human-readable, which is beneficial for prompt engineers and developers to understand and modify.49  
* **Easy Parsing in Python:** Python's built-in json module provides json.load() for reading JSON data from files and json.loads() for parsing JSON strings into Python dictionaries or lists.48 This native support simplifies integration.  
* **Dynamic Loading:** Prompts can be loaded at runtime, allowing for A/B testing of different prompt versions or rapid deployment of new prompt strategies without altering the core application code.49

**Example of JSON Prompt Structure (prompts.json):**

JSON

{  
  "evaluation\_relevance": {  
    "system\_message": "You are an expert content evaluator. Your task is to rate summaries for relevance. Relevance: Evaluates if the summary includes only important information and excludes redundancies. Follow these steps: 1\. Read source and summary. 2\. Identify main points of article. 3\. Assess how well summary covers main points and irrelevant info. 4\. Assign score 1-5.",  
    "user\_template": "Source: \\"\\"\\"{}\\"\\"\\" Summary: \\"\\"\\"{}\\"\\"\\" Evaluate the relevance of the summary to the source on a scale of 1-5. Explain your reasoning step-by-step.",  
    "output\_format\_instruction": "Output JSON: {\\"score\\": int, \\"explanation\\": \\"string\\"}"  
  },  
  "categorization\_general": {  
    "system\_message": "You are a content categorizer. Your task is to assign the most appropriate category to the provided text. The categories are:. The value for 'category' should be one of the provided categories.",  
    "user\_template": "Text: \\"\\"\\"{}\\"\\"\\" Categorize this text into one of the following:. Respond in JSON.",  
    "output\_format\_instruction": "Output JSON: {\\"category\\": \\"string\\", \\"explanation\\": \\"string\\"}",  
    "examples": \[  
      {"input": "...", "output": "..."}  
    \]  
  }  
}

48

**Python Code to Load JSON Prompt:**

Python

import json

def load\_prompts\_from\_json(filepath='prompts.json'):  
    try:  
        with open(filepath, 'r', encoding='utf-8') as f:  
            prompts \= json.load(f)  
        return prompts  
    except FileNotFoundError:  
        print(f"Error: Prompt file not found at {filepath}")  
        return {}  
    except json.JSONDecodeError:  
        print(f"Error: Invalid JSON format in {filepath}")  
        return {}

\# Example usage:  
\# all\_prompts \= load\_prompts\_from\_json()  
\# relevance\_prompt\_config \= all\_prompts.get("evaluation\_relevance")  
\# if relevance\_prompt\_config:  
\#     system\_msg \= relevance\_prompt\_config\["system\_message"\]  
\#     user\_template \= relevance\_prompt\_config\["user\_template"\]  
\#     \#... use these in OpenAI API call

48

### **5.2. Storing Prompts in Plaintext (INI-style) Files**

For simpler prompt configurations, particularly those involving key-value pairs or basic sections, plaintext files formatted like INI files can be a viable option. Python's configparser module is specifically designed for this purpose.54

**Advantages of Plaintext (INI) for Prompts:**

* **Simplicity:** INI files are very straightforward, consisting of sections and key-value pairs, making them easy to read and manually edit.54  
* **Lightweight:** They have minimal overhead and are suitable for basic configuration needs.  
* **Built-in Python Support:** The configparser module is part of Python's standard library, requiring no external dependencies.54

**Limitations:**

* **Limited Structure:** INI files are less suitable for highly complex or deeply nested prompt structures compared to JSON. They primarily support two levels: sections and key-value pairs within sections.  
* **Type Handling:** Values are read as strings and require explicit type conversion (e.g., to integers or booleans) in Python code.

**Example of INI Prompt Structure (prompts.ini):**

Ini, TOML

\[Evaluation\]  
relevance\_system\_message \= You are an expert content evaluator. Your task is to rate summaries for relevance.  
relevance\_user\_template \= Source: """{}""" Summary: """{}""" Evaluate the relevance of the summary to the source on a scale of 1\-5.  
relevance\_output\_format \= Output JSON: {"score": int, "explanation": "string"}

\[Categorization\]  
general\_system\_message \= You are a content categorizer. Your task is to assign the most appropriate category.  
general\_user\_template \= Text: """{}""" Categorize this text into one of the following:.  
general\_output\_format \= Output JSON: {"category": "string", "explanation": "string"}

54

**Python Code to Load INI Prompt:**

Python

import configparser

def load\_prompts\_from\_ini(filepath='prompts.ini'):  
    config \= configparser.ConfigParser()  
    try:  
        config.read(filepath)  
        prompts \= {}  
        for section in config.sections():  
            prompts\[section\] \= {key: config.get(section, key) for key in config.options(section)}  
        return prompts  
    except configparser.Error as e:  
        print(f"Error parsing INI file {filepath}: {e}")  
        return {}  
    except FileNotFoundError:  
        print(f"Error: Prompt file not found at {filepath}")  
        return {}

\# Example usage:  
\# all\_prompts\_ini \= load\_prompts\_from\_ini()  
\# eval\_section \= all\_prompts\_ini.get("Evaluation")  
\# if eval\_section:  
\#     system\_msg \= eval\_section\["relevance\_system\_message"\]  
\#     \#... use these in OpenAI API call

54

### **5.3. Dynamic Loading and Management of AI Prompts**

Externalizing prompts, whether in JSON or INI format, is a foundational element for agile AI agent development. This approach allows for the dynamic loading and management of AI prompts, which is crucial for iterative improvement and operational flexibility.

**Benefits of External Prompt Management:**

* **Decoupling Logic from Code:** Prompts, which dictate AI behavior, are separated from the core application logic. This means that changes to prompt wording, instructions, or examples do not require modifications and redeployments of the Python codebase.52  
* **Version Control:** External prompt files can be managed under version control systems (e.g., Git) just like source code.52 This enables tracking changes, reverting to previous versions, and collaborating on prompt development. Some tools even offer specific prompt management features with versioning.52  
* **A/B Testing and Experimentation:** Different prompt versions can be loaded dynamically to conduct A/B tests, allowing developers to quickly iterate and identify the most effective prompts for specific tasks without downtime.13  
* **Dynamic Templating (Jinja2):** For even greater flexibility, prompt strings stored externally can be treated as templates. Libraries like Jinja2 (natively supported in Semantic Kernel for Python) allow for dynamic insertion of variables or conditional logic within the prompt text.60 This means a single template can serve multiple contexts by filling in placeholders at runtime, reducing prompt duplication and enhancing reusability. For example, a prompt template could include  
  {{ customer.first\_name }} to personalize AI responses.60  
* **Centralized Management:** For complex AI agent systems with numerous prompts, dedicated prompt management libraries or frameworks (e.g., PromptsManager from sokinpui/logLLM, or Langfuse 52) can provide a centralized store, command-line interfaces for easy manipulation, and API access for programmatic retrieval.

Choosing the Right Format:  
The choice between JSON and plaintext (INI) depends on the complexity of the prompts. For simple key-value configurations, INI files are sufficient. However, for prompts that require nested structures, lists of examples, or varying roles (like system/user messages in chat models), JSON is the superior choice due to its inherent support for complex data types. The ability to dynamically load and manage prompts from external files is a fundamental requirement for any serious AI agent workflow, allowing for rapid iteration, improved maintainability, and enhanced control over AI model behavior.

#### **Table: External Prompt Configuration Formats**

| Format | Pros | Cons | Example Snippet (Conceptual) | Value and Application |  |  |  |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **JSON** | \- Structured and hierarchical data support for complex prompts (esystem/user messages, few-shot examples).48 |  \- Native Python json module for easy parsing.48 |  \- Human-readable for complex structures.49 |  \- Ideal for version control and dynamic loading. | \- Can become verbose for very simple key-value pairs. \- Requires strict syntax adherence. | {"prompt\_key": {"system": "...", "user": "...", "examples": \[...\]}} | **Value:** Essential for managing complex AI prompts, especially for chat models and few-shot learning. Enables clear separation of prompt logic from code, facilitating A/B testing, rapid iteration, and version control. This directly translates to more agile AI agent development and deployment. |
| **Plaintext (INI-style)** | \- Extremely simple and lightweight for basic key-value pairs.54 |  \- Easy for manual editing. \- Python's configparser module provides built-in support.54 | \- Limited structural depth (sections and key-value pairs only). \- All values are read as strings, requiring manual type conversion. \- Less suitable for dynamic examples or multi-part prompts. | \\nprompt\_key \= Your prompt text here. | **Value:** Suitable for simpler, static AI model parameters or short, single-line prompts. Provides a quick and easy way to externalize basic configurations, improving maintainability for less complex AI behaviors. |  |  |

## **Conclusion**

The development of a robust AI agent workflow, encompassing automated web scraping, AI-powered content evaluation, email automation, and efficient data management, necessitates a holistic and best-practice-driven approach. Each component, while distinct, is intricately linked, contributing to the overall reliability, efficiency, and intelligence of the system.

Automated daily web scraping requires a foundation of robust error handling, including try-except blocks and exponential backoff retry logic, to ensure continuous operation despite transient network issues or website changes. The strategic decision to employ tools like Selenium for dynamic content must be balanced against its resource intensity, advocating for a tiered approach where simpler methods are prioritized. Furthermore, adherence to ethical guidelines, such as respecting robots.txt and implementing polite request delays, is not merely a compliance measure but a critical factor in the long-term viability of scraping operations. The integration of OpenAI API post-scraping transforms raw data into actionable intelligence through summarization and extraction, avoiding complex local NLP setups.

AI-powered content evaluation and dynamic categorization leverage the OpenAI API's capabilities, particularly the "LLM-as-a-judge" paradigm. The precision of prompt engineering, including clear criteria, structured instructions, Chain-of-Thought reasoning, and few-shot examples, directly dictates the quality and consistency of AI outputs. This emphasis on prompt design effectively shifts AI behavior definition from traditional coding to meticulous prompt construction, demanding similar development rigor. The agility offered by zero-shot and few-shot classification allows for dynamic adaptation to evolving content landscapes without extensive model retraining.

Python-based email workflows are essential for effective communication of AI-generated insights. Crafting rich HTML emails with embedded content and attachments enhances readability and user engagement. For collecting structured feedback, the generation of unique, potentially time-limited, UUID-based links ensures traceability and security, while a minimalist Flask backend provides an efficient, dedicated endpoint for data ingestion. This design prioritizes a low-friction user experience while maintaining data integrity.

Finally, the efficient storage of feedback data in a local SQLite database is fundamental for continuous improvement. A well-designed schema, incorporating appropriate data types, constraints, and indexing, is crucial for transforming raw feedback into analyzable data. Adhering to SQLite performance best practices, such as Write-Ahead Logging and batching operations, ensures the database remains responsive. The externalization of AI prompt configurations into JSON or plaintext files is a critical architectural decision, decoupling AI behavior from code, enabling version control, facilitating A/B testing, and supporting dynamic updates via templating.

In conclusion, the successful implementation of this AI agent workflow hinges on the synergistic integration of these components, each built upon a foundation of best practices in software engineering, data management, and AI interaction. This comprehensive framework provides a scalable, maintainable, and intelligent solution for automated content acquisition, evaluation, and feedback-driven refinement.

#### **Works cited**

1. Building a Robust Web Scraper with Error Handling and Retry Logic ..., accessed on July 7, 2025, [https://medium.com/techtrends-digest/building-a-robust-web-scraper-with-error-handling-and-retry-logic-3e7b6541bbbc](https://medium.com/techtrends-digest/building-a-robust-web-scraper-with-error-handling-and-retry-logic-3e7b6541bbbc)  
2. Python Web Scraping: Full Tutorial With Examples (2025 ..., accessed on July 7, 2025, [https://www.scrapingbee.com/blog/web-scraping-101-with-python/](https://www.scrapingbee.com/blog/web-scraping-101-with-python/)  
3. Web Scraping in Python (An Ultimate Guide) \- Scrapingdog, accessed on July 7, 2025, [https://www.scrapingdog.com/blog/web-scraping-with-python/](https://www.scrapingdog.com/blog/web-scraping-with-python/)  
4. BeautifulSoup \- Error Handling \- GeeksforGeeks, accessed on July 7, 2025, [https://www.geeksforgeeks.org/python/beautifulsoup-error-handling/](https://www.geeksforgeeks.org/python/beautifulsoup-error-handling/)  
5. Exploring the power of Beautiful Soup for web scraping in Python, accessed on July 7, 2025, [https://discuss.datasciencedojo.com/t/exploring-the-power-of-beautiful-soup-for-web-scraping-in-python/912](https://discuss.datasciencedojo.com/t/exploring-the-power-of-beautiful-soup-for-web-scraping-in-python/912)  
6. Working with the OpenAI API in Python \- Trenton McKinney, accessed on July 7, 2025, [https://trenton3983.github.io/posts/openai-api/](https://trenton3983.github.io/posts/openai-api/)  
7. jarif87/daily-email-report: Python tool that automates daily ... \- GitHub, accessed on July 7, 2025, [https://github.com/jarif87/daily-email-report](https://github.com/jarif87/daily-email-report)  
8. openai-cookbook/examples/evaluation ... \- GitHub, accessed on July 7, 2025, [https://github.com/openai/openai-cookbook/blob/main/examples/evaluation/How\_to\_eval\_abstractive\_summarization.ipynb](https://github.com/openai/openai-cookbook/blob/main/examples/evaluation/How_to_eval_abstractive_summarization.ipynb)  
9. Best practices for prompt engineering with the OpenAI API, accessed on July 7, 2025, [https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-the-openai-api](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-the-openai-api)  
10. From Art to Engineering: A Practical Rubric for GPT-4.1 Prompt Design \- Medium, accessed on July 7, 2025, [https://medium.com/@reveriano.francisco/from-art-to-engineering-a-practical-rubric-for-gpt-4-1-prompt-design-e4cc9f9d55de](https://medium.com/@reveriano.francisco/from-art-to-engineering-a-practical-rubric-for-gpt-4-1-prompt-design-e4cc9f9d55de)  
11. Asked ChatGPT to evaluate my prompt engineering skill across all my past chats and give a quantifiable ranking. : r/ChatGPTPromptGenius \- Reddit, accessed on July 7, 2025, [https://www.reddit.com/r/ChatGPTPromptGenius/comments/1kr221a/asked\_chatgpt\_to\_evaluate\_my\_prompt\_engineering/](https://www.reddit.com/r/ChatGPTPromptGenius/comments/1kr221a/asked_chatgpt_to_evaluate_my_prompt_engineering/)  
12. GPT-based zero-shot text classification with the OpenAI API ..., accessed on July 7, 2025, [https://developer.dataiku.com/12/tutorials/machine-learning/genai/nlp/gpt-zero-shot-clf/index.html](https://developer.dataiku.com/12/tutorials/machine-learning/genai/nlp/gpt-zero-shot-clf/index.html)  
13. Evals API Use-case \- Bulk model and prompt experimentation | OpenAI Cookbook, accessed on July 7, 2025, [https://cookbook.openai.com/examples/evaluation/use-cases/bulk-experimentation](https://cookbook.openai.com/examples/evaluation/use-cases/bulk-experimentation)  
14. The Few Shot Prompting Guide \- PromptHub, accessed on July 7, 2025, [https://www.prompthub.us/blog/the-few-shot-prompting-guide](https://www.prompthub.us/blog/the-few-shot-prompting-guide)  
15. GPT-4 \- Prompt Engineering Guide, accessed on July 7, 2025, [https://www.promptingguide.ai/models/gpt-4](https://www.promptingguide.ai/models/gpt-4)  
16. Text Classification | Endpoints | Openai Api Tutorial, accessed on July 7, 2025, [https://www.swiftorial.com/tutorials/artificial\_intelligence/openai\_api/endpoints/text\_classification](https://www.swiftorial.com/tutorials/artificial_intelligence/openai_api/endpoints/text_classification)  
17. API Reference \- OpenAI Platform, accessed on July 7, 2025, [https://platform.openai.com/docs/api-reference](https://platform.openai.com/docs/api-reference)  
18. OpenAI Python API \- Complete Guide \- GeeksforGeeks, accessed on July 7, 2025, [https://www.geeksforgeeks.org/data-science/openai-python-api/](https://www.geeksforgeeks.org/data-science/openai-python-api/)  
19. How To Send Email Notifications With Attachments in Python \- Better Programming, accessed on July 7, 2025, [https://betterprogramming.pub/send-e-mail-notification-with-attachment-in-python-b60f892bdb9b](https://betterprogramming.pub/send-e-mail-notification-with-attachment-in-python-b60f892bdb9b)  
20. Sending Emails With Attachments Using Python | by Abdullah zulfiqar | Medium, accessed on July 7, 2025, [https://medium.com/@abdullahzulfiqar653/sending-emails-with-attachments-using-python-32b908909d73](https://medium.com/@abdullahzulfiqar653/sending-emails-with-attachments-using-python-32b908909d73)  
21. How to Send Email in Python: SMTP & Email API Methods Explained \- Mailtrap, accessed on July 7, 2025, [https://mailtrap.io/blog/python-send-email/](https://mailtrap.io/blog/python-send-email/)  
22. How to create a link in the message body of email with Python? \[closed\], accessed on July 7, 2025, [https://gis.stackexchange.com/questions/85464/how-to-create-a-link-in-the-message-body-of-email-with-python](https://gis.stackexchange.com/questions/85464/how-to-create-a-link-in-the-message-body-of-email-with-python)  
23. Python/Email \- How to receive user feedback with send\_email? \- Stack Overflow, accessed on July 7, 2025, [https://stackoverflow.com/questions/32975823/python-email-how-to-receive-user-feedback-with-send-email](https://stackoverflow.com/questions/32975823/python-email-how-to-receive-user-feedback-with-send-email)  
24. uuid — UUID objects according to RFC 4122 — Python 3.13.5 documentation, accessed on July 7, 2025, [https://docs.python.org/3/library/uuid.html](https://docs.python.org/3/library/uuid.html)  
25. Generating Random id's using UUID in Python \- GeeksforGeeks, accessed on July 7, 2025, [https://www.geeksforgeeks.org/python/generating-random-ids-using-uuid-python/](https://www.geeksforgeeks.org/python/generating-random-ids-using-uuid-python/)  
26. How to generate a unique auth token in python? \- Stack Overflow, accessed on July 7, 2025, [https://stackoverflow.com/questions/41354205/how-to-generate-a-unique-auth-token-in-python](https://stackoverflow.com/questions/41354205/how-to-generate-a-unique-auth-token-in-python)  
27. Get customer feedback by sending link to uniquely populated feedback form \- Bubble Forum, accessed on July 7, 2025, [https://forum.bubble.io/t/get-customer-feedback-by-sending-link-to-uniquely-populated-feedback-form/23410](https://forum.bubble.io/t/get-customer-feedback-by-sending-link-to-uniquely-populated-feedback-form/23410)  
28. Handling Email Confirmation During Registration in Flask \- Real Python, accessed on July 7, 2025, [https://realpython.com/handling-email-confirmation-in-flask/](https://realpython.com/handling-email-confirmation-in-flask/)  
29. API Route Parameters vs. Query Parameters Clearly Explained in Flask and Express | by Ebo Jackson | Medium, accessed on July 7, 2025, [https://medium.com/@ebojacky/api-route-parameters-vs-query-parameters-clearly-explained-in-flask-and-express-e2cea6ad5ab1](https://medium.com/@ebojacky/api-route-parameters-vs-query-parameters-clearly-explained-in-flask-and-express-e2cea6ad5ab1)  
30. GET Request Query Parameters with Flask \- GeeksforGeeks, accessed on July 7, 2025, [https://www.geeksforgeeks.org/python/get-request-query-parameters-with-flask/](https://www.geeksforgeeks.org/python/get-request-query-parameters-with-flask/)  
31. Login and Registration Project in Flask using MySQL \- GeeksforGeeks, accessed on July 7, 2025, [https://www.geeksforgeeks.org/python/login-and-registration-project-using-flask-and-mysql/](https://www.geeksforgeeks.org/python/login-and-registration-project-using-flask-and-mysql/)  
32. Quickstart — Flask Documentation (3.1.x), accessed on July 7, 2025, [https://flask.palletsprojects.com/en/stable/quickstart/](https://flask.palletsprojects.com/en/stable/quickstart/)  
33. Using SQLite 3 with Flask — Flask Documentation (3.1.x), accessed on July 7, 2025, [https://flask.palletsprojects.com/en/stable/patterns/sqlite3/](https://flask.palletsprojects.com/en/stable/patterns/sqlite3/)  
34. Build a Simple REST API Using Python Flask and SQLite (With Tests) \- DZone, accessed on July 7, 2025, [https://dzone.com/articles/build-simple-api-with-python-flask-and-sql](https://dzone.com/articles/build-simple-api-with-python-flask-and-sql)  
35. Python Snippets: SQLite & SQLAlchemy Database Tips \- Zencoder, accessed on July 7, 2025, [https://zencoder.ai/blog/python-database-sqlite-sqlalchemy-snippets](https://zencoder.ai/blog/python-database-sqlite-sqlalchemy-snippets)  
36. Appropriate Uses For SQLite, accessed on July 7, 2025, [https://www.sqlite.org/whentouse.html](https://www.sqlite.org/whentouse.html)  
37. Best Practices for Database Schema Design in SQLite | MoldStud, accessed on July 7, 2025, [https://moldstud.com/articles/p-best-practices-for-database-schema-design-in-sqlite](https://moldstud.com/articles/p-best-practices-for-database-schema-design-in-sqlite)  
38. Get Schema in SQLite with Python | Tom Ordonez, accessed on July 7, 2025, [https://tomordonez.com/get-schema-sqlite-python/](https://tomordonez.com/get-schema-sqlite-python/)  
39. SQLite Python: Creating New Tables Example, accessed on July 7, 2025, [https://www.sqlitetutorial.net/sqlite-python/creating-tables/](https://www.sqlitetutorial.net/sqlite-python/creating-tables/)  
40. How do I use a python variable in a SQLITE SELECT statement \- Stack Overflow, accessed on July 7, 2025, [https://stackoverflow.com/questions/49103406/how-do-i-use-a-python-variable-in-a-sqlite-select-statement](https://stackoverflow.com/questions/49103406/how-do-i-use-a-python-variable-in-a-sqlite-select-statement)  
41. Best practices for SQLite performance | App quality \- Android Developers, accessed on July 7, 2025, [https://developer.android.com/topic/performance/sqlite-performance-best-practices](https://developer.android.com/topic/performance/sqlite-performance-best-practices)  
42. sqlite3 — DB-API 2.0 interface for SQLite databases — Python 3.13.5 documentation, accessed on July 7, 2025, [https://docs.python.org/3/library/sqlite3.html](https://docs.python.org/3/library/sqlite3.html)  
43. Python: Create a SQLite table within the database \- w3resource, accessed on July 7, 2025, [https://www.w3resource.com/python-exercises/sqlite/python-sqlite-exercise-3.php](https://www.w3resource.com/python-exercises/sqlite/python-sqlite-exercise-3.php)  
44. SQLite Python: Inserting Data, accessed on July 7, 2025, [https://www.sqlitetutorial.net/sqlite-python/insert/](https://www.sqlitetutorial.net/sqlite-python/insert/)  
45. Python SQLite \- Insert Data \- GeeksforGeeks, accessed on July 7, 2025, [https://www.geeksforgeeks.org/python/python-sqlite-insert-data/](https://www.geeksforgeeks.org/python/python-sqlite-insert-data/)  
46. Python Sqlite3: INSERT INTO table VALUE(dictionary goes here) \- Stack Overflow, accessed on July 7, 2025, [https://stackoverflow.com/questions/14108162/python-sqlite3-insert-into-table-valuedictionary-goes-here](https://stackoverflow.com/questions/14108162/python-sqlite3-insert-into-table-valuedictionary-goes-here)  
47. 10 Best Practices for Logging in Python | Better Stack Community, accessed on July 7, 2025, [https://betterstack.com/community/guides/logging/python/python-logging-best-practices/](https://betterstack.com/community/guides/logging/python/python-logging-best-practices/)  
48. Read JSON file using Python \- GeeksforGeeks, accessed on July 7, 2025, [https://www.geeksforgeeks.org/python/read-json-file-using-python/](https://www.geeksforgeeks.org/python/read-json-file-using-python/)  
49. Read JSON File Using Python Code and Prompt 2025 \- DEV Community, accessed on July 7, 2025, [https://dev.to/onlinejsonformatter0/read-json-file-using-python-code-and-prompt-2025-5ji](https://dev.to/onlinejsonformatter0/read-json-file-using-python-code-and-prompt-2025-5ji)  
50. \[query\] Inputting Json to llama cpp and getting output into txt file ? · Issue \#1192 \- GitHub, accessed on July 7, 2025, [https://github.com/abetlen/llama-cpp-python/issues/1192](https://github.com/abetlen/llama-cpp-python/issues/1192)  
51. GPT4o Ultimate Consistency: How I Automated AI Image Prompt Engineering with Python \+ JSON \- YouTube, accessed on July 7, 2025, [https://www.youtube.com/watch?v=P2J-5kNn4Uo](https://www.youtube.com/watch?v=P2J-5kNn4Uo)  
52. I have built a prompts manager for python project\! : r/LLMDevs \- Reddit, accessed on July 7, 2025, [https://www.reddit.com/r/LLMDevs/comments/1jebp95/i\_have\_built\_a\_prompts\_manager\_for\_python\_project/](https://www.reddit.com/r/LLMDevs/comments/1jebp95/i_have_built_a_prompts_manager_for_python_project/)  
53. Creating a json file from user input in python 3.X \- Stack Overflow, accessed on July 7, 2025, [https://stackoverflow.com/questions/54355382/creating-a-json-file-from-user-input-in-python-3-x](https://stackoverflow.com/questions/54355382/creating-a-json-file-from-user-input-in-python-3-x)  
54. How to read a config file using python \- Stack Overflow, accessed on July 7, 2025, [https://stackoverflow.com/questions/19379120/how-to-read-a-config-file-using-python](https://stackoverflow.com/questions/19379120/how-to-read-a-config-file-using-python)  
55. 3\. Writing the Setup Configuration File — Python 3.10.17 documentation, accessed on July 7, 2025, [https://docs.python.org/3.10/distutils/configfile.html](https://docs.python.org/3.10/distutils/configfile.html)  
56. Python Config Parser environment variables \- Stack Overflow, accessed on July 7, 2025, [https://stackoverflow.com/questions/41889499/python-config-parser-environment-variables](https://stackoverflow.com/questions/41889499/python-config-parser-environment-variables)  
57. abilzerian/LLM-Prompt-Library: A playground of highly ... \- GitHub, accessed on July 7, 2025, [https://github.com/abilzerian/LLM-Prompt-Library](https://github.com/abilzerian/LLM-Prompt-Library)  
58. Open Source Prompt Management \- Langfuse, accessed on July 7, 2025, [https://langfuse.com/docs/prompts/get-started](https://langfuse.com/docs/prompts/get-started)  
59. Example: Langfuse Prompt Management with Langchain (Python), accessed on July 7, 2025, [https://langfuse.com/docs/prompts/example-langchain](https://langfuse.com/docs/prompts/example-langchain)  
60. Using Jinja2 prompt template syntax with Semantic Kernel \- Learn Microsoft, accessed on July 7, 2025, [https://learn.microsoft.com/en-us/semantic-kernel/concepts/prompts/jinja2-prompt-templates](https://learn.microsoft.com/en-us/semantic-kernel/concepts/prompts/jinja2-prompt-templates)  
61. I created an open-source Python library for local prompt management, versioning, and templating : r/LLMDevs \- Reddit, accessed on July 7, 2025, [https://www.reddit.com/r/LLMDevs/comments/1j3h4ra/i\_created\_an\_opensource\_python\_library\_for\_local/](https://www.reddit.com/r/LLMDevs/comments/1j3h4ra/i_created_an_opensource_python_library_for_local/)