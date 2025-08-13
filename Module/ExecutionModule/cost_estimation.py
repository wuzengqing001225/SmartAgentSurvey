import json
import difflib
import re
from Module.ExecutionModule.format_questionnaire import format_full_question
from Module.ExecutionModule.smart_model_matcher import (
    get_claude_api_model_name,
    get_openai_encoding_for_model,
    get_openai_message_tokens_overhead
)
from UtilityFunctions import json_processing
import tiktoken
import anthropic
import os
from typing import Optional, Tuple, Dict, Any



def _estimate_claude_tokens_with_api(messages: list, model_name: str, system_prompt: str = "", llm_client=None) -> Optional[int]:
    """
    Use Claude's official token counting API for accurate input token estimation.

    Args:
        messages: List of message dictionaries
        model_name: Claude model name
        system_prompt: System prompt string
        llm_client: Existing LLM client instance (optional)

    Returns:
        int: Accurate input token count, or None if API call fails
    """
    try:
        # Use existing client if provided, otherwise create new one
        if llm_client is not None:
            client = llm_client
        else:
            # Fallback: check if ANTHROPIC_API_KEY is available
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return None
            client = anthropic.Anthropic(api_key=api_key)

        # Intelligently match API model name
        api_model = get_claude_api_model_name(model_name)

        # Prepare request parameters
        request_params = {
            "model": api_model,
            "messages": messages
        }

        if system_prompt:
            request_params["system"] = system_prompt

        # Call token counting API
        response = client.messages.count_tokens(**request_params)
        return response.input_tokens

    except anthropic.APIError as e:
        # Handle specific API errors silently for estimation fallback
        return None
    except Exception as e:
        # Handle other errors silently for estimation fallback
        return None


def _estimate_openai_tokens_with_tiktoken(messages: list, model_name: str, system_prompt: str = "") -> int:
    """
    Use tiktoken for accurate OpenAI token counting with proper message formatting.

    Args:
        messages: List of message dictionaries
        model_name: OpenAI model name
        system_prompt: System prompt string

    Returns:
        int: Accurate input token count
    """
    # Intelligently get encoding
    encoding = get_openai_encoding_for_model(model_name)

    # Prepare messages for token counting
    formatted_messages = []
    if system_prompt:
        formatted_messages.append({"role": "system", "content": system_prompt})
    formatted_messages.extend(messages)

    # Get model-specific message overhead
    tokens_per_message, tokens_per_name = get_openai_message_tokens_overhead(model_name)

    num_tokens = 0
    for message in formatted_messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(str(value)))
            if key == "name":
                num_tokens += tokens_per_name

    # Every reply is primed with assistant message
    num_tokens += 3

    return num_tokens


def _estimate_claude_output_tokens(full_output_length: int, sample_space_size: int, model_name: str) -> int:
    """
    Estimate Claude output tokens more accurately based on response patterns.

    Args:
        full_output_length: Expected character length of output per sample
        sample_space_size: Number of samples
        model_name: Claude model name

    Returns:
        int: Estimated output tokens
    """
    # Claude models have different token densities
    if "haiku" in model_name.lower():
        chars_per_token = 3.8  # Haiku is more efficient
    elif "sonnet" in model_name.lower():
        chars_per_token = 4.0  # Standard efficiency
    elif "opus" in model_name.lower():
        chars_per_token = 4.2  # Slightly less efficient but more thoughtful
    else:
        chars_per_token = 4.0  # Default

    # Base output tokens per sample
    base_output_tokens = int(full_output_length / chars_per_token)

    # Add JSON formatting overhead (brackets, quotes, commas, etc.)
    json_overhead_per_sample = max(50, int(base_output_tokens * 0.15))

    # Total output tokens
    total_output_tokens = (base_output_tokens + json_overhead_per_sample) * sample_space_size

    # Add response wrapper overhead
    wrapper_overhead = 100  # For response structure

    return total_output_tokens + wrapper_overhead


