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


def get_token_estimation_details(processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256, model_name="gpt-4o", llm_client=None):
    """
    Get detailed token estimation breakdown for analysis and debugging.

    Args:
        processed_data: Processed questionnaire data
        question_segments: Number of question segments
        sample_space_size: Total number of sample profiles
        sample_profile_0: Sample profile string for token estimation
        output_max_token: Maximum output tokens per response
        model_name: LLM model name
        llm_client: Existing LLM client instance (optional)

    Returns:
        dict: Detailed breakdown of token estimation components
    """
    full_question_list, full_output_length = format_full_question(processed_data, output_max_token)

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

    details = {
        "model_name": model_name,
        "estimation_method": "",
        "input_components": {},
        "output_components": {},
        "sample_data": {
            "question_list_length": len(full_question_list),
            "profile_length": len(sample_profile_0),
            "system_prompt_length": len(system_prompt),
            "expected_output_length": full_output_length,
            "question_segments": question_segments,
            "sample_space_size": sample_space_size
        }
    }

    if "claude" in model_name.lower():
        details["estimation_method"] = "Claude API + Fallback Character-based"

        # Try API estimation first
        sample_messages = [
            {
                "role": "user",
                "content": f"Profile: {sample_profile_0}\n\nSurvey Questions:\n{full_question_list}"
            }
        ]

        api_tokens = _estimate_claude_tokens_with_api(sample_messages, model_name, system_prompt, llm_client)

        if api_tokens is not None:
            details["input_components"] = {
                "api_tokens_per_sample": api_tokens,
                "total_segments": question_segments,
                "total_samples": sample_space_size,
                "total_input_tokens": api_tokens * question_segments * sample_space_size,
                "estimation_source": "Claude Token Counting API"
            }
        else:
            # Fallback estimation details
            base_content = system_prompt + full_question_list + sample_profile_0
            chars_per_token = 4.0 if "sonnet" in model_name.lower() else (3.8 if "haiku" in model_name.lower() else 4.2)
            base_tokens = int(len(base_content) / chars_per_token)
            message_overhead = 50

            details["input_components"] = {
                "base_content_chars": len(base_content),
                "chars_per_token": chars_per_token,
                "base_tokens": base_tokens,
                "message_overhead": message_overhead,
                "tokens_per_sample": (base_tokens + message_overhead) * question_segments,
                "total_input_tokens": (base_tokens + message_overhead) * question_segments * sample_space_size,
                "estimation_source": "Character-based Fallback"
            }

        # Output estimation details
        chars_per_token = 4.0 if "sonnet" in model_name.lower() else (3.8 if "haiku" in model_name.lower() else 4.2)
        base_output_tokens = int(full_output_length / chars_per_token)
        json_overhead = max(50, int(base_output_tokens * 0.15))
        wrapper_overhead = 100

        details["output_components"] = {
            "base_output_chars": full_output_length,
            "chars_per_token": chars_per_token,
            "base_output_tokens": base_output_tokens,
            "json_overhead_per_sample": json_overhead,
            "wrapper_overhead": wrapper_overhead,
            "tokens_per_sample": base_output_tokens + json_overhead,
            "total_output_tokens": (base_output_tokens + json_overhead) * sample_space_size + wrapper_overhead
        }

    else:
        details["estimation_method"] = "Tiktoken with Message Formatting"

        # OpenAI estimation details
        sample_messages = [
            {
                "role": "user",
                "content": f"Profile: {sample_profile_0}\n\nSurvey Questions:\n{full_question_list}"
            }
        ]

        tokens_per_sample = _estimate_openai_tokens_with_tiktoken(sample_messages, model_name, system_prompt)

        details["input_components"] = {
            "tokens_per_sample_per_segment": tokens_per_sample,
            "total_segments": question_segments,
            "total_samples": sample_space_size,
            "total_input_tokens": tokens_per_sample * question_segments * sample_space_size,
            "estimation_source": "Tiktoken with Message Formatting"
        }

        # Output estimation details
        try:
            encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        sample_output = "A" * min(full_output_length, 1000)
        sample_tokens = len(encoding.encode(sample_output)) if len(sample_output) > 0 else 1
        chars_per_token = len(sample_output) / sample_tokens if len(sample_output) > 0 else 4.0

        base_output_tokens = int(full_output_length / chars_per_token)
        json_overhead = max(30, int(base_output_tokens * 0.12))
        wrapper_overhead = 80

        details["output_components"] = {
            "base_output_chars": full_output_length,
            "chars_per_token": chars_per_token,
            "base_output_tokens": base_output_tokens,
            "json_overhead_per_sample": json_overhead,
            "wrapper_overhead": wrapper_overhead,
            "tokens_per_sample": base_output_tokens + json_overhead,
            "total_output_tokens": (base_output_tokens + json_overhead) * sample_space_size + wrapper_overhead
        }

    return details


def get_detailed_cost_breakdown(config_set, processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token = 256):
    """
    Get detailed cost breakdown for analysis and debugging with enhanced token estimation details.

    Returns:
        dict: Detailed breakdown of cost components including token estimation details
    """
    config, llm_client, logger, output_manager = config_set
    model_name = json_processing.get_json_nested_value(config, "llm_settings.model")

    if not model_name:
        return {"error": "Model name not found in configuration"}

    # Get enhanced token estimations
    input_tokens, output_tokens = token_consumption_estimation(
        processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token, model_name, llm_client
    )

    # Get detailed token estimation breakdown
    token_details = get_token_estimation_details(
        processed_data, question_segments, sample_space_size, sample_profile_0, output_max_token, model_name, llm_client
    )

    # Load pricing
    try:
        with open('./Config/api_cost_1000.json', 'r') as file:
            pricing = json.load(file)
    except Exception as e:
        return {"error": f"Failed to load pricing: {e}"}

    # Find model pricing with improved matching
    matched_model = None
    normalized_model_name = model_name.lower().strip()

    # Try exact match first
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
            cutoff=0.6
        )
        if closest_matches:
            for price_model in pricing.keys():
                if price_model.lower() == closest_matches[0]:
                    matched_model = price_model
                    break

    if not matched_model:
        return {"error": f"Model pricing not found for '{model_name}'. Available models: {list(pricing.keys())}"}

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
            "output_per_sample": output_tokens // sample_space_size if sample_space_size > 0 else 0,
            "input_per_sample_per_segment": input_tokens // (sample_space_size * question_segments) if sample_space_size > 0 and question_segments > 0 else 0,
        },
        "token_estimation_details": token_details,
        "pricing": {
            "input_per_1k": input_price,
            "output_per_1k": output_price
        },
        "costs": {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
            "cost_per_sample": (input_cost + output_cost) / sample_space_size if sample_space_size > 0 else 0,
            "cost_per_1k_input_tokens": input_price,
            "cost_per_1k_output_tokens": output_price
        },
        "efficiency_metrics": {
            "cost_per_question": (input_cost + output_cost) / len(processed_data) if len(processed_data) > 0 else 0,
            "tokens_per_question": (input_tokens + output_tokens) / len(processed_data) if len(processed_data) > 0 else 0,
            "input_output_ratio": input_tokens / output_tokens if output_tokens > 0 else 0
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