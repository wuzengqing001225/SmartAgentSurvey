from Module.PreprocessingModule.File2QuestionTree.question_parser import extract_raw_questions, create_batch_prompt, merge_survey_data
from Module.PreprocessingModule.File2QuestionTree.graph_builder import SurveyFlowVisualizer
from Module.PreprocessingModule.file_convert import read_file
from UtilityFunctions import json_processing
import json

def preprocess_survey(config_set, file_path: str):
    config, llm_client, logger, output_manager = config_set

    try:
        # Max questions per segment
        if json_processing.get_json_nested_value(config, "user_preference.preprocessing.max_questions_per_segment") != "not found":
            max_questions_per_segment = json_processing.get_json_nested_value(config, "user_preference.preprocessing.max_questions_per_segment")
        else:
            max_questions_per_segment = 20
        
        # Load
        logger.info(f"Reading survey file: {file_path}")
        survey_text = read_file(file_path)
        
        # Extract raw questions
        logger.info("Extracting raw questions from survey text")
        # raw_questions = extract_raw_questions(survey_text)
        # logger.info(f"Extracted {len(raw_questions)} questions")
        
        # Create JSON
        logger.info("Creating analysis prompt")
        prompt = create_batch_prompt(survey_text)
        
        analysis = llm_client.generate(
            prompt=prompt,
            system_prompt="You are a survey analysis assistant. Strictly return JSON only, with no explanations or additional text. Do not place ```json at the beginning.",
            force_max_tokens = 16384
        )

        logger.info("Merging survey data")
        # processed_data = merge_survey_data(json.loads(analysis), raw_questions)
        processed_data = json.loads(analysis)
        logger.info("Successfully loaded response as JSON!")
        
        # Output JSON
        output_manager.save_merged_data(processed_data)
        
        # Visualization
        logger.info("Creating survey flow visualization")
        visualizer = SurveyFlowVisualizer(processed_data)
        
        # DAG Check
        is_dag = visualizer.is_dag()
        logger.info(f"Survey flow DAG check: {'Valid' if is_dag else 'Invalid'}")

        viz_path = output_manager.get_visualization_path()
        if viz_path:
            visualizer.visualize(viz_path)
            logger.info(f"Visualization saved to: {viz_path}")

        # Split survey to segments
        question_segments = visualizer.split_question_segments(max_questions_per_segment = max_questions_per_segment)

        return processed_data, question_segments, is_dag
    
    except Exception as e:
        logger.error(f"Error processing survey: {str(e)}", exc_info=True)
        raise

def preprocess_survey_load(config, processed_data):
    if json_processing.get_json_nested_value(config, "user_preference.preprocessing.max_questions_per_segment") != "not found":
        max_questions_per_segment = json_processing.get_json_nested_value(config, "user_preference.preprocessing.max_questions_per_segment")
    else:
        max_questions_per_segment = 20
    
    visualizer = SurveyFlowVisualizer(processed_data)
    is_dag = visualizer.is_dag()
    question_segments = visualizer.split_question_segments(max_questions_per_segment = max_questions_per_segment)

    return question_segments, is_dag

def preprocess_survey_model_calibration(config_set, processed_data):
    config, llm_client, logger, output_manager = config_set
    preference_model_calibration = json_processing.get_json_nested_value(config, "user_preference.preprocessing.model_calibration")

    if preference_model_calibration.get('enable'):
        try:
            if preference_model_calibration.get('question') == -1:
                single_choice_problems = json_processing.find_keys_with_type(processed_data, 'single_choice')
                if len(single_choice_problems) == 0:
                    calibration_question = 1
                else:
                    import random
                    calibration_question = single_choice_problems[random.randint(0, len(single_choice_problems) - 1)]
            else:
                calibration_question = preference_model_calibration.get('question')
            
            calibration_question_text = json_processing.get_json_nested_value(processed_data, f'{calibration_question}.question')
            calibration_question_fulltext = f"{json_processing.get_json_nested_value(processed_data, f'{calibration_question}.question')}\nOptions: {','.join(json_processing.get_json_nested_value(processed_data, f'{calibration_question}.options'))}"

            if len(calibration_question_text) > 60: calibration_question_text = f"{calibration_question_text[:60]}..."
            logger.info(f"Choose question #{calibration_question}: \"{calibration_question_text}\" for model calibration.")

            calibration_new_question_fulltext = llm_client.generate(
                prompt=f"Design a question that has the same meaning as the original question provided but with a different expression (Note that if the options contain jump logic like go to question XXX, neglect the jump logic part). Output the question on the first line and the options on the second line, separated by commas. Make sure the output has two lines. The options should correspond one-to-one with the original options in both order and meaning (they may be identical). If the original question is a rating question, the new options should also be ratings.\nOriginal question: {calibration_question_fulltext}",
                system_prompt="Output should be concise.",
                force_max_tokens = 512
            )

            calibration_new_question, calibration_new_question_options = calibration_new_question_fulltext.split('\n')[0].strip(), calibration_new_question_fulltext.split('\n')[-1].strip().split(',')
            json_processing.append_question_to_json(output_manager.output_dir / "processed_survey.json", {"question": calibration_new_question, "options": calibration_new_question_options}, str(len(processed_data) + 1))
            logger.info("Model calibration question generated.")
        
        except Exception as e:
            logger.error(f"Error generating model calibration: {str(e)}", exc_info=True)
            raise
