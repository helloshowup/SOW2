**AI Agent Workflow Research Summary**

**Initial Overview:**
Develop an AI agent to autonomously gather and evaluate brand-adjacent, non-trend-driven content relevant to consumer interests. Inspiration drawn from SuperAnnotate’s iterative training workflows, emphasizing continuous refinement via human feedback.

**Core Workflow Components:**

1. **Daily Data Collection:**

   - Google Search API and web scraping as primary tools.
   - Content should include news articles, academic papers, and innovative, out-of-the-box sources.

2. **Content Evaluation:**

   - Scoring based on topic relevance, source credibility, and consumer engagement potential.

3. **Human-in-the-Loop Feedback:**

   - Human reviewers provide binary (yes/no) feedback initially, potentially evolving to a detailed rating scale (e.g., 1-5).
   - Feedback directly trains the AI to enhance relevance assessment.

4. **Continuous AI Model Training:**

   - Incremental learning through human annotations.
   - Progressive improvement of content relevance predictions.

**Expanded and Creative Content Sources:**

- Industry Reports (White papers, market analyses)
- Competitor and industry leader blogs
- Forums (e.g., Reddit, Quora)
- Podcasts and webinar summaries or transcripts
- Regulatory updates from authoritative bodies

**Updated Workflow Summary:**

1. **Content Prioritization:**
   No specific content types are prioritized; focus is on developing the prompt engineering aspect.

2. **Geographical Scope:**
   The agent should monitor both African/South African regions and global news, ensuring significant global events are captured.

3. **Language Capabilities:**
   Limit content processing to English for now.

4. **Feedback Depth:**
   Begin with a simple yes-no feedback system, with potential to expand to a nuanced rating scale similar to SuperAnnotate’s methodology.

5. **System Integration:**
   No immediate integration with existing tools or platforms is required. The focus is on developing a cost-effective prototype.

**Prompt Engineering and Automation:**

- Development of effective system and user prompts for content selection, summarization, and categorization.
- Emphasis on automating the search component in a cost-effective way.

**Technical Constraints and Preferences:**

- Developed locally; no cloud infrastructure.
- MVP demonstrates the workflow for a single instance: monitor the internet for approximately 10 minutes, categorize findings, and send an email.
- Preference for Python and BeautifulSoup for web scraping.
- Avoid usage-based cost APIs (e.g., SERP API).
- Include capability for calculating estimated running costs clearly.

**Email Communication:**

- Utilize Python's `smtplib` and `email` libraries to send plain-text emails summarizing the top five findings.
- Implement email receiving using Python's `imaplib` and `email` libraries to parse feedback ratings from clients for training purposes.

**Feedback Integration:**

- Store feedback ratings locally (e.g., SQLite database) for AI training.
- Use feedback data iteratively to refine content selection accuracy.

**Next Steps & Questions:**

1. **Email Parsing Specifics:**
   - Feedback should be easy and clickable, potentially through a web form for each finding, enabling straightforward rating capture for training purposes.

2. **Data Storage Preferences:**
   - SQLite database preferred for ease of future handoff.
   - Data exporting capability is required, with exports anticipated approximately every six months.

3. **Error Handling and Notifications:**
   - Implement email notifications to hello@showup.courses with detailed error descriptions if issues occur during web scraping or email processing.