def _estimate_openai_output_tokens(full_output_length: int, sample_space_size: int, model_name: str) -> int:
    """
    Estimate OpenAI output tokens using tiktoken for better accuracy.

    Args:
        full_output_length: Expected character length of output per sample
        sample_space_size: Number of samples
        model_name: OpenAI model name

    Returns:
        int: Estimated output tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # Create a sample output to estimate token density
    sample_output = "A" * min(full_output_length, 1000)  # Limit sample size for efficiency
    sample_tokens = len(encoding.encode(sample_output))

    if len(sample_output) > 0:
        chars_per_token = len(sample_output) / sample_tokens
    else:
        chars_per_token = 4.0  # Fallback

    # Base output tokens per sample
    base_output_tokens = int(full_output_length / chars_per_token)

    # Add JSON formatting overhead
    json_overhead_per_sample = max(30, int(base_output_tokens * 0.12))

    # Total output tokens
    total_output_tokens = (base_output_tokens + json_overhead_per_sample) * sample_space_size

    # Add response wrapper overhead
    wrapper_overhead = 80

    return total_output_tokens + wrapper_overhead


def token_consumption_estimation(processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256, model_name="gpt-4o", llm_client=None):
    """
    Enhanced token consumption estimation with improved accuracy for both Claude and OpenAI models.

    Args:
        processed_data: Processed questionnaire data
        question_segments: Number of question segments
        sample_space_size: Total number of sample profiles
        sample_profile_0: Sample profile string for token estimation
        output_max_token: Maximum output tokens per response
        model_name: LLM model name
        llm_client: Existing LLM client instance (optional)

    Returns:
        tuple: (input_token_estimation, output_token_estimation)
    """
    full_question_list, full_output_length = format_full_question(processed_data, output_max_token)

    # Estimate system prompts based on typical survey system prompts
    system_prompt = f"""You are an AI assistant helping with survey responses. You will receive a survey questionnaire and a respondent profile. Please answer each question based on the profile characteristics provided.

Survey Instructions:
- Answer all questions honestly based on the given profile
- Provide responses in the specified format
- For rating questions, use the provided scale
- For multiple choice, select appropriate options
- For text responses, be concise but informative

Profile-based Response Guidelines:
- Consider the respondent's background, demographics, and characteristics
- Ensure consistency across all responses
- Reflect realistic human response patterns

Please format your responses as JSON with question IDs as keys."""

    if "claude" in model_name.lower():
        # Enhanced Claude token estimation

        # Prepare sample messages for token counting
        sample_messages = [
            {
                "role": "user",
                "content": f"Profile: {sample_profile_0}\n\nSurvey Questions:\n{full_question_list}"
            }
        ]

        # Try to use Claude's official token counting API
        api_input_tokens = _estimate_claude_tokens_with_api(sample_messages, model_name, system_prompt, llm_client)

        if api_input_tokens is not None:
            # Use API result and scale for all samples and segments
            input_tokens_per_sample = api_input_tokens * question_segments
            input_token_estimation = input_tokens_per_sample * sample_space_size
        else:
            # Fallback to improved character-based estimation
            base_content = system_prompt + full_question_list + sample_profile_0

            # More accurate character-to-token ratio for Claude
            if "haiku" in model_name.lower():
                chars_per_token = 3.8
            elif "sonnet" in model_name.lower():
                chars_per_token = 4.0
            elif "opus" in model_name.lower():
                chars_per_token = 4.2
            else:
                chars_per_token = 4.0

            base_tokens = int(len(base_content) / chars_per_token)

            # Add message formatting overhead
            message_overhead = 50  # For message structure, role indicators, etc.

            input_tokens_per_sample = (base_tokens + message_overhead) * question_segments
            input_token_estimation = input_tokens_per_sample * sample_space_size

        # Enhanced output token estimation for Claude
        output_token_estimation = _estimate_claude_output_tokens(
            full_output_length, sample_space_size, model_name
        )

    else:
        # Enhanced OpenAI token estimation

        # Prepare sample messages for accurate token counting
        sample_messages = [
            {
                "role": "user",
                "content": f"Profile: {sample_profile_0}\n\nSurvey Questions:\n{full_question_list}"
            }
        ]

        # Use tiktoken for accurate input token counting
        input_tokens_per_sample = _estimate_openai_tokens_with_tiktoken(
            sample_messages, model_name, system_prompt
        ) * question_segments

        input_token_estimation = input_tokens_per_sample * sample_space_size

        # Enhanced output token estimation for OpenAI
        output_token_estimation = _estimate_openai_output_tokens(
            full_output_length, sample_space_size, model_name
        )

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
        processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token, model_name, llm_client
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

