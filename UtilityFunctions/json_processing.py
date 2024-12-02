import json

def get_json_nested_value(data, key_path, not_found="not found"):
    keys = key_path.split('.')
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return not_found
    return data

def read_json_value(file_path, key_path, not_found="not found"):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return get_json_nested_value(data, key_path, not_found)

def find_keys_with_type(json_data, target_type="single_choice"):
    result = []
    for key, value in json_data.items():
        if isinstance(value, dict) and value.get("type") == target_type:
            result.append(key)
    return result

def append_question_to_json(file_path, new_question, question_id="0"):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        data[question_id] = new_question

        data[question_id]['type'] = 'single_choice'

        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)
        
        print(f"Question with ID '{question_id}' added successfully.")
    except FileNotFoundError:
        print("The specified file does not exist.")
    except json.JSONDecodeError:
        print("Error decoding JSON from the file.")

def get_key_list(data, target_key):
    try:
        sorted_keys = sorted(data.keys())
        result_list = [data[key][target_key] for key in sorted_keys if target_key in data[key]]
        return result_list
    except KeyError:
        print("The specified key does not exist in some items.")
        return []

def dump_print(data):
    print(json.dumps(data, indent = 4))
