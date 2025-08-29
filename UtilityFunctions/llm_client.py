import json
import logging
from typing import Dict, List, Optional, Union
import anthropic
import openai
import base64
import os
class LLMClient:
    def __init__(self, config_path: str = "config.json", output_dir: str = './'):
        self.output_dir = output_dir
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._setup_client()

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            raise Exception(f"Failed to load config file: {str(e)}")

    def _setup_logging(self):
        log_config = self.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO"))
        log_file = self.output_dir / "llm_client.log"

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _setup_client(self):
        llm_settings = self.config.get("llm_settings", {})
        self.provider = llm_settings.get("provider", "anthropic").lower()
        self.api_key = llm_settings.get("api_key")
        self.model = llm_settings.get("model", "gpt-4o-mini")
        self.base_url = llm_settings.get("base_url")
        self.max_tokens = llm_settings.get("max_tokens", 256)
        self.temperature = llm_settings.get("temperature", 0.0)

        if not self.api_key:
            raise ValueError("API key not found in config")

        if self.provider == "anthropic":
            if not self.base_url:
                self.base_url = "https://api.anthropic.com"
            self.client = anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url)
        elif self.provider == "openai":
            if not self.base_url:
                self.base_url = "https://api.openai.com/v1"
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate(self,
                prompt: str,
                system_prompt: Optional[str] = None,
                force_max_tokens: Optional[int] = None) -> str:
        try:
            if force_max_tokens is not None:
                self.max_tokens = force_max_tokens

            messages = [{"role": "user", "content": prompt}]

            if system_prompt:
                messages.insert(0, {"role": "user" if self.provider=="anthropic" else "system", "content": system_prompt})

            self.logger.info(f"Sending request to {self.provider} with {len(messages)} messages")
            self.logger.info(f"Message sent: {messages}")

            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                response_text = response.content[0].text
                # Extract JSON from response if it contains extra text
                cleaned_response = self._extract_json_from_response(response_text)
                self.logger.info(f"Response: {cleaned_response}")
                return cleaned_response

            elif self.provider == "openai":
                if "gpt-5" in self.model:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature
                    )
                response_text = response.choices[0].message.content
                # Extract JSON from response if it contains extra text
                cleaned_response = self._extract_json_from_response(response_text)
                self.logger.info(f"Response: {cleaned_response}")
                return cleaned_response

        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON content from LLM response that may contain additional explanatory text.
        This method handles cases where LLM adds reasoning or explanation before/after the JSON.
        """
        import re

        # Remove any markdown code block markers
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*$', '', response_text)

        # First, try to parse the response directly as JSON
        try:
            json.loads(response_text.strip())
            return response_text.strip()
        except json.JSONDecodeError:
            pass

        # Try to find the most complete JSON object using balanced braces
        brace_count = 0
        start_idx = -1
        end_idx = -1

        for i, char in enumerate(response_text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    end_idx = i
                    break

        if start_idx != -1 and end_idx != -1:
            potential_json = response_text[start_idx:end_idx + 1]
            try:
                json.loads(potential_json)
                return potential_json.strip()
            except json.JSONDecodeError:
                pass

        # If all else fails, return original response and let the calling code handle the error
        self.logger.warning("Could not extract valid JSON from response, returning original text")
        return response_text

    def generate_multimodal(self, file_path: str, prompt: str, system_prompt: Optional[str] = None,) -> str:
        """
        Upload a file to OpenAI and generate a response using multimodal processing.
        This method is used for surveys containing images, where the LLM needs to analyze both text and images.
        NOTE ONLY PDF files are supported for multimodal processing.
        """

        if not file_path.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are supported for multimodal processing.")

        try:
            # upload the file to OpenAI
            if self.provider == "openai":
                file = self.client.files.create(
                    file=open(file_path, "rb"),
                    purpose="user_data",
                )

                messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_file",
                                    "file_id": file.id,
                                },
                                {
                                    "type": "input_text",
                                    "text": prompt,
                                },
                            ],
                        },
                    ]

                if system_prompt:
                    messages.insert(0, {"role": "user", "content": system_prompt})

                # Call the OpenAI multimodal API
                response = self.client.responses.create(
                    model=self.model,
                    input=messages
                )

                self.logger.info("Successfully generated multimodal response...")

                # Extract JSON from response if it contains extra text
                cleaned_response = self._extract_json_from_response(response.output_text)
                self.logger.info(f"Cleaned response: {cleaned_response}")
                return cleaned_response
            else:
                 with open(file_path, "rb") as f:
                    file=self.client.beta.files.upload(file=(os.path.basename(f.name), f, "application/pdf"))

                 messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "file",
                                        "file_id": file.id
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                            ],
                        },
                    ]

                 if system_prompt:
                    messages.insert(0, {"role": "user", "content": system_prompt})

                 response = self.client.beta.messages.create(
                    betas=["files-api-2025-04-14"],
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=messages,)
                 self.logger.info("Successfully generated multimodal response...")
                 response_text = response.content[0].text

                 # Extract JSON from response if it contains extra text
                 cleaned_response = self._extract_json_from_response(response_text)
                 self.logger.info(f"Cleaned response: {cleaned_response}")
                 return cleaned_response

        except Exception as e:
            self.logger.error(f"Error in multimodal processing: {str(e)}")
            raise
