import json

from Module.ExecutionModule.iterator import questionnaire_iterator_segment, questionnaire_iterator


def questionnaire_execute_iterator(config_set, processed_data, question_segments, execution_order, sample_space, sample_space_size, sample_dimensions, segmentation=True, upload=False):
    output_dir = config_set[3].output_dir

    # Read number of executions from sample_settings.json
    try:
        with open(output_dir / "sample_settings.json", 'r') as f:
            settings = json.load(f)
            num_executions = int(settings.get("executions", 1))
    except (FileNotFoundError, json.JSONDecodeError):
        num_executions = 1

    all_answers = {}
    all_errors = {}

    for execution_num in range(1, num_executions + 1):
        # Create execution-specific directory
        execution_dir = output_dir / f"execution_{execution_num}"
        execution_dir.mkdir(exist_ok=True)

        # Update output manager's directory for this execution
        config_set[3].set_execution_dir(execution_dir)

        # Create execution-specific progress file
        execution_progress_file = execution_dir / "progress.json"
        with open(execution_progress_file, 'w') as f:
           json.dump({'progress': 0}, f)

        if segmentation:
            answers, errors = questionnaire_iterator_segment(
                config_set, processed_data, question_segments, execution_order,
                sample_space, sample_space_size, sample_dimensions, upload,
                execution_progress_file
            )
        else:
            answers, errors = questionnaire_iterator(
                config_set, processed_data, execution_order,
                sample_space, sample_space_size, sample_dimensions, upload,
                execution_progress_file
            )

        all_answers[execution_num] = answers
        all_errors[execution_num] = errors

    return all_answers, all_errors
