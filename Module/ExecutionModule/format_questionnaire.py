few_shot_learning_template = {
    "reasoning": "The response should consist of two elements. The first element explains the reasoning behind your answer, and the second element contains the answer. Answer in a list."
}

def add_few_shot_learning(processed_data, few_shot_dict: dict = {}):
    if few_shot_dict == {}: return processed_data

    for question_id, few_shot_content in few_shot_dict.items():
        question_id = str(question_id)
        processed_data[question_id]["few_shot_content"] = few_shot_content
    
    return processed_data

def format_single_question(processed_data, question_id, output_max_token = 256):
    if str(question_id) in processed_data.keys():
        question_data = processed_data[str(question_id)]
    else: return f"{str(question_id)}. SKIP THIS QUESTION", 0
    
    # Initialize dictionary to store formatted parts
    question_parts = {
        "id": f"{question_id}",
        "question": question_data["question"],
        "type": "",
        "options": "",
        "extra_info": "",
        "few_shot_content": ""
    }

    if "few_shot_content" in question_data.keys():
        question_parts["few_shot_content"] = question_data["few_shot_content"]

    if question_data["type"] == 'single_choice':
        question_parts["type"] += " (single choice)"
        question_parts["options"] = ', '.join(question_data['options'])
        formatted_output_length = len(question_parts["options"]) // len(question_data['options'])
    elif question_data["type"] == 'multiple_choice':
        if 'table_structure' in question_data.keys():
            question_parts["type"] += " (rating)"
            question_parts["options"] = "\n".join(
                [f"{question_id}-{index + 1}: {dimension} - {', '.join(question_data['table_structure']['options'])}"
                for index, dimension in enumerate(question_data['table_structure']['dimensions'])]
            )
            formatted_output_length = sum(
                len(', '.join(question_data['table_structure']['options'])) // len(question_data['table_structure']['options'])
                for _ in question_data['table_structure']['dimensions']
            )
        else:
            question_parts["type"] += " (multiple choice)"
            question_parts["options"] = ', '.join(question_data['options'])
            formatted_output_length = len(question_parts["options"]) // 2
    elif question_data["type"] == 'rating':
        question_parts["type"] += " (rating)"
        question_parts["extra_info"] = f"Rate from {question_data['scale'][0]} to {question_data['scale'][1]} with a step of {question_data['scale'][2]}"
        formatted_output_length = len(str(question_data['scale'][1])) // 2
    elif question_data["type"] == 'text_response':
        question_parts["type"] += " (text)"
        question_parts["extra_info"] = "Present your idea briefly."
        formatted_output_length = int(output_max_token / 4 * 3)
    elif question_data["type"] == 'table_rating':
        if 'table_structure' in question_data.keys():
            question_parts["type"] += " (rating)"
            question_parts["options"] = "\n".join(
                [f"{question_id}-{index + 1}: {dimension} - {', '.join(question_data['table_structure']['options'])}"
                for index, dimension in enumerate(question_data['table_structure']['dimensions'])]
            )
            formatted_output_length = sum(
                len(', '.join(question_data['table_structure']['options'])) // len(question_data['table_structure']['options'])
                for _ in question_data['table_structure']['dimensions']
            )
        else:
            question_parts["type"] += " (rating)"
            question_parts["options"] = " ".join(question_data['options'])
            formatted_output_length = len(question_parts["options"]) // 2
    
    # Unified format method
    formatted_question_parts = [
        f"{question_parts['id']}. {question_parts['question']} {question_parts['type']}"
    ]
    if question_parts['options']:
        formatted_question_parts.append(f"{question_parts['options']}")
    if question_parts['extra_info']:
        formatted_question_parts.append(f"{question_parts['extra_info']}")
    if question_parts['few_shot_content']:
        formatted_question_parts.append(f"{question_parts['few_shot_content']}")
    formatted_question = "\n".join(formatted_question_parts) + "\n"
    
    return formatted_question, formatted_output_length

def format_full_question(processed_data, output_max_token = 256):
    full_question_list = ""
    full_output_length = 0

    for question_id in range(1, len(processed_data) + 1):
        formatted_question, formatted_output_length = format_single_question(processed_data, question_id, output_max_token)
        full_question_list += formatted_question + '\n'
        full_output_length += formatted_output_length
    
    return full_question_list, full_output_length

def format_range_question(processed_data, question_ids, output_max_token = 256):
    full_question_list = ""

    for question_id in question_ids:
        formatted_question = format_single_question(processed_data, question_id, output_max_token)[0]
        full_question_list += formatted_question + '\n'
    
    return full_question_list
