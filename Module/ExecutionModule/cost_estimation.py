import json
import difflib
from Module.ExecutionModule.format_questionnaire import format_full_question
from UtilityFunctions import json_processing
import tiktoken

def token_consumption_estimation(processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256, model_name="gpt-4o"):
    """
    Estimate token consumption for LLM API calls.

    Args:
        processed_data: Processed questionnaire data
        question_segments: Number of question segments
        sample_space_size: Total number of sample profiles
        sample_profile_0: Sample profile string for token estimation
        output_max_token: Maximum output tokens per response
        model_name: LLM model name

    Returns:
        tuple: (input_token_estimation, output_token_estimation)
    """
    full_question_list, full_output_length = format_full_question(processed_data, output_max_token)

    if "claude" in model_name.lower():
        # Claude models: Use character-based estimation (4 chars ≈ 1 token)
        # Base input: questionnaire + profile per sample
        base_input_chars = len(full_question_list) + len(sample_profile_0)
        input_chars_per_sample = base_input_chars * question_segments
        total_input_chars = input_chars_per_sample * sample_space_size

        # System prompts overhead (estimated based on your system)
        system_prompt_chars = 1590 + 1728 + len(full_question_list)
        total_input_chars += system_prompt_chars

        # Output estimation
        output_chars_per_sample = full_output_length
        total_output_chars = output_chars_per_sample * sample_space_size

        # Add output system prompt overhead
        output_system_chars = 1024 + int(len(full_question_list) * 1.2)
        total_output_chars += output_system_chars

        # Convert to tokens (Claude: ~4 chars per token)
        input_token_estimation = total_input_chars // 4
        output_token_estimation = total_output_chars // 4

    else:
        # OpenAI models: Use tiktoken for accurate token counting
        try:
            encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to gpt-4 encoding if model not found
            encoding = tiktoken.encoding_for_model("gpt-4")

        # Base tokens: questionnaire + profile
        base_question_tokens = len(encoding.encode(full_question_list))
        profile_tokens = len(encoding.encode(sample_profile_0))

        # Input tokens per sample (questionnaire + profile) * segments
        input_tokens_per_sample = (base_question_tokens + profile_tokens) * question_segments
        total_input_tokens = input_tokens_per_sample * sample_space_size

        # System prompt overhead (convert char estimates to tokens)
        system_prompt_text = "System prompt overhead estimation"  # Placeholder
        system_prompt_tokens = len(encoding.encode(system_prompt_text)) + base_question_tokens // 10
        total_input_tokens += system_prompt_tokens + 400  # Conservative estimate for system prompts

        # Output tokens
        output_tokens_per_sample = full_output_length
        total_output_tokens = output_tokens_per_sample * sample_space_size

        # Output system overhead
        total_output_tokens += 256  # Conservative estimate for output formatting

        input_token_estimation = total_input_tokens
        output_token_estimation = total_output_tokens

    return input_token_estimation, output_token_estimation


def cost_estimation(config_set, processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256):
    """
    Calculate the estimated cost for LLM API calls.

    Args:
        config_set: Configuration tuple (config, llm_client, logger, output_manager)
        processed_data: Processed questionnaire data
        question_segments: Number of question segments
        sample_space_size: Total number of sample profiles
        sample_profile_0: Sample profile string for token estimation
        output_max_token: Maximum output tokens per response

    Returns:
        float: Estimated total cost in USD, or -1 if model pricing not found
    """
    config, llm_client, logger, output_manager = config_set
    model_name = json_processing.get_json_nested_value(config, "llm_settings.model")

    if not model_name:
        logger.error("Model name not found in configuration")
        return -1

    # Get token estimations
    input_token_estimation, output_token_estimation = token_consumption_estimation(
        processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token, model_name
    )

    # Load pricing data from JSON
    try:
        with open('./Config/api_cost_1000.json', 'r') as file:
            pricing = json.load(file)
    except FileNotFoundError:
        logger.error("Pricing configuration file not found: ./Config/api_cost_1000.json")
        return -1
    except json.JSONDecodeError:
        logger.error("Invalid JSON in pricing configuration file")
        return -1

    # Normalize model name for better matching
    normalized_model_name = model_name.lower().strip()

    # Try exact match first
    matched_model = None
    for price_model in pricing.keys():
        if normalized_model_name == price_model.lower():
            matched_model = price_model
            break

    # If no exact match, try fuzzy matching
    if not matched_model:
        closest_matches = difflib.get_close_matches(
            normalized_model_name,
            [k.lower() for k in pricing.keys()],
            n=1,
            cutoff=0.6  # Increased cutoff for better accuracy
        )

        if closest_matches:
            # Find the original key that matches the lowercase version
            for price_model in pricing.keys():
                if price_model.lower() == closest_matches[0]:
                    matched_model = price_model
                    break

    if not matched_model:
        logger.error(f"Model pricing not found for '{model_name}'. Available models: {list(pricing.keys())}")
        return -1

    # Validate pricing structure
    if "input" not in pricing[matched_model] or "output" not in pricing[matched_model]:
        logger.error(f"Invalid pricing structure for model '{matched_model}'")
        return -1

    # Calculate costs
    try:
        input_price_per_1k = pricing[matched_model]["input"]
        output_price_per_1k = pricing[matched_model]["output"]

        input_cost = (input_price_per_1k * input_token_estimation) / 1000
        output_cost = (output_price_per_1k * output_token_estimation) / 1000
        total_cost = input_cost + output_cost

        # Enhanced logging with more details
        logger.info(
            f"Cost estimation for {model_name} (matched: {matched_model}):\n"
            f"  - Input: {input_token_estimation:,} tokens @ ${input_price_per_1k}/1k = ${input_cost:.6f}\n"
            f"  - Output: {output_token_estimation:,} tokens @ ${output_price_per_1k}/1k = ${output_cost:.6f}\n"
            f"  - Total cost for {sample_space_size} agents: ${total_cost:.6f}"
        )

        return total_cost

    except (TypeError, ValueError) as e:
        logger.error(f"Error calculating cost: {e}")
        return -1


