import Module.PreprocessingModule.flow
import Module.SampleGenerationModule.flow
import Module.ExecutionModule.flow
from Config.config import load_config, load
from Module.ExecutionModule.cost_estimation import cost_estimation
from UtilityFunctions import json_processing

if __name__ == "__main__":
    # Setup
    config_set = load_config("./Config/config.json")
    config, llm_client, logger, output_manager = config_set
    
    ################################
    # I. Survey preprocessing
    # I-a. Preprocessing
    if json_processing.get_json_nested_value(config, "debug_switch.preprocess"):
        processed_data, question_segments, is_dag = Module.PreprocessingModule.flow.preprocess_survey(config_set, json_processing.get_json_nested_value(config, "user_preference.survey_path"))
    else: processed_data, question_segments, is_dag = load('preprocess', config)
    
    # I-b. DAG check
    logger.info(f"Survey size: {len(processed_data)}")
    
    # I-c. Model calibration
    if json_processing.get_json_nested_value(config, "user_preference.model_calibration.enable"):
        Module.PreprocessingModule.flow.preprocess_survey_model_calibration(config_set, processed_data)
    
    processed_data, question_segments, is_dag = load('preprocess', config)
    
    ################################
    # II. Sample space generation
    if json_processing.get_json_nested_value(config, "debug_switch.samplespace"):
        # II-a. Sample dimensions generation
        sample_dimensions = Module.SampleGenerationModule.flow.generate_sample_dimension(config_set, processed_data)
        
        # II-b. User adjust dimensions
        
        # II-c. Sample generation
        sampled_df = Module.SampleGenerationModule.flow.generate_sample_space(config_set)
    else: sample_dimensions, sampled_df = load('samplespace', config)

    sample_space, sample_space_size = Module.SampleGenerationModule.flow.format_sample_space(sampled_df)
    sample_profile_0 = Module.SampleGenerationModule.flow.format_single_profile(sample_space[0], sample_dimensions)
    
    # II-d. User adjust samples
    
    ################################
    # III. Execute
    # III-a. User few-shot/zero-shot addition
    ### NOTE Zengqing Wu: Not yet implemented at the front end.
    # few_shot_dict = {"2": Module.ExecutionModule.flow.few_shot_learning_template["reasoning"]}
    # processed_data = Module.ExecutionModule.flow.add_few_shot_learning(processed_data, few_shot_dict)

    # III-b. Cost estimation and change parameters
    total_cost = cost_estimation(config_set, processed_data, question_segments, sample_space_size, sample_profile_0, json_processing.get_json_nested_value(config, "llm_settings.max_tokens"))

    # III-c. Format questionnaire
    execution_order = json_processing.get_json_nested_value(config, "user_preference.execution.order")

    if not json_processing.get_json_nested_value(config, "debug_switch.execution"): sample_space_size = 2
    answers, errors = Module.ExecutionModule.flow.questionnaire_execute_iterator(config_set, processed_data, question_segments, execution_order, sample_space, sample_space_size, sample_dimensions, json_processing.get_json_nested_value(config, "user_preference.execution.segmentation"))
    
    ################################
    # IV. Results presentation
    