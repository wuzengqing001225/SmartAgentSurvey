from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime
from pathlib import Path
import Module.PreprocessingModule.flow
import Module.SampleGenerationModule.flow
import Module.ExecutionModule.flow
from Module.ExecutionModule.cost_estimation import cost_estimation
from Module.ExecutionModule.format_questionnaire import add_few_shot_learning
from Module.ExecutionModule.iterator import ExecutionState
from UtilityFunctions import json_processing
from Config.config import load_config, load
from shutil import copy2
import atexit
import pandas as pd
import io


class ConfigManager:
    def __init__(self):
        self._current_config = None
        self._current_config_set = None
        self._current_filename = None

    def set_current_file(self, filename):
        self._current_filename = filename
        self._current_config = None  # Clear cached config
        self._current_config_set = None

    def get_config_set(self):
        if self._current_config_set is None:
            self._current_config_set = load_config(CONFIG_FILE)
        return self._current_config_set

    def get_output_dir(self):
        return self.get_config_set()[3].output_dir

    def update_sample_size(self, new_sample_size):
        self._current_config_set[0]['user_preference']['sample']['sample_size'] = new_sample_size

    def clear(self):
        self._current_config = None
        self._current_config_set = None
        self._current_filename = None


config_manager = ConfigManager()

app = Flask(__name__)

UPLOAD_FOLDER = 'Data/UserUpload'
ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf', 'txt', 'md', 'markdown'}
PROCESS_STATUS_FILE = 'Data/process_status.json'
CONFIG_FILE = 'Config/config.json'
TEMP_FOLDER = 'static/temp'
os.makedirs(TEMP_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def cleanup_temp_folder():
    for filename in os.listdir(TEMP_FOLDER):
        file_path = os.path.join(TEMP_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)


atexit.register(cleanup_temp_folder)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_process_status():
    """Load processing status from JSON file"""
    if os.path.exists(PROCESS_STATUS_FILE):
        with open(PROCESS_STATUS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_process_status(status_dict):
    """Save processing status to JSON file"""
    os.makedirs(os.path.dirname(PROCESS_STATUS_FILE), exist_ok=True)
    with open(PROCESS_STATUS_FILE, 'w') as f:
        json.dump(status_dict, f)


def get_upload_history():
    """Get upload history with processing status"""
    history = []
    status_dict = load_process_status()

    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            file_stat = os.stat(file_path)
            history.append({
                'filename': filename,
                'upload_time': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': file_stat.st_size,
                'processed': status_dict.get(filename, False)
            })
    return sorted(history, key=lambda x: x['upload_time'], reverse=True)


def get_sample_settings_dict():
    config_set = config_manager.get_config_set()
    output_dir = config_set[3].output_dir

    with open(output_dir / 'sample_settings.json', 'r') as f:
        return json.load(f)


@app.route('/')
def index():
    history = get_upload_history()
    return render_template('index.html', history=history)


@app.route('/samplespace')
def samplespace():
    history = get_upload_history()
    return render_template('samplespace.html', history=history)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        file_stat = os.stat(file_path)
        return jsonify({
            'success': True,
            'file': {
                'filename': filename,
                'upload_time': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': file_stat.st_size,
                'processed': False
            }
        })

    return jsonify({'error': 'File type not allowed'}), 400


def update_config(filename):
    """Update config.json with new survey path"""
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    config['user_preference']['survey_path'] = f'./Data/UserUpload/{filename}'

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


@app.route('/process', methods=['POST'])
def process_file():
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({'error': 'Invalid request data'}), 400

    filename = data.get('filename')
    if not filename or not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        return jsonify({'error': 'Invalid filename'}), 400

    try:
        config_manager.set_current_file(filename)

        # Set initial preprocessing status
        status_dict = load_process_status()
        status_dict[filename] = 'preprocessing'
        save_process_status(status_dict)

        # Update config with new file path
        update_config(filename)

        # Load config and process survey
        config_set = config_manager.get_config_set()
        config = config_set[0]

        if json_processing.get_json_nested_value(config, "debug_switch.preprocess"):
            processed_data, question_segments, is_dag = Module.PreprocessingModule.flow.preprocess_survey(
                config_set,
                json_processing.get_json_nested_value(config, "user_preference.survey_path"))
        else:
            processed_data, question_segments, is_dag = load('preprocess', config)

        if not is_dag:
            # Update status to show DAG error
            status_dict = load_process_status()
            status_dict[filename] = 'dag-error'
            save_process_status(status_dict)

            return jsonify({
                'success': False,
                'error': 'DAG_ERROR',
                'message': 'Survey contains cycles and cannot be processed'
            })

        # Update status to preprocessed if successful
        status_dict = load_process_status()
        status_dict[filename] = 'preprocessed'
        save_process_status(status_dict)

        # Load processed survey for display
        output_dir = config_set[3].output_dir
        try:
            with open(output_dir / 'processed_survey.json', 'r', encoding='utf-8') as f:
                survey_data = json.load(f)
        except Exception as e:
            print(f"Error loading processed_survey.json: {e}")
            return jsonify({'error': 'Failed to load processed survey data'}), 500

        # Format questions for display
        questions = []
        for qid, qdata in survey_data.items():
            questions.append({
                'id': qid,
                'question': qdata['question'],
                'type': qdata['type']
            })

        # Copy survey_flow.png to static/temp
        source_image = output_dir / 'survey_flow.png'
        temp_image_path = os.path.join(TEMP_FOLDER, f"survey_flow.png")
        copy2(source_image, temp_image_path)

        return jsonify({
            'success': True,
            'questions': questions,
            'total_questions': len(questions),
            'flow_image': f"{temp_image_path}",
            'is_dag': is_dag
        })

    except Exception as e:
        config_manager.clear()  # Clear on error

        # If there's an error, reset status to unprocessed
        status_dict = load_process_status()
        status_dict[filename] = 'unprocessed'
        save_process_status(status_dict)

        print(f"Processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/delete_temp/<path:filename>', methods=['DELETE'])
def delete_temp_file(filename):
    file_path = os.path.join(TEMP_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'success': True, 'message': f"{filename} deleted successfully"})
    return jsonify({'error': 'File not found'}), 404


@app.route('/few-shot', methods=['POST'])
def handle_few_shot():
    """Adds few shot examples to processed survey by saving them to the processed_survey.json file."""
    few_shot_dict = request.get_json()

    if not isinstance(few_shot_dict, dict):
        return jsonify({"error": "Invalid input format. Expected a dictionary."}), 400

    try:
        config_set = config_manager.get_config_set()
        output_dir = config_set[3].output_dir
        with open(output_dir / "processed_survey.json", 'r', encoding='utf-8') as f:
            processed_data = json.load(f)

        processed_data = add_few_shot_learning(processed_data, few_shot_dict)

        with open(output_dir / "processed_survey.json", 'w') as f:
            json.dump(processed_data, f, indent=2)
        return jsonify({
            'success': True
        })

    except Exception as e:
        print(f"Few-shot processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/save-profiles', methods=['POST'])
def handle_profiles():
    """Update the profiles in sample_space.csv file."""
    edited_profiles = request.get_json()

    if not isinstance(edited_profiles, list) or not all(isinstance(profile, dict) for profile in edited_profiles):
        return jsonify({'error': 'Invalid data format'}), 400

    try:
        df = pd.DataFrame(edited_profiles)
        config_set = config_manager.get_config_set()
        _, _, _, output_manager = config_set
        output_manager.save_csv(df, "sample_space.csv")

        return jsonify({
            'success': True
        })

    except Exception as e:
        print(f"Profile saving error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/calibration', methods=['POST'])
def handle_calibration():
    data = request.get_json()  # Change from request.json
    if not data or 'enable' not in data or 'filename' not in data:
        return jsonify({'error': 'Invalid request data'}), 400

    enable_calibration = data.get('enable')
    filename = data.get('filename')

    try:
        # Load and update config
        config_set = config_manager.get_config_set()
        config, llm_client, logger, output_manager = config_set
        output_dir = config_set[3].output_dir

        # Update calibration settings
        config['user_preference']['preprocessing']['model_calibration']['enable'] = enable_calibration

        # Save updated config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

        if enable_calibration:
            with open(output_dir / "processed_survey.json", 'r', encoding='utf-8') as f:
                processed_data = json.load(f)

            # Perform calibration
            Module.PreprocessingModule.flow.preprocess_survey_model_calibration(config_set, processed_data)

        # Update status to show calibration state
        status_dict = load_process_status()
        status_dict[filename] = 'attention check'
        save_process_status(status_dict)

        return jsonify({
            'success': True
        })

    except Exception as e:
        print(f"Calibration error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/sample/generate_dimensions', methods=['POST'])
def generate_dimensions():
    try:
        current_file = request.json.get('filename')
        if not current_file:
            return jsonify({'error': 'No file specified'}), 400

        # Use existing config set
        config_set = config_manager.get_config_set()
        config, llm_client, logger, output_manager = config_set
        output_dir = config_set[3].output_dir

        config['user_preference']['sample']['upload'] = False
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

        # Load config and generate dimensions
        with open(output_dir / "processed_survey.json", 'r', encoding='utf-8') as f:
            processed_data = json.load(f)

        if json_processing.get_json_nested_value(config, "debug_switch.samplespace"):
            sample_dimensions = Module.SampleGenerationModule.flow.generate_sample_dimension(config_set, processed_data)
        else:
            sample_dimensions = load('sampledimensions', config)

        # Save dimensions
        output_path = output_dir / 'sample_dimensions.json'
        with open(output_path, 'w') as f:
            json.dump(sample_dimensions, f, indent=4)

        return jsonify({
            'success': True,
            'dimensions': sample_dimensions
        })
    except Exception as e:
        print(f"Error generating dimensions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sample/upload', methods=['POST'])
def upload_samples():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Update config
        config_set = config_manager.get_config_set()
        config, llm_client, logger, output_manager = config_set

        config['user_preference']['sample']['upload'] = True
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

        # Process the uploaded file
        output_dir = config_set[3].output_dir

        # Save and process the uploaded samples
        samples = [line.strip() for line in file.stream.read().decode('utf-8').splitlines()]
        sampled_df = pd.DataFrame({'profile': samples})
        sampled_df.to_csv(output_dir / 'sample_space.csv', index=False)

        sample_space = []
        for id, sample in enumerate(samples):
            sample_space.append([id + 1, sample, 1])

        sample_space_size = sampled_df.size
        sample_profile_0 = sample_space[0]

        if sample_space_size >= 8:
            sample_profiles = sample_space[:8]
        else:
            sample_profiles = sample_space

        return jsonify({
            'success': True,
            'total_samples': sample_space_size,
            'sample_profiles': sample_profiles,
            'sample_profile_0': sample_profile_0
        })

    except Exception as e:
        print(f"Error uploading samples: {e}")
        return jsonify({'error': f'Error uploading samples: {str(e)}'}), 500


@app.route('/sample/update_dimensions', methods=['POST'])
def update_dimensions():
    try:
        dimensions = request.json.get('dimensions')
        sample_size = request.json.get('sample_size')
        if not dimensions:
            return jsonify({'error': 'No dimensions provided'}), 400

        config_manager.update_sample_size(sample_size)
        config_set = config_manager.get_config_set()
        output_dir = config_set[3].output_dir

        # Save updated dimensions
        with open(output_dir / 'sample_dimensions.json', 'w') as f:
            json.dump(dimensions, f, indent=4)

        # Generate samples
        sampled_df = Module.SampleGenerationModule.flow.generate_sample_space(config_set)
        sample_space, sample_space_size = Module.SampleGenerationModule.flow.format_sample_space(sampled_df)
        sample_profile_0 = Module.SampleGenerationModule.flow.format_single_profile(sample_space[0], dimensions)

        if sample_space_size >= 8:
            sample_profiles = sample_space[:8]
        else:
            sample_profiles = sample_space

        return jsonify({
            'success': True,
            'total_samples': sample_space_size,
            'sample_profiles': sample_profiles,
            'sample_profile_0': sample_profile_0
        })
    except Exception as e:
        print(f"Error updating dimensions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sample/save_dimensions', methods=['POST'])
def save_dimensions():
    try:
        dimensions = request.json.get('dimensions')
        if not dimensions:
            return jsonify({'error': 'No dimensions provided'}), 400

        config_set = config_manager.get_config_set()
        config, llm_client, logger, output_manager = config_set
        output_dir = config_set[3].output_dir

        # Save dimensions
        with open(output_dir / 'sample_dimensions.json', 'w') as f:
            json.dump(dimensions, f, indent=4)

        return jsonify({
            'success': True,
            'message': 'Dimensions saved successfully'
        })
    except Exception as e:
        print(f"Error saving dimensions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sample/settings', methods=['POST'])
def save_sample_settings():
    try:
        executions = request.json.get('executions')
        if not executions:
            return jsonify({'error': 'No executions provided'}), 400
        config_set = config_manager.get_config_set()
        output_dir = config_set[3].output_dir

        with open(output_dir / 'sample_settings.json', 'w') as f:
            json.dump({'executions': executions}, f, indent=4)
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully'
        })
    except Exception as e:
        print(f"Error saving settings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sample/settings', methods=['GET'])
def get_sample_settings():
    try:
        executions = get_sample_settings_dict()

        return jsonify({
            'success': True,
            'executions': executions['executions']
        })
    except Exception as e:
        print(f"Error retrieving settings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sample/results', methods=['GET'])
def get_sample_results():
    try:
        config_set = config_manager.get_config_set()
        output_dir = config_set[3].output_dir

        # Check if using uploaded samples
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            is_upload = config['user_preference']['sample']['upload']

        if is_upload:
            # For uploaded samples, just read the CSV directly
            sampled_df = pd.read_csv(output_dir / 'sample_space.csv')

            # removed for now
            # if len(sampled_df) > 8:
            #     samples = sampled_df['profile'].tolist()[:8]
            # else:
            #    samples = sampled_df['profile'].tolist()
            samples = sampled_df['profile'].tolist()

            return jsonify({
                'success': True,
                'is_upload': True,
                'total_samples': len(sampled_df),
                'samples': samples
            })
        else:
            # For generated samples, combine with dimensions
            with open(output_dir / 'sample_dimensions.json', 'r') as f:
                dimensions = json.load(f)

            sampled_df = pd.read_csv(output_dir / 'sample_space.csv')

            # if len(sampled_df) > 8:
            #     samples = sampled_df.head(8).to_dict('records')
            # else:
            #     samples = sampled_df.to_dict('records')
            samples = sampled_df.to_dict('records')

            return jsonify({
                'success': True,
                'is_upload': False,
                'total_samples': len(sampled_df),
                'samples': samples,
                'dimensions': dimensions
            })

    except Exception as e:
        print(f"Error getting sample results: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/execute')
def execute():
    history = get_upload_history()
    return render_template('execution.html', history=history)


@app.route('/api/execution/metrics')
def get_execution_metrics():
    try:
        config_set = config_manager.get_config_set()
        config = config_set[0]
        output_dir = config_set[3].output_dir

        # Load necessary data
        processed_survey_path = output_dir / 'processed_survey.json'

        with open(processed_survey_path, 'r', encoding='utf-8') as f:
            processed_data = json.load(f)

        question_segments = Module.PreprocessingModule.flow.preprocess_survey_load(config, processed_data)[0]

        sampled_df_path = output_dir / 'sample_space.csv'
        sampled_df = pd.read_csv(sampled_df_path)

        if not json_processing.get_json_nested_value(config, "user_preference.sample.upload"):
            sample_space, sample_space_size = Module.SampleGenerationModule.flow.format_sample_space(sampled_df)
        else:
            sample_space = []
            samples = sampled_df.iloc[:, 0].tolist()
            for id, sample in enumerate(samples):
                sample_space.append([id + 1, sample, 1])
            sample_space_size = len(sample_space)

        if not json_processing.get_json_nested_value(config, "user_preference.sample.upload"):
            with open(output_dir / "sample_dimensions.json", 'r') as file:
                sample_dimensions = json.load(file)
            sample_profile_0 = Module.SampleGenerationModule.flow.format_single_profile(sample_space[0],
                                                                                        sample_dimensions)
        else:
            sample_profile_0 = sample_space[0]

        # Calculate metrics
        total_cost = cost_estimation(
            config_set,
            processed_data,
            question_segments,
            sample_space_size,
            sample_profile_0,
            json_processing.get_json_nested_value(config, "llm_settings.max_tokens")
        )

        return jsonify({
            'survey_length': len(processed_data),
            'agent_count': sample_space_size,
            'estimated_cost': float(total_cost)
        })
    except Exception as e:
        print(f"Error in metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/execution/start', methods=['POST'])
def start_execution():
    try:
        config_set = config_manager.get_config_set()
        config = config_set[0]
        output_dir = config_set[3].output_dir
        # Reset stop related things
        ExecutionState.reset()
        with open(output_dir / "stop.json", 'w') as f:
            json.dump({'stopped': False}, f)

        # Load necessary data
        with open(output_dir / 'processed_survey.json', 'r', encoding='utf-8') as f:
            processed_data = json.load(f)

        question_segments, is_dag = Module.PreprocessingModule.flow.preprocess_survey_load(config, processed_data)

        sampled_df_path = output_dir / 'sample_space.csv'
        sampled_df = pd.read_csv(sampled_df_path)

        if not json_processing.get_json_nested_value(config, "user_preference.sample.upload"):
            sample_space, sample_space_size = Module.SampleGenerationModule.flow.format_sample_space(sampled_df)
        else:
            sample_space = []
            samples = sampled_df.iloc[:, 0].tolist()
            for id, sample in enumerate(samples):
                sample_space.append([id + 1, sample, 1])

        if not json_processing.get_json_nested_value(config, "user_preference.sample.upload"):
            with open(output_dir / "sample_dimensions.json", 'r') as file:
                sample_dimensions = json.load(file)
            print("Loaded sample dimensions")
        else:
            sample_dimensions = {}
            print("Using empty sample dimensions (upload mode)")

        execution_order = json_processing.get_json_nested_value(
            config, "user_preference.execution.order"
        )
        segmentation = json_processing.get_json_nested_value(
            config, "user_preference.execution.segmentation"
        )
        upload_mode = json_processing.get_json_nested_value(config, "user_preference.sample.upload")
        print(f"Execution settings - order: {execution_order}, segmentation: {segmentation}, upload: {upload_mode}")


        try:
            print("Starting questionnaire execution with parameters:")
            print(f"- Output dir: {output_dir}")
            print(f"- Sample space size: {len(sample_space)}")
            print(f"- Question segments: {len(question_segments)}")

            # Execute survey
            answers, errors = Module.ExecutionModule.flow.questionnaire_execute_iterator(
                config_set,
                processed_data,
                question_segments,
                execution_order,
                sample_space,
                len(sample_space),
                sample_dimensions,
                segmentation,
                upload_mode,
            )
            if ExecutionState.get_stop():
                return jsonify({'success': True, 'stopped': True}), 200

            if not isinstance(answers, dict):
                raise ValueError(f"Invalid answers format: {type(answers)}")

            print(f"Execution completed. Got {len(answers)} answers")

            # Save results
            with open(output_dir / 'answers.json', 'w') as f:
                json.dump(answers, f, indent=2)
            print("Saved results")

            return jsonify({'success': True})

        except Exception as inner_e:
            error_msg = f"Execution error: {str(inner_e)}"
            print(error_msg)
            print(f"Error type: {type(inner_e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

    except Exception as e:
        error_msg = f"Error in start_execution: {str(e)}"
        print(error_msg)
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/execution/stop', methods=['POST'])
def stop_execution():
    try:
        ExecutionState.set_stop()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error setting stop status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stopped': False
        })


@app.route('/api/execution/stop', methods=['GET'])
def get_stop_status():
    try:
        config_set = config_manager.get_config_set()
        output_dir = config_set[3].output_dir
        stop_file = output_dir / 'stop.json'
        if not stop_file.exists():
            return jsonify({
                'success': True,
                'stopped': False
            })

        with open(output_dir / 'stop.json', 'r+', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify({
                'success': True,
                'stopped': data['stopped']
            })
    except Exception as e:
        print(f"Error reading stop status: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'error': str(e),
            'stopped': False
        })


@app.route('/api/execution/progress/<int:execution_num>')
def get_execution_progress(execution_num):
    try:
        output_dir = config_manager.get_config_set()[3].output_dir
        total_executions = get_sample_settings_dict()['executions']

        # Get progress from current execution directory
        execution_dir = output_dir / f"execution_{execution_num}"
        progress_file = execution_dir / 'progress.json'

        if progress_file.exists():
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
                if 'error' in progress_data:
                    return jsonify({
                        'success': False,
                        'error': progress_data['error'],
                        'progress': 0,
                        'current_execution': execution_num,
                        'total_executions': total_executions
                    })
                return jsonify({
                    'success': True,
                    'progress': progress_data.get('progress', 0),
                    'current_execution': execution_num,
                    'total_executions': total_executions
                })
        return jsonify({
            'success': False,
            'progress': 0,
            'current_execution': execution_num,
            'total_executions': total_executions
        })
    except Exception as e:
        print(f"Error reading progress: {str(e)}")  # Debug print
        return jsonify({
            'success': False,
            'error': str(e),
            'progress': 0,
            'current_execution': 1,
            'total_executions': 1
        })


@app.route('/api/execution/download/<format>/<int:execution_num>')
def download_results(format, execution_num):
    try:
        output_dir = config_manager.get_config_set()[3].output_dir
        execution_dir = output_dir / f"execution_{execution_num}"

        # Check if execution directory exists
        if not execution_dir.exists():
            return jsonify({'error': f'Execution {execution_num} not found'}), 404

        if format == 'json':
            json_path = execution_dir / 'answers.json'
            if not json_path.exists():
                return jsonify({'error': 'Results file not found'}), 404

            return send_file(
                json_path,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'survey_responses_execution_{execution_num}.json'
            )

        elif format == 'csv':
            json_path = execution_dir / 'answers.json'
            if not json_path.exists():
                return jsonify({'error': 'Results file not found'}), 404

            # Load JSON data
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Convert to DataFrame
            rows = []
            for agent_id, responses in data.items():
                row = {'agent_id': agent_id}
                for q_id, answer in responses.items():
                    if isinstance(answer, list):
                        answer = ' | '.join(str(a) for a in answer)
                    elif isinstance(answer, dict):
                        for sub_q, sub_a in answer.items():
                            row[f"Q{q_id}_{sub_q}"] = sub_a
                        continue
                    row[f"Q{q_id}"] = answer
                rows.append(row)

            df = pd.DataFrame(rows)

            # Convert to CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)

            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'survey_responses_execution_{execution_num}.csv'
            )

        elif format == 'samplespace':
            sample_space_path = execution_dir / 'sample_space.csv'
            if not sample_space_path.exists():
                return jsonify({'error': 'Sample space file not found'}), 404

            return send_file(
                sample_space_path,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'sample_space_execution_{execution_num}.csv'
            )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/cleanup', methods=['POST'])
def cleanup_config():
    config_manager.clear()
    return jsonify({'success': True})


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'GET':
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return jsonify(config)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.get_json()

            # Load existing config
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)

            # Update config with new values
            config['llm_settings'].update(data['llm_settings'])
            config['user_preference']['sample'].update(data['user_preference']['sample'])
            config['user_preference']['execution'].update(data['user_preference']['execution'])

            # Save updated config
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/execution/download/samplespace')
def download_sample_space():
    try:
        output_dir = config_manager.get_config_set()[3].output_dir
        return send_file(
            output_dir / 'sample_space.csv',
            mimetype='text/csv',
            as_attachment=True,
            download_name='sample_profiles.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run()
