#!/usr/bin/env python3
"""
Smart Model Matcher
Flexible model name matching system based on configuration files
"""

import json
import re
import os
from typing import Optional, Tuple, Dict, Any
import tiktoken


class SmartModelMatcher:
    """Smart model matcher class"""

    def __init__(self, config_path: str = "./Config/model_mapping_rules.json"):
        """
        Initialize model matcher

        Args:
            config_path: Configuration file path
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found, using fallback rules")
            return self._get_fallback_config()
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {self.config_path}: {e}, using fallback rules")
            return self._get_fallback_config()

    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration"""
        return {
            "claude_api_mapping": {
                "default_model": "claude-3-5-sonnet-20241022"
            },
            "openai_encoding_mapping": {
                "default_encoding": "cl100k_base"
            },
            "openai_message_overhead": {
                "default_overhead": {"tokens_per_message": 3, "tokens_per_name": 1}
            }
        }

    def get_claude_api_model_name(self, model_name: str) -> str:
        """
        Get Claude API compatible model name

        Args:
            model_name: User input model name

        Returns:
            str: API compatible model name
        """
        if not model_name or not model_name.strip():
            return self.config["claude_api_mapping"]["default_model"]

        normalized_name = model_name.lower().strip()

        # Check if already in API format
        api_pattern = self.config["claude_api_mapping"].get("api_model_pattern", "")
        if api_pattern and re.match(api_pattern, normalized_name):
            return model_name

        # Try to match patterns in configuration
        patterns = self.config["claude_api_mapping"].get("patterns", {})

        for rule_name, rule_config in patterns.items():
            rule_patterns = rule_config.get("patterns", [])
            api_model = rule_config.get("api_model", "")

            for pattern in rule_patterns:
                try:
                    if re.search(pattern, normalized_name):
                        return api_model
                except re.error:
                    # If regex has error, skip this pattern
                    continue

        # If no match found, return default model
        return self.config["claude_api_mapping"]["default_model"]

    def get_openai_encoding(self, model_name: str):
        """
        Get tiktoken encoding for OpenAI model

        Args:
            model_name: Model name

        Returns:
            tiktoken encoding object
        """
        normalized_name = model_name.lower().strip()

        # First try to get directly
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            pass

        # Use mapping rules from configuration file
        encodings = self.config["openai_encoding_mapping"].get("encodings", {})

        for encoding_name, encoding_config in encodings.items():
            patterns = encoding_config.get("patterns", [])

            for pattern in patterns:
                try:
                    if re.search(pattern, normalized_name):
                        return tiktoken.get_encoding(encoding_name)
                except re.error:
                    continue

        # Default encoding
        default_encoding = self.config["openai_encoding_mapping"]["default_encoding"]
        return tiktoken.get_encoding(default_encoding)

    def get_openai_message_overhead(self, model_name: str) -> Tuple[int, int]:
        """
        Get OpenAI model message token overhead

        Args:
            model_name: Model name

        Returns:
            Tuple[tokens_per_message, tokens_per_name]
        """
        overhead_config = self.config["openai_message_overhead"]

        # Check specific models
        specific_models = overhead_config.get("specific_models", {})
        if model_name in specific_models:
            model_config = specific_models[model_name]
            return (model_config["tokens_per_message"], model_config["tokens_per_name"])

        # Check model families
        normalized_name = model_name.lower().strip()
        model_families = overhead_config.get("model_families", {})

        for family_name, family_config in model_families.items():
            if family_name.lower() in normalized_name:
                return (family_config["tokens_per_message"], family_config["tokens_per_name"])

        # Default overhead
        default_config = overhead_config["default_overhead"]
        return (default_config["tokens_per_message"], default_config["tokens_per_name"])

    def add_claude_model_rule(self, rule_name: str, patterns: list, api_model: str):
        """
        Dynamically add Claude model matching rule

        Args:
            rule_name: Rule name
            patterns: List of matching patterns
            api_model: API model name
        """
        if "claude_api_mapping" not in self.config:
            self.config["claude_api_mapping"] = {"patterns": {}}

        if "patterns" not in self.config["claude_api_mapping"]:
            self.config["claude_api_mapping"]["patterns"] = {}

        self.config["claude_api_mapping"]["patterns"][rule_name] = {
            "patterns": patterns,
            "api_model": api_model
        }

    def add_openai_encoding_rule(self, encoding_name: str, patterns: list):
        """
        Dynamically add OpenAI encoding matching rule

        Args:
            encoding_name: Encoding name
            patterns: List of matching patterns
        """
        if "openai_encoding_mapping" not in self.config:
            self.config["openai_encoding_mapping"] = {"encodings": {}}

        if "encodings" not in self.config["openai_encoding_mapping"]:
            self.config["openai_encoding_mapping"]["encodings"] = {}

        self.config["openai_encoding_mapping"]["encodings"][encoding_name] = {
            "patterns": patterns
        }

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_supported_models(self) -> Dict[str, list]:
        """
        Get list of supported models

        Returns:
            Dict containing Claude and OpenAI supported model information
        """
        result = {
            "claude_models": [],
            "openai_models": []
        }

        # Claude models
        claude_patterns = self.config.get("claude_api_mapping", {}).get("patterns", {})
        for rule_name, rule_config in claude_patterns.items():
            api_model = rule_config.get("api_model", "")
            patterns = rule_config.get("patterns", [])
            result["claude_models"].append({
                "rule_name": rule_name,
                "api_model": api_model,
                "supported_patterns": patterns
            })

        # OpenAI encodings
        openai_encodings = self.config.get("openai_encoding_mapping", {}).get("encodings", {})
        for encoding_name, encoding_config in openai_encodings.items():
            patterns = encoding_config.get("patterns", [])
            result["openai_models"].append({
                "encoding": encoding_name,
                "supported_patterns": patterns
            })

        return result

    def validate_model_name(self, model_name: str) -> Dict[str, Any]:
        """
        Validate model name and return detailed information

        Args:
            model_name: Model name to validate

        Returns:
            Dict containing validation results and matching information
        """
        result = {
            "original_name": model_name,
            "is_claude": "claude" in model_name.lower(),
            "is_openai": "claude" not in model_name.lower(),
            "matched_rule": None,
            "api_model": None,
            "encoding": None,
            "message_overhead": None
        }

        if result["is_claude"]:
            result["api_model"] = self.get_claude_api_model_name(model_name)
            # Find matching rule
            normalized_name = model_name.lower().strip()
            patterns = self.config.get("claude_api_mapping", {}).get("patterns", {})

            for rule_name, rule_config in patterns.items():
                rule_patterns = rule_config.get("patterns", [])
                for pattern in rule_patterns:
                    try:
                        if re.search(pattern, normalized_name):
                            result["matched_rule"] = rule_name
                            break
                    except re.error:
                        continue
                if result["matched_rule"]:
                    break

        if result["is_openai"]:
            encoding = self.get_openai_encoding(model_name)
            result["encoding"] = encoding.name
            result["message_overhead"] = self.get_openai_message_overhead(model_name)

        return result


# Global instance
_global_matcher = None

def get_global_matcher() -> SmartModelMatcher:
    """Get global model matcher instance"""
    global _global_matcher
    if _global_matcher is None:
        _global_matcher = SmartModelMatcher()
    return _global_matcher


# Convenience functions
def get_claude_api_model_name(model_name: str) -> str:
    """Convenience function: Get Claude API model name"""
    return get_global_matcher().get_claude_api_model_name(model_name)


def get_openai_encoding_for_model(model_name: str):
    """Convenience function: Get OpenAI encoding"""
    return get_global_matcher().get_openai_encoding(model_name)


def get_openai_message_tokens_overhead(model_name: str) -> Tuple[int, int]:
    """Convenience function: Get OpenAI message overhead"""
    return get_global_matcher().get_openai_message_overhead(model_name)