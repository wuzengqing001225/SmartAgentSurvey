from UtilityFunctions import json_processing
from Module.SampleGenerationModule.sample_space import load_sample_dimensions, calculate_sample_space_size, parse_dimensions, generate_sample_space_with_target_size, get_improvement_suggestions, adjust_sampling_with_delta, visualize_kl_overall, visualize_kl_comparison, visualize_sample_distribution_comparison
from Module.SampleGenerationModule.sample_generation import sample_dimension_generation

def generate_sample_dimension(config_set, processed_data):
    return sample_dimension_generation(config_set, processed_data)

def generate_sample_space(config_set):
    config, llm_client, logger, output_manager = config_set
    file_path = output_manager.output_dir / "sample_dimensions.json"

    target_sample_size = json_processing.get_json_nested_value(config, "user_preference.sample.sample_size")
    kl_threshold = json_processing.get_json_nested_value(config, "user_preference.sample.kl_threshold")
    
    sample_dimensions = load_sample_dimensions(file_path)
    sample_space_size = calculate_sample_space_size(sample_dimensions)
    logger.info(f"Sample Space Size: {sample_space_size}")

    parsed_dimensions = parse_dimensions(sample_dimensions)
    sampled_df, kl_divs_before = generate_sample_space_with_target_size(parsed_dimensions, target_sample_size)

    improvement_suggestions, over_threshold_dimensions = get_improvement_suggestions(parsed_dimensions, sampled_df, kl_divs_before, kl_threshold)

    if len(over_threshold_dimensions) != 0:
        sampled_df = adjust_sampling_with_delta(parsed_dimensions, improvement_suggestions, sampled_df, target_sample_size)
        _, kl_divs_after = generate_sample_space_with_target_size(parsed_dimensions, target_sample_size)
        visualize_kl_overall(kl_divs_before, kl_threshold)
        visualize_kl_comparison(kl_divs_before, kl_divs_after, kl_threshold)
        visualize_kl_overall(kl_divs_after, kl_threshold)
    else:
        visualize_kl_overall(kl_divs_before, kl_threshold)
    
    output_manager.save_csv(sampled_df, "sample_space.csv")
    logger.info(f"Sample space generated.")

    visualize_sample_distribution_comparison(parsed_dimensions, sampled_df)

    return sampled_df

def format_sample_space(sampled_df):
    profile_counts = sampled_df.groupby(list(sampled_df.columns)).size().reset_index(name='count')    
    profile_counts['profile_id'] = range(1, len(profile_counts) + 1)

    sample_space = [
        [row['profile_id'], list(row[:-2]), row['count']] for _, row in profile_counts.iterrows()
    ]

    sample_space_size = len(sample_space)
    return sample_space, sample_space_size

def format_single_profile(formatted_sample_profile, sample_dimensions):
    profile = ""

    for settings, value in zip(sample_dimensions.values(), formatted_sample_profile[1]):
        profile += f"{settings['format'].replace('X', str(value))} "
    profile = profile.strip()

    return profile