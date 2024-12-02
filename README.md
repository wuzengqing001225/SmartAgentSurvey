# Smart Agent Survey: LLM Automated Survey Response Framework 

**Smart Agent Survey** is an application that automates survey response generation by processing survey documents and creating multiple synthetic respondents using LLM agents. Users can input their survey file and either upload sample profiles or generate diverse respondent profiles automatically, after which the system produces comprehensive survey responses from each synthetic respondent based on their unique profiles and characteristics.

## Functions

![Workflow](https://github.com/wuzengqing001225/SmartAgentSurvey/blob/main/static/images/workflow.png?raw=true)

**1. Preprocessing:** Survey file upload, survey flow validation, and optional attention check question addition.

**2. Sample Space Generation:** Upload sample profiles from a text file or generate them automatically using LLM models. The automated generation feature enables the creation of sample dimensions directly from survey content, with the option to edit dimension attributes.

**3. Execution:** The LLM answers the questionnaire based on the sample profile and returns the questionnaire responses in both JSON and CSV formats.

## Demo

https://github.com/user-attachments/assets/e1810e31-2143-44e8-bb03-6f35b2536685

Demo questionnaire source: [TCU Test from Institute of Behavioral Research, Texas Christian University](https://ibr.tcu.edu/forms/)

## Setup

- Install dependencies: `pip install -r requirements.txt`
- Run `app.py` and open url http://127.0.0.1:5000
- File Structure

```bash
├── Config/
│   ├── config.json        # Configuration file
├── Data/
│   ├── Output/            # Execution results
│   └── UserUpload/        # Survey files
├── Module/
│   ├── PreprocessingModule/
│   ├── SampleGenerationModule/
│   └── ExecutionModule/
└── app.py
```