def get_detailed_cost_breakdown(config_set, processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256):
    """
    Get detailed cost breakdown for analysis and debugging.

    Returns:
        dict: Detailed breakdown of cost components
    """
    config, llm_client, logger, output_manager = config_set
    model_name = json_processing.get_json_nested_value(config, "llm_settings.model")

    if not model_name:
        return {"error": "Model name not found in configuration"}

    # Get token estimations
    input_tokens, output_tokens = token_consumption_estimation(
        processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token, model_name
    )

    # Load pricing
    try:
        with open('./Config/api_cost_1000.json', 'r') as file:
            pricing = json.load(file)
    except Exception as e:
        return {"error": f"Failed to load pricing: {e}"}

    # Find model pricing
    matched_model = None
    for price_model in pricing.keys():
        if model_name.lower() == price_model.lower():
            matched_model = price_model
            break

    if not matched_model:
        closest_matches = difflib.get_close_matches(model_name.lower(), [k.lower() for k in pricing.keys()], n=1, cutoff=0.6)
        if closest_matches:
            for price_model in pricing.keys():
                if price_model.lower() == closest_matches[0]:
                    matched_model = price_model
                    break

    if not matched_model:
        return {"error": f"Model pricing not found for '{model_name}'"}

    input_price = pricing[matched_model]["input"]
    output_price = pricing[matched_model]["output"]
    input_cost = (input_price * input_tokens) / 1000
    output_cost = (output_price * output_tokens) / 1000

    return {
        "model_name": model_name,
        "matched_model": matched_model,
        "sample_space_size": sample_space_size,
        "question_segments": question_segments,
        "tokens": {
            "input_total": input_tokens,
            "output_total": output_tokens,
            "input_per_sample": input_tokens // sample_space_size if sample_space_size > 0 else 0,
            "output_per_sample": output_tokens // sample_space_size if sample_space_size > 0 else 0
        },
        "pricing": {
            "input_per_1k": input_price,
            "output_per_1k": output_price
        },
        "costs": {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
            "cost_per_sample": (input_cost + output_cost) / sample_space_size if sample_space_size > 0 else 0
        }
    }


def validate_cost_estimation_inputs(processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token):
    """
    Validate inputs for cost estimation to catch potential issues early.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not processed_data:
        return False, "processed_data is empty or None"

    if not isinstance(question_segments, int) or question_segments <= 0:
        return False, f"question_segments must be a positive integer, got: {question_segments}"

    if not isinstance(sample_space_size, int) or sample_space_size <= 0:
        return False, f"sample_space_size must be a positive integer, got: {sample_space_size}"

    if not sample_profile_0 or not isinstance(sample_profile_0, str):
        return False, f"sample_profile_0 must be a non-empty string, got: {type(sample_profile_0)}"

    if not isinstance(output_max_token, int) or output_max_token <= 0:
        return False, f"output_max_token must be a positive integer, got: {output_max_token}"

    return True, "All inputs are valid"