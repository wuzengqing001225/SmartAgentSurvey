from typing import List, Dict, Any, Optional, Tuple
import re

def parse_table_content(content: List[str]) -> Optional[Tuple[List[str], List[str]]]:
    """Parse table content to extract options and dimensions."""
    if not content or len(content) < 2:
        return None

    try:
        # First line contains options
        options = [opt.strip() for opt in content[0].split('\t') if opt.strip()]

        # Following lines contain dimensions
        dimensions = []
        for line in content[1:]:
            dim_match = re.match(r'([^*_]+)', line.strip())
            if dim_match:
                dimensions.append(dim_match.group(1).strip())

        return options, dimensions
    except Exception as e:
        # logger.error(f"Error parsing table content: {str(e)}")
        return None

def extract_raw_questions(text: str) -> List[Dict[str, Any]]:
    """Extract initial question structures from text."""
    questions = []
    current_question = None
    in_table = False
    table_content = []

    for line in text.split('\n'):
        if 'TABLE START' in line:
            in_table = True
            table_content = []
            continue
        elif 'TABLE END' in line:
            if current_question:
                table_structure = parse_table_content(table_content)
                if table_structure:
                    options, dimensions = table_structure
                    current_question['table_structure'] = {
                        'options': options,
                        'dimensions': dimensions
                    }
            in_table = False
            continue

        match = re.match(r'(\d+)\.\s*(.*)', line)
        if match:
            if current_question:
                questions.append(current_question)

            current_question = {
                'number': int(match.group(1)),
                'text': match.group(2).strip(),
                'options': []
            }
        elif current_question and line.strip():
            if in_table:
                table_content.append(line.strip())
            else:
                current_question['options'].append(line.strip())

    if current_question:
        questions.append(current_question)

    return questions

def create_batch_prompt(questions) -> str:
    # question_sequence = "\n".join([
    #     f"Q{q['number']}: {q['text']}"
    #     for q in sorted(questions, key=lambda x: x['number'])
    # ])

    # questions_text = "\n\n".join([
    #     f"Question {q['number']}: {q['text']}" +
    #     (f"\nOptions: {', '.join(q['options'])}" if q.get('options') else "")
    #     for q in questions
    # ])

    questions_text = questions

    return f"""Analyze these survey questions as part of a complete flow and return a JSON object mapping question numbers to their analysis.
For each question, determine:

1. Question Type:
- single_choice: One option from multiple choices
- multiple_choice: Multiple options can be selected
- rating: Numerical rating or scale. For questions identified as rating, e.g., "on a scale of / rating from X to Y", add a new property of scale: [X, Y, step] other than options, e.g., [1, 5, 1] means 1, 2, 3, 4, 5
- text_response: Free text answer
- table_rating: Table of ratings
- image_description: For every image that is referenced or required to answer a question, provide a detailed and comprehensive description of the image in English, so that a person can answer the question without seeing the original image.
If a question is presented in a table, use table_rating instead of multiple_choice or single_choice. However, if no dim found for a table_structure question, classify it as a single_choice or multiple_choice question.

2. Jump Logic (Important):
- Analyze explicit jumps (e.g., "... go to question X")
- For branch points, determine where each branch should continue to
- For questions reached by branches, identify their next logical target
- Format as {{condition: target_number}} for conditional jumps
- Use {{"next": target_number}} for direct flow to next question
- Consider the overall survey flow when determining targets

3. Include raw questions, options, scale and table_structure with options and dimensions (if applicable).

For branching questions, understand the full branch structure

Questions to analyze:
{questions_text}

Return a JSON object with question numbers as keys. Example format:
{{
    "40": {{
        "question": "...",
        "type": "rating",
        "jump_logic": {{"next": 41}},
        "options": [],
        "scale": [1, 5, 1]
    }},
    ...
    "109": {{
        "question": "...",
        "type": "single_choice",
        "jump_logic": {{"X": 110, "Y": 111}},
        "options": ["X", "Y"]
    }},
    "110": {{
        "question": "...",
        "type": "table_rating",
        "jump_logic": {{"next": 112}},
        "table_structure": {{
            "options": ['Not very', 'Neutral', 'Very'],
            "dimensions": ['Issue A', 'Issue B']
        }}
    }}
    ...
}}

Analyze the complete question flow to ensure proper survey navigation. Be careful with the JSON format."""

def create_batch_prompt_multimodal() -> str:
    return f"""Analyze the survey questionnaire pdf file as part of a complete flow and return a JSON object mapping question numbers to their analysis.
For each question, determine:

1. Question Type:
- single_choice: One option from multiple choices
- multiple_choice: Multiple options can be selected
- rating: Numerical rating or scale. For questions identified as rating, e.g., "on a scale of / rating from X to Y", add a new property of scale: [X, Y, step] other than options, e.g., [1, 5, 1] means 1, 2, 3, 4, 5
- text_response: Free text answer
- table_rating: Table of ratings
- image_description: For every image that is referenced or required to answer a question, provide a detailed and comprehensive description of the image in English, so that a person can answer the question without seeing the original image. If no image involved, do not use the property.
If a question is presented in a table, use table_rating instead of multiple_choice or single_choice. However, if no dim found for a table_structure question, classify it as a single_choice or multiple_choice question.

2. Jump Logic (Important):
- Analyze explicit jumps (e.g., "... go to question X")
- For branch points, determine where each branch should continue to
- For questions reached by branches, identify their next logical target
- Format as {{condition: target_number}} for conditional jumps
- Use {{"next": target_number}} for direct flow to next question
- Consider the overall survey flow when determining targets

3. Include raw questions, options, scale and table_structure with options and dimensions (if applicable).

For branching questions, understand the full branch structure

Return a JSON object with question numbers as keys. Example format:
{{
    "40": {{
        "question": "...",
        "type": "rating",
        "jump_logic": {{"next": 41}},
        "options": [],
        "scale": [1, 5, 1],
        "image_description": "The image displays four options for a logo design, all with the word 'aila'. Option 1 is 'aila' in red text on a white background. Option 2 has 'aila' in red text on a black rectangular background. Option 3 shows 'aila' in black text on a white background. Option 4 features 'aila' in white text on a black rectangular background."
    }},
    ...
    "109": {{
        "question": "...",
        "type": "single_choice",
        "jump_logic": {{"X": 110, "Y": 111}},
        "options": ["X", "Y"]
    }},
    "110": {{
        "question": "...",
        "type": "table_rating",
        "jump_logic": {{"next": 112}},
        "table_structure": {{
            "options": ['Not very', 'Neutral', 'Very'],
            "dimensions": ['Issue A', 'Issue B']
        }}
    }}
    ...
}}

Analyze the complete question flow to ensure proper survey navigation. Be careful with the JSON format."""


def merge_survey_data(structure_json, questions_list):
    merged_data = {}

    questions_dict = {q['number']: q for q in questions_list}

    for key, value in structure_json.items():
        question_num = int(key)
        question_data = questions_dict.get(question_num, {})

        merged_item = {
            'question': question_data.get('text', ''),
            'type': value.get('type', ''),
            'jump_logic': value.get('jump_logic', ''),
        }

        options = question_data.get('options', value.get('options', []))
        if options:
            merged_item['options'] = options

        for attr in ['table_structure', 'scale', 'additional_info']:
            if attr in question_data:
                merged_item[attr] = question_data[attr]
            elif attr in value:
                merged_item[attr] = value[attr]

        merged_data[str(question_num)] = merged_item

    return merged_data
