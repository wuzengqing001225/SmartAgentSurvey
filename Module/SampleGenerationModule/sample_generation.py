from UtilityFunctions import json_processing
import json

def sample_dimension_generation(config_set, processed_data):
    # NOTICE: Forced conversion with gpt-4o / claude-3-sonnet model for better performance

    config, llm_client, logger, output_manager = config_set

    survey_text = json_processing.get_key_list(processed_data, target_key = 'question')
    if len(survey_text) > 20: survey_text = survey_text[:20]

    if llm_client.provider == "anthropic":
        llm_client.model = 'claude-3-sonnet-latest'
    else:
        llm_client.model = 'gpt-4o'

    sample_dimensions = llm_client.generate(
        prompt=f"""I am researching the background attributes that participants should have for a social science survey (e.g., age, socioeconomic level). Based on the survey, please generate some attributes. Also provide the possible options and the distribution of each attribute. The attributes should be representative and consist to represent a real human profile. Do not use too problem-specific attributes but social background attributes. Options should be differentiated from each other, e.g. assuming an age attribute, the step size should be greater than 1. Gender and race are not considered in this survey.
        
Return a JSON object, for each attribute, it should include options (list), population distribution where total is 100 (list), and profile format (str). If there are many potential options, add an 'others' option. Note that if an attribute is scale based, output "scale" including three numbers: lower bound, upper bound, and step of the scale. The distribution of scale should be "uniform" or "normal". Try your best to use real world distributions of the attributes.

Example format:
{{  
    "education level": {{
        "options": ["high school","some college","bachelor","master","doctoral","others"],
        "distribution": [30, 25, 20, 15, 5, 5]
        "format": "Your education level is X".
    }},
    "job satisfaction": {{
        "scale": [1, 10, 1],
        "distribution": "uniform",
        "format": "Your job satisfaction is X (1 is lowest and 10 is highest)".
    }}
}}

Survey: {survey_text}

Be careful with the JSON format. Do not wrap elements in an array.""",
        system_prompt="You are a survey analysis assistant. Strictly return JSON only, with no explanations or additional text. Do not place ```json at the beginning.",
        force_max_tokens = 1024
    )

    llm_client.model = config.get("llm_settings", {}).get("model", "gpt-4o-mini")
    
    sample_dimensions = json.loads(sample_dimensions)

    output_manager.save_json(sample_dimensions, 'sample_dimensions.json')
    logger.info(f"Sample dimensions saved.")

    return sample_dimensions
