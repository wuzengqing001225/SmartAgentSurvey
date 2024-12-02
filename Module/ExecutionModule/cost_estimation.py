import json
import difflib
from Module.ExecutionModule.format_questionnaire import format_full_question
from UtilityFunctions import json_processing

def token_consumption_estimation(processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256):
    full_question_list, full_output_length = format_full_question(processed_data, output_max_token)

    input_english_chars_consumption = (len(full_question_list) + len(question_segments) * len(sample_profile_0)) * sample_space_size
    output_english_chars_consumption = full_output_length * sample_space_size

    input_prompt_sample_dimension = 1590 + len(full_question_list)
    input_prompt_preprocess = 1728 + len(full_question_list)
    input_english_chars_consumption += input_prompt_sample_dimension + input_prompt_preprocess

    output_prompt_sample_dimension = 1024
    output_prompt_preprocess = len(full_question_list) * 1.2
    output_english_chars_consumption += output_prompt_sample_dimension + output_prompt_preprocess

    input_token_estimation = input_english_chars_consumption // 4
    output_token_estimation = output_english_chars_consumption // 4

    return input_token_estimation, output_token_estimation

def cost_estimation(config_set, processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256):
    config, llm_client, logger, output_manager = config_set
    model_name = json_processing.get_json_nested_value(config, "llm_settings.model")
    
    input_token_estimation, output_token_estimation = token_consumption_estimation(processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token)

    # Load pricing data from JSON
    with open('./Config/api_cost_1000.json', 'r') as file:
        pricing = json.load(file)
    
    # Attempt to find the best match for the model name
    closest_match = difflib.get_close_matches(model_name, pricing.keys(), n=1, cutoff=0.5)
    
    if not closest_match:
        # If no close match is found, return cost -1
        logger.error("Model price not found.")
        return -1

    # Use the best match to calculate the cost
    matched_model = closest_match[0]
    input_cost = pricing[matched_model]["input"] * input_token_estimation / 1000
    output_cost = pricing[matched_model]["output"] * output_token_estimation / 1000
    total_cost = input_cost + output_cost

    logger.info(f"Cost for {model_name} with {input_token_estimation//1000}k input tokens ({pricing[matched_model]['input']}/1k tokens) and {output_token_estimation//1000}k output tokens ({pricing[matched_model]['output']}/1k tokens) for {sample_space_size} agents: ${total_cost:.5f}")

    return total_cost
