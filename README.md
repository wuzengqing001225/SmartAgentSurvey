# Smart Agent Survey: LLM Automated Survey Response Framework

**Smart Agent Survey** is an application that automates survey response generation by processing survey documents and creating multiple synthetic respondents using LLM agents. Users can input their survey file and either upload sample profiles or generate diverse respondent profiles automatically, after which the system produces comprehensive survey responses from each synthetic respondent based on their unique profiles and characteristics.

## Functions

![Workflow](https://github.com/wuzengqing001225/SmartAgentSurvey/blob/main/static/images/workflow.png?raw=true)

**1. Preprocessing:** Survey file upload, survey flow validation, and optional attention check question addition.

**2. Sample Space Generation:** Upload sample profiles from a text file or generate them automatically using LLM models. The automated generation feature enables the creation of sample dimensions directly from survey content, with the option to edit dimension attributes.

**3. Execution:** The LLM answers the questionnaire based on the sample profile and returns the questionnaire responses in both JSON and CSV formats.

## Demo

[https://github.com/user-attachments/assets/e1810e31-2143-44e8-bb03-6f35b2536685](https://github.com/user-attachments/assets/e1810e31-2143-44e8-bb03-6f35b2536685)

Demo questionnaire source: [Sample Survey Questions for Current Undergraduate Students, Teaching Support Centre, Western University](https://teaching.uwo.ca/pdf/curriculum/Sample-Survey-Questions-Template-for-Undergraduate-Students-.pdf)

## Setup

- Install dependencies: `pip install -r requirements.txt`
- Run `app.py` and open url [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Project Structure

The project is organized into a modular structure to separate concerns, making it easier to maintain and extend.

```
SmartAgentSurvey/
├── Config/                      # Stores all configuration files.
├── Data/                        # Handles all user data and generated outputs.
│   ├── Output/                  # Contains the final survey results (JSON, CSV).
│   └── UserUpload/              # Stores user-uploaded survey files.
├── Module/                      # Contains the core business logic of the application.
│   ├── PreprocessingModule/     # Handles survey ingestion, parsing, and validation.
│   ├── SampleGenerationModule/  # Manages the creation of synthetic respondent profiles.
│   └── ExecutionModule/         # Orchestrates the survey-taking process by LLM agents.
├── static/                      # Holds all static frontend assets.
│   ├── css/                     # Contains stylesheets for the web interface.
│   ├── js/                      # Contains JavaScript files for frontend interactivity.
│   └── images/                  # Stores images used in the UI.
├── templates/                   # Contains HTML templates for the Flask web application.
├── UtilityFunctions/            # Provides shared helper functions, like the LLM client.
├── Questionnaire/               # Provides example questionnaires.
├── app.py                       # The main entry point for the Flask application.
└── requirements.txt             # Lists the Python dependencies for the project.
```
