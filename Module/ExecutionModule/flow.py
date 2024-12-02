from Module.ExecutionModule.format_questionnaire import add_few_shot_learning, few_shot_learning_template
from Module.ExecutionModule.cost_estimation import cost_estimation
from Module.ExecutionModule.iterator import questionnaire_iterator, questionnaire_iterator_segment

def questionnaire_execute_iterator(config_set, processed_data, question_segments, execution_order, sample_space, sample_space_size, sample_dimensions, segmentation = True, upload = False, progress_file=None):

    if segmentation:
        answers, errors = questionnaire_iterator_segment(config_set, processed_data, question_segments, execution_order, sample_space, sample_space_size, sample_dimensions, upload, progress_file)

    else:
        answers, errors = questionnaire_iterator(config_set, processed_data, execution_order, sample_space, sample_space_size, sample_dimensions, upload, progress_file)
    
    return answers, errors
