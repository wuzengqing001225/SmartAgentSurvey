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
            if force_max_tokens != None:
                self.max_tokens = force_max_tokens

            messages = [{"role": "user", "content": prompt}]

            if system_prompt:
                messages.insert(0, {"role": "user", "content": system_prompt})

            self.logger.info(f"Sending request to {self.provider} with {len(messages)} messages")
            self.logger.info(f"Message sent: {messages}")

            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                self.logger.info(f"Response: {response.content[0].text}")
                return response.content[0].text

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                self.logger.info(f"Response: {response.choices[0].message.content}")
                return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise

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

                return response.output_text
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
                 return response.content[0].text

        except Exception as e:
            self.logger.error(f"Error in multimodal processing: {str(e)}")
            raise
