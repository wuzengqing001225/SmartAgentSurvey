import json
import numpy as np
from scipy.stats import entropy
import random
import pandas as pd
import matplotlib.pyplot as plt

def load_sample_dimensions(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_sample_space_size(dimensions):
    size = 1
    for settings in dimensions.values():
        if "scale" in settings:
            start, end, step = settings["scale"]
            values = list(range(start, end + 1, step))
        elif "options" in settings:
            values = settings["options"]
        else:
            values = []
        size *= len(values)
    return size

def parse_dimensions(dimensions):
    parsed_dimensions = {}
    for dimension, settings in dimensions.items():
        if "scale" in settings:
            start, end, step = settings["scale"]
            values = list(range(start, end + 1, step))
            probabilities = [1 / len(values)] * len(values)  # 均匀分布
        elif "options" in settings:
            values = settings["options"]
            if "distribution" in settings:
                probabilities = [p / sum(settings["distribution"]) for p in settings["distribution"]]
            else:
                probabilities = [1 / len(values)] * len(values)  # 均匀分布
        else:
            values = []
            probabilities = []
        parsed_dimensions[dimension] = {"values": values, "probabilities": probabilities}
    return parsed_dimensions

def generate_sample_space_with_target_size(parsed_dimensions, target_size, batch_size=10):
    samples = []
    dimension_keys = list(parsed_dimensions.keys())
    dimension_values = [parsed_dimensions[dim]["values"] for dim in dimension_keys]
    dimension_probs = [parsed_dimensions[dim]["probabilities"] for dim in dimension_keys]

    current_counts = {dim: {val: 0 for val in values} for dim, values in zip(dimension_keys, dimension_values)}

    for _ in range(0, target_size, batch_size):
        batch_samples = []

        for _ in range(min(batch_size, target_size - len(samples))):
            sample = []
            for dim_idx, (values, target_probs) in enumerate(zip(dimension_values, dimension_probs)):
                total_generated = sum(current_counts[dimension_keys[dim_idx]].values())
                if total_generated > 0:
                    generated_probs = [
                        current_counts[dimension_keys[dim_idx]][val] / total_generated for val in values
                    ]
                else:
                    generated_probs = [0] * len(values)

                adjusted_probs = np.array(target_probs) - np.array(generated_probs)
                adjusted_probs = np.maximum(adjusted_probs, 0)
                if adjusted_probs.sum() > 0:
                    adjusted_probs /= adjusted_probs.sum()
                else:
                    adjusted_probs = np.array(target_probs)

                sampled_value = random.choices(values, weights=adjusted_probs, k=1)[0]
                sample.append(sampled_value)

                current_counts[dimension_keys[dim_idx]][sampled_value] += 1

            batch_samples.append(tuple(sample))

        samples.extend(batch_samples)

    sampled_df = pd.DataFrame(samples, columns=dimension_keys)

    kl_divergences = {}
    for dim_idx, (dimension, target_probs) in enumerate(zip(dimension_keys, dimension_probs)):
        generated_counts = sampled_df[dimension].value_counts(normalize=True)
        generated_probs = np.array([generated_counts.get(val, 0) for val in dimension_values[dim_idx]])
        kl_divergence = entropy(generated_probs + 1e-10, np.array(target_probs) + 1e-10)
        kl_divergences[dimension] = kl_divergence

    return sampled_df, kl_divergences


def get_improvement_suggestions(parsed_dimensions, sampled_df, kl_divs, threshold):
    over_threshold_dimensions = [dim for dim, kl in kl_divs.items() if kl > threshold]
    improvement_suggestions = {}

    for dimension in over_threshold_dimensions:
        target_probs = np.array(parsed_dimensions[dimension]["probabilities"])
        generated_counts = sampled_df[dimension].value_counts(normalize=True)
        generated_probs = np.array([generated_counts.get(v, 0) for v in parsed_dimensions[dimension]["values"]])
        delta = target_probs - generated_probs
        improvement_suggestions[dimension] = delta

    return improvement_suggestions, over_threshold_dimensions

def adjust_sampling_with_delta(parsed_dimensions, improvement_suggestions, original_df, target_size):
    adjusted_samples = {}

    for dimension in parsed_dimensions.keys():
        if dimension in improvement_suggestions:
            values = parsed_dimensions[dimension]["values"]
            original_probs = parsed_dimensions[dimension]["probabilities"]
            delta = improvement_suggestions[dimension]
            adjustment = original_probs + delta

            adjustment = np.maximum(adjustment, 0)
            adjustment /= adjustment.sum()

            adjusted_samples[dimension] = random.choices(values, weights=adjustment, k=target_size)
        else:
            adjusted_samples[dimension] = original_df[dimension].tolist()

    adjusted_df = pd.DataFrame(adjusted_samples)
    return adjusted_df

def visualize_distribution_comparison(parsed_dimensions, sampled_df, adjusted_df, over_threshold_dimensions):
    num_plots = len(over_threshold_dimensions)
    rows = (num_plots + 1) // 2
    plt.figure(figsize=(14, 5 * rows))

    for idx, dimension in enumerate(over_threshold_dimensions, start=1):
        target_probs = parsed_dimensions[dimension]["probabilities"]
        target_labels = parsed_dimensions[dimension]["values"]
        
        original_counts = sampled_df[dimension].value_counts(normalize=True)
        original_probs = [original_counts.get(value, 0) for value in target_labels]

        adjusted_counts = adjusted_df[dimension].value_counts(normalize=True)
        adjusted_probs = [adjusted_counts.get(value, 0) for value in target_labels]
        
        plt.subplot(rows, 2, idx)
        width = 0.25
        x = np.arange(len(target_labels))
        plt.bar(x - width, target_probs, width, label='Target', alpha=0.7)
        plt.bar(x, original_probs, width, label='Original', alpha=0.7)
        plt.bar(x + width, adjusted_probs, width, label='Adjusted', alpha=0.7)
        plt.title(f'Distribution: {dimension}', fontsize=12)
        plt.xticks(x, target_labels, rotation=45, fontsize=10)
        plt.legend(fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    # plt.show()

def visualize_kl_overall(kl_divs, threshold):
    dimensions = list(kl_divs.keys())
    kl_values = list(kl_divs.values())

    sorted_indices = np.argsort(kl_values)
    sorted_dimensions = [dimensions[i] for i in sorted_indices]
    sorted_kl_values = [kl_values[i] for i in sorted_indices]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(sorted_dimensions, sorted_kl_values, color='skyblue', edgecolor='black')
    plt.axhline(y=threshold, color='red', linestyle='--', label=f'Threshold = {threshold}')
    plt.title('Overall KL Divergence for Each Dimension', fontsize=14)
    plt.xlabel('Dimensions', fontsize=12)
    plt.ylabel('KL Divergence', fontsize=12)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    for bar, kl_value in zip(bars, sorted_kl_values):
        if kl_value > threshold:
            bar.set_color('salmon')

    plt.tight_layout()
    # plt.show()

def visualize_kl_comparison(before_kl, after_kl, threshold):
    dimensions = list(before_kl.keys())
    before_values = [before_kl[dim] for dim in dimensions]
    after_values = [after_kl[dim] for dim in dimensions]

    x = np.arange(len(dimensions))
    width = 0.35

    plt.figure(figsize=(12, 6))
    plt.bar(x - width / 2, before_values, width, label='Before Adjustment', color='skyblue', edgecolor='black')
    plt.bar(x + width / 2, after_values, width, label='After Adjustment', color='salmon', edgecolor='black')
    plt.axhline(y=threshold, color='red', linestyle='--', label=f'Threshold = {threshold}')
    plt.title('KL Divergence Before and After Adjustment', fontsize=14)
    plt.xlabel('Dimensions', fontsize=12)
    plt.ylabel('KL Divergence', fontsize=12)
    plt.xticks(ticks=x, labels=dimensions, rotation=45)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    # plt.show()

def visualize_sample_distribution_comparison(parsed_dimensions, sampled_df):
    """
    Visualize the comparison of actual sample distribution with target distribution for each dimension.
    """
    num_dimensions = len(parsed_dimensions)
    rows = (num_dimensions + 1) // 2  # Ensure neat layout with appropriate rows
    plt.figure(figsize=(14, 5 * rows))

    for idx, (dimension, settings) in enumerate(parsed_dimensions.items(), start=1):
        # Get target distribution
        target_probs = settings["probabilities"]
        target_labels = settings["values"]

        # Get actual generated distribution
        generated_counts = sampled_df[dimension].value_counts(normalize=True)
        generated_probs = [generated_counts.get(value, 0) for value in target_labels]

        # Plot comparison
        plt.subplot(rows, 2, idx)
        width = 0.4  # Bar width
        x = np.arange(len(target_labels))
        plt.bar(x - width / 2, target_probs, width, label='Target', alpha=0.7, color='skyblue')
        plt.bar(x + width / 2, generated_probs, width, label='Generated', alpha=0.7, color='salmon')
        plt.title(f'Distribution Comparison: {dimension}', fontsize=12)
        plt.xticks(x, target_labels, rotation=15, fontsize=10)
        plt.ylabel('Probability', fontsize=10)
        plt.legend(fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    # plt.show()
