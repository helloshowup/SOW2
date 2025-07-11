# Repository Investigation- 11 July 2025

# Table of Contents

- [Build, Environment, and Dependency Management](https://www.google.com/search?q=%23build-environment-and-dependency-management)  
  - [Launch Script and Virtual Environment Activation](https://www.google.com/search?q=%23launch-script-and-virtual-environment-activation)  
  - [Undeclared Dependencies in pyproject.toml](https://www.google.com/search?q=%23undeclared-dependencies-in-pyprojecttoml)  
  - [Editable Installation and Package Configuration](https://www.google.com/search?q=%23editable-installation-and-package-configuration)  
- [Code Architecture and Import Strategy](https://www.google.com/search?q=%23code-architecture-and-import-strategy)  
  - [Custom Import Hook: Showup Tools Path Finder](https://www.google.com/search?q=%23custom-import-hook-showup-tools-path-finder)  
- [Fatal ImportError: enhanced\_generate\_content](https://www.google.com/search?q=%23fatal-importerror-enhanced_generate_content)  
- [Module Structure and Boundaries](https://www.google.com/search?q=%23module-structure-and-boundaries)  
- [Application Workflow and Logic](https://www.google.com/search?q=%23application-workflow-and-logic)  
  - [The run\_workflow Entry Point](https://www.google.com/search?q=%23the-run_workflow-entry-point)  
  - [Multi-Model Generation Strategy](https://www.google.com/search?q=%23multi-model-generation-strategy)  
  - [Student Handbook Integration (RAG System)](https://www.google.com/search?q=%23student-handbook-integration-rag-system)

---

## Build, Environment, and Dependency Management

### Launch Script and Virtual Environment Activation

\[cite\_start\]The Windows launch script (`run_simplified_app.bat`) is designed to activate a local virtual environment and then run the application. \[cite: 4\] \[cite\_start\]It first navigates to the project's root directory and then executes the activation script. \[cite: 5\] \[cite\_start\]This process assumes a `venv` folder exists at the project's root. \[cite: 8\] \[cite\_start\]An error message, "The system cannot find the path specified," suggests that the `venv` directory is either missing or its relative path is incorrect. \[cite: 8\] \[cite\_start\]The script in its current form does not create a virtual environment if one doesn't exist. \[cite: 9\]

\[cite\_start\]The primary issue is the failure of the relative path logic when the virtual environment has not been set up in the expected location. \[cite: 11\] \[cite\_start\]If the batch file is executed without setting up `venv` first, or if the file's location has been altered (which would affect the `%~dp0` resolution), the activation path becomes invalid. \[cite: 12\]

\[cite\_start\]The solution is to ensure the batch script can create the `venv` if it's missing or to provide instructions for manual creation beforehand. \[cite: 13\] \[cite\_start\]An alternative is to use an absolute path or an environment variable for the `venv`. \[cite: 14\] \[cite\_start\]For instance, the script could execute `python -m venv venv` if `venv\Scripts\activate.bat` is not found. \[cite: 15\] \[cite\_start\]It is also crucial to verify that the working directory is correct. \[cite: 15\]

### Undeclared Dependencies in pyproject.toml

\[cite\_start\]An error, "No module named 'claude\_api'," indicates that required packages were not declared in the `pyproject.toml` file. \[cite: 19\] \[cite\_start\]An audit of the code's imports revealed several missing dependencies\[cite: 20\]:

* \[cite\_start\]**OpenAI API**: The code references `openai`, but it was not listed in `pyproject.toml`. \[cite: 21\]  
* \[cite\_start\]**Azure Cognitive Services Speech SDK**: Modules import `azure.cognitiveservices.speech`, which requires the `azure-cognitiveservices-speech` package. \[cite: 23\]  
* \[cite\_start\]**Python-Docx**: The project uses `docx.*` imports, necessitating the `python-docx` package. \[cite: 25, 26\]  
* \[cite\_start\]**Markdown**: An import of `markdown` requires the `Markdown` PyPI package. \[cite: 26\]  
* \[cite\_start\]**Pillow**: The code utilizes `PIL` for image processing, which means `Pillow` is a required dependency. \[cite: 27\]  
* \[cite\_start\]**aiohttp**: This is used for asynchronous API calls but was not listed in the toml file. \[cite: 28\]  
* \[cite\_start\]**Streamlit**: It is mentioned in a dependency check and should be declared if any part of the tool uses it. \[cite: 29\]  
* \[cite\_start\]**Cache Utilities**: The code imports `cache_utils`, which is not a standard PyPI package and may be a missing internal module. \[cite: 30, 31\]

\[cite\_start\]While the `pyproject.toml` file has been updated to include some packages like `claude_api`, the full list of dependencies should be added to prevent `ModuleNotFound` errors. \[cite: 33, 34, 37\] \[cite\_start\]The complete list includes: **anthropic, claude\_api, openai, loguru, numpy, pandas, python-dotenv, scikit-learn, sentence-transformers, tqdm, markdown, python-docx, Pillow, aiohttp, azure-cognitiveservices-speech**, and potentially **streamlit**. \[cite: 36\]

### Editable Installation and Package Configuration

\[cite\_start\]The project is installed in editable mode (`pip install -e .`), which requires the package structure to be correctly defined. \[cite: 39\] \[cite\_start\]The `pyproject.toml` specifies the project name but does not explicitly list the packages or use a discovery mechanism. \[cite: 40\] \[cite\_start\]The non-standard repository layout can cause modules to be missed during installation. \[cite: 42\] \[cite\_start\]The codebase has several top-level directories that need to be recognized as packages. \[cite: 43, 44\] \[cite\_start\]A naming mismatch, such as a folder named `showup-core` being imported as `showup_core`, can also cause issues with editable installs. \[cite: 45, 46\] \[cite\_start\]The application's startup code manually modifies `sys.path`, which is a clear sign of improper packaging. \[cite: 47, 48\]

\[cite\_start\]The recommended solution is to update the packaging configuration to include all modules. \[cite: 54\] \[cite\_start\]This involves renaming directories to valid Python package names (e.g., `showup-core` to `showup_core`) and configuring `pyproject.toml` to automatically find all packages under the project root. \[cite: 55, 56, 59\] \[cite\_start\]This will make the modules importable without manual path adjustments and improve the system's reliability. \[cite: 61, 63\]

---

## Code Architecture and Import Strategy

### Custom Import Hook: Showup Tools Path Finder

\[cite\_start\]Earlier versions of the code utilized a custom importer named `ShowupToolsPathFinder`. \[cite: 66\] \[cite\_start\]This hook was designed to resolve import issues arising from naming inconsistencies, such as mapping module names with underscores to directory names with hyphens (e.g., importing `showup_core` from a directory named `showup-core`). \[cite: 67, 68, 69\] \[cite\_start\]This workaround suggests a past design problem where directory names were not valid for Python's import syntax. \[cite: 70, 71\]

\[cite\_start\]The recommended fix is to eliminate the need for this custom import hook by normalizing package names. \[cite: 74\] \[cite\_start\]This involves renaming directories to match the import names used in the code. \[cite: 75\] \[cite\_start\]Once the names are consistent, the standard import system will function correctly, and the custom finder can be removed, simplifying the codebase and reducing potential import errors. \[cite: 76, 77, 79\]

---

## Fatal ImportError: enhanced\_generate\_content

\[cite\_start\]A critical error, "cannot import name 'enhanced\_generate\_content' from 'showup\_tools.simplified\_app.rag\_system'," prevents the application from running. \[cite: 82\] \[cite\_start\]This is triggered in `simplified_workflow/content_generator.py`. \[cite: 84\] \[cite\_start\]The failure occurs because an internal import within the `rag_system` package did not succeed, meaning `enhanced_generate_content` was never defined in that module's namespace. \[cite: 85\]

\[cite\_start\]The root cause is a `NameError` in `rag_integration.py`, where a variable named `settings` is referenced without being defined. \[cite: 86, 87\] \[cite\_start\]This error during module initialization prevents the `rag_integration` module from executing completely, so its functions are never bound. \[cite: 87\] \[cite\_start\]A check for circular dependencies confirmed that this is not the issue; the problem lies solely with the exception in `rag_integration.py`. \[cite: 89, 90, 91\]

\[cite\_start\]The solution is to fix the `rag_integration.py` module so it can be imported cleanly. \[cite: 94\] \[cite\_start\]The `settings` variable should either be passed as a parameter or removed. \[cite: 95\] \[cite\_start\]The simplest fix is to remove the logic that uses `settings.get('specific_query')` and instead rely on the `query` parameter that is already being passed. \[cite: 98\] \[cite\_start\]Resolving this bug will allow the `rag_system` to import `enhanced_generate_content` successfully, which in turn will allow `simplified_workflow.content_generator` to load without error. \[cite: 99\]

---

## Module Structure and Boundaries

\[cite\_start\]The repository consists of three main modules\[cite: 101\]:

* \[cite\_start\]**showup\_core**: Contains fundamental utilities, configuration, and API interfacing code. \[cite: 102\] \[cite\_start\]It is intended to be independent of the UI and higher-level workflows. \[cite: 104\]  
* \[cite\_start\]**showup\_tools**: Acts as the main application logic layer, including the RAG system and a simplified UI. \[cite: 107, 108, 109\] \[cite\_start\]It uses utilities from `showup_core` to provide features for the content generation workflow. \[cite: 109\]  
* \[cite\_start\]**simplified\_workflow**: This module orchestrates the content generation process, defining the business logic and sequence of steps. \[cite: 112, 113\] \[cite\_start\]It depends on `showup_core` and `showup_tools` but not the other way around, which is a correct one-way dependency. \[cite: 114, 115, 116\]  
* \[cite\_start\]**showup\_editor\_ui**: A separate package that contains a more advanced graphical user interface. \[cite: 117\]

\[cite\_start\]Each module has a clear responsibility, and maintaining these boundaries is crucial for the project's architecture. \[cite: 120, 124\] \[cite\_start\]`showup_core` is the low-level base, `simplified_workflow` is the high-level logic, `showup_tools` provides supporting features, and UI modules wrap everything for the user. \[cite: 120, 121, 122, 123\] \[cite\_start\]To maintain stability, imports should remain one-directional (core \-\> tools \-\> workflow/UI), and the code should avoid circular dependencies. \[cite: 126, 127, 128\]

---

## Application Workflow and Logic

### The run\_workflow Entry Point

\[cite\_start\]The primary entry point for the content generation process is the `run_workflow` function in the `simplified_workflow` module. \[cite: 132\] \[cite\_start\]It wraps an asynchronous `main()` coroutine. \[cite: 133\]

**Inputs:**

* \[cite\_start\]`csv_path`: Path to the curriculum CSV file. \[cite: 135\]  
* \[cite\_start\]`course_name`: Name of the course. \[cite: 136\]  
* \[cite\_start\]`learner_profile`: Description of the target audience. \[cite: 137\]  
* \[cite\_start\]`ui_settings`: A dictionary with configuration options. \[cite: 138\]  
* \[cite\_start\]`selected_modules`: An optional list of modules to process. \[cite: 140\]  
* \[cite\_start\]`instance_id`: An identifier for the run. \[cite: 142\]  
* \[cite\_start\]`workflow_phase`: Can limit execution to a specific phase ("generate", "compare", "review", or "finalize"). \[cite: 143\]  
* \[cite\_start\]`output_dir`: Directory for saving output files. \[cite: 144\]  
* \[cite\_start\]`progress_queue`: A queue for sending progress updates to the GUI. \[cite: 145\]

**Process:**

1. \[cite\_start\]**Initialization**: Sets up logging and creates a summary dictionary. \[cite: 147\]  
2. \[cite\_start\]**Data Loading**: Reads the CSV and creates output subdirectories for each phase. \[cite: 147\]  
3. \[cite\_start\]**Filtering**: Filters rows based on `selected_modules` if provided. \[cite: 148\]  
4. \[cite\_start\]**Data Preparation**: For each row, it extracts variables, builds context from adjacent steps, and loads a content generation template. \[cite: 149, 150, 151, 152, 153\]  
5. \[cite\_start\]**Phase Execution**: It iterates through each row, processing it through the required phases sequentially. \[cite: 156\] \[cite\_start\]If a phase fails, it stops processing that row and moves to the next. \[cite: 158\] \[cite\_start\]Interim results are saved periodically. \[cite: 159\]  
6. \[cite\_start\]**Finalization**: After processing all rows, it collates results, creates phase-specific summaries, and merges all log entries. \[cite: 160, 161\]

**Return Value:** \[cite\_start\]The function returns a `summary` dictionary containing the final status, success/error counts, log file path, output directories, and a list of processed rows with their results. \[cite: 161, 162, 163, 164, 165, 166, 167\] \[cite\_start\]This summary is used by the GUI to display results. \[cite: 168\]

\[cite\_start\]State is managed by passing a `row_data_item` dictionary through the phases, with each phase appending its results. \[cite: 170, 171\] \[cite\_start\]This avoids global state and ensures data flows sequentially. \[cite: 173, 174\]

### Multi-Model Generation Strategy

\[cite\_start\]The system supports using a different model for initial content generation than for subsequent processing steps. \[cite: 177\] \[cite\_start\]This allows for a faster, cheaper model to be used for initial drafts, while a more powerful model handles refinement tasks like comparison and review. \[cite: 178\]

\[cite\_start\]In the generation phase, the code checks for an `initial_generation_model` in the UI settings, with a default of "claude-3-haiku-20240307". \[cite: 179, 180, 181\] \[cite\_start\]It uses this model to generate three initial versions of the content. \[cite: 182\] \[cite\_start\]For all subsequent phases, such as comparison and review, the system uses the main "Processing Steps Model" specified in the UI settings. \[cite: 184, 185, 186, 191\] \[cite\_start\]This two-model workflow is a good practice, allowing for a balance of speed, cost, and quality. \[cite: 196\] \[cite\_start\]The backend code already supports this; the key is to ensure the UI correctly passes the selected model IDs in the `ui_settings` dictionary. \[cite: 197\]

### Student Handbook Integration (RAG System)

\[cite\_start\]The "Pull relevant information from student handbook" option enables a Retrieval-Augmented Generation (RAG) workflow. \[cite: 200\] \[cite\_start\]When activated, the system retrieves context from a student handbook to inform content creation. \[cite: 201\]

**How it works:**

1. \[cite\_start\]**Vector Database**: The `rag_system` module sets up a vector database to index and query the handbook text, retrieving only relevant sections to save on tokens. \[cite: 203, 205\]  
2. \[cite\_start\]**Information Extraction**: Before generation, if the feature is enabled, the workflow calls `extract_student_handbook_information()`. \[cite: 207, 208\]  
3. \[cite\_start\]**Querying**: This function uses the current step's content outline to query the vector DB for the most relevant chunks of the handbook. \[cite: 209, 210\]  
4. \[cite\_start\]**Context Injection**: The retrieved text snippets are then formatted and inserted directly into the prompt that is sent to the language model. \[cite: 212, 216, 217\]  
5. \[cite\_start\]**RAG-Enhanced Generation**: The model then generates content based on both the original outline and the curated, relevant text from the handbook. \[cite: 218\] \[cite\_start\]The system has a dedicated function, `enhanced_generate_content`, that manages this RAG process, including caching and token limit checks. \[cite: 222, 229, 230\]

\[cite\_start\]This RAG integration is a powerful feature for ensuring the generated content is accurate and consistent with specific source material like a student handbook. \[cite: 233, 234, 239\] \[cite\_start\]While there is some redundancy in the implementation that could be streamlined, the functional design is sound. \[cite: 224, 240, 241\]

