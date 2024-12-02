import json
from UtilityFunctions import json_processing
from Module.ExecutionModule.format_questionnaire import format_range_question, format_full_question
import Module.SampleGenerationModule.flow

def find_all_by_first_element(nested_list, target):
    matches = []
    for sublist in nested_list:
        if sublist[0] == target:
            matches.append(sublist)
    return matches

def fuzzy_match(condition_list, answer):
    if answer == None: return None, 2
    
    processed_conditions = [cond[1].strip().lower() for cond in condition_list]
    processed_answer = answer.strip().lower()

    if processed_answer in processed_conditions:
        matched_index = processed_conditions.index(processed_answer)
        return condition_list[matched_index], 0

    for cond in processed_conditions:
        if processed_answer in cond or cond in processed_answer:
            matched_index = processed_conditions.index(cond)
            return condition_list[matched_index], 1

    return None, 2

def merge_dicts_in_lexicographical_order(dict1, dict2):
    merged_dict = {**dict1, **dict2}
    sorted_dict = dict(sorted(merged_dict.items()))
    return sorted_dict

def questionnaire_iterator_segment(config_set, processed_data, question_segments, execution_order, sample_space, sample_space_size, sample_dimensions, upload = False, progress_file=None):
    config, llm_client, logger, output_manager = config_set
    survey_size = len(processed_data)
    answers = {}
    errors = {}
    
    for agent_id in range(sample_space_size):
        # Update progress
        if progress_file:
            progress = agent_id  * 100 / sample_space_size
            with open(progress_file, 'w') as f:
                json.dump({'progress': progress}, f)

        if not upload:
            sample_profile = Module.SampleGenerationModule.flow.format_single_profile(sample_space[agent_id], sample_dimensions)
        else:
            sample_profile = sample_space[agent_id]
        
        answer = {}
        current_question = 1
        errors[agent_id + 1] = []

        while current_question <= survey_size:
            question_segment = find_all_by_first_element(question_segments, current_question)

            if len(question_segment) == 1:
                segment = question_segment[0]
                questions = format_range_question(processed_data, segment[2], json_processing.get_json_nested_value(config, "llm_settings.max_tokens"))
            
            elif len(question_segment) > 1:
                segment, match_status = fuzzy_match(question_segment, answer.get(str(current_question)))
                
                if match_status == 1:
                    errors[agent_id + 1].append(f"Jump condition imperfect match at question {str(current_question)}")
                elif match_status == 2:
                    errors[agent_id + 1].append(f"Jump condition not match at question {str(current_question)}")
                    logger.error(f"Jump condition not match.")
                    segment = question_segment[0]
                
                questions = format_range_question(processed_data, segment[2], json_processing.get_json_nested_value(config, "llm_settings.max_tokens"))
            
            elif len(question_segment) == 0:
                logger.error(f"Question not found.")
                        
            answer_text = llm_client.generate(
                prompt=f"""{execution_order}\n{questions}""",
                system_prompt=f"""You act as a survey participant with the following profile: {sample_profile}\nThe output format should be in JSON, with each value structured as "question number: answer".  Do not place ```json at the beginning."""
            )

            try:
                answer_dict = json.loads(answer_text)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format: {e}")
        
            answer = merge_dicts_in_lexicographical_order(answer, answer_dict)

            if segment[2][-1] != 1 and segment[2][-1] == current_question: break
            current_question = segment[2][-1]

        answers = merge_dicts_in_lexicographical_order(answers, {agent_id + 1: answer})

    # Set final progress to 100%
    if progress_file:
        with open(progress_file, 'w') as f:
            json.dump({'progress': 100}, f)
    
    output_manager.save_json(answers, 'answers.json')
    output_manager.save_json(errors, 'execution_errors.json')

    return answers, errors

def questionnaire_iterator(config_set, processed_data, execution_order, sample_space, sample_space_size, sample_dimensions, upload = False, progress_file=None):
    config, llm_client, logger, output_manager = config_set
    answers = {}
    errors = {}
    
    for agent_id in range(sample_space_size):
        # Update progress
        if progress_file:
            progress = agent_id  * 100 / sample_space_size
            with open(progress_file, 'w') as f:
                json.dump({'progress': progress}, f)

        if not upload:
            sample_profile = Module.SampleGenerationModule.flow.format_single_profile(sample_space[agent_id], sample_dimensions)
        else:
            sample_profile = sample_space[agent_id]
                
        errors[agent_id + 1] = []
        
        questions = format_full_question(processed_data, json_processing.get_json_nested_value(config, "llm_settings.max_tokens"))[0]
                    
        answer_text = llm_client.generate(
            prompt=f"""{execution_order}\n{questions}""",
            system_prompt=f"""You act as a survey participant with the following profile: {sample_profile}\nThe output format should be in JSON, with each value structured as "question number: answer".  Do not place ```json at the beginning."""
        )

        try:
            answer_dict = json.loads(answer_text)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            answer_dict = {}
        
        answers = merge_dicts_in_lexicographical_order(answers, {agent_id + 1: answer_dict})

    # Set final progress to 100%
    if progress_file:
        with open(progress_file, 'w') as f:
            json.dump({'progress': 100}, f)

    output_manager.save_json(answers, 'answers.json')
    output_manager.save_json(errors, 'execution_errors.json')

    return answers, errors
