import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from UtilityFunctions.llm_client import LLMClient
import pandas as pd

class OutputManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        if self.config['output']['mode'] == 'debug':
            self.folder = "debug"
        else:
            self.folder = datetime.now().strftime("%Y%m%d_%H%M%S") + '_' + self.config['output']['name']
        self.output_dir = self._setup_output_dir()
        self._setup_logging()
        
    def _setup_output_dir(self) -> Path:
        base_dir = Path(self.config["output"]["base_dir"])
        output_dir = base_dir / self.folder
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
        
    def _setup_logging(self):
        log_file = self.output_dir / "processor.log"
        log_config = self.config.get("logging", {})
        
        logging.basicConfig(
            level=getattr(logging, log_config.get("level", "INFO")),
            format=log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Output directory created at: {self.output_dir}")
        
    def save_merged_data(self, data: Dict[str, Any]):
        if self.config["output"]["merged_json"]["enabled"]:
            output_path = self.output_dir / "processed_survey.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Merged data saved to: {output_path}")
    
    def get_visualization_path(self) -> str:
        if self.config["output"]["visualization"]["enabled"]:
            return str(self.output_dir / f"survey_flow.{self.config['output']['visualization']['format']}")
        return None
    
    def save_json(self, data: Dict[str, Any], file_name: str):
        if ".json" not in file_name: file_name += ".json"
        output_path = self.output_dir / file_name
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Data saved to: {output_path}")
        return output_path
    
    def save_csv(self, data, file_name: str):
        if ".csv" not in file_name: file_name += ".csv"
        output_path = self.output_dir / file_name
        data.to_csv(output_path, index=False)
        self.logger.info(f"Data saved to: {output_path}")
        return output_path

def load_config(config_path: str = "./Config/config.json"):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    from Config.config import OutputManager
    output_manager = OutputManager(config)
    logger = logging.getLogger(__name__)

    llm_client = LLMClient(config_path, output_manager.output_dir)

    return config, llm_client, logger, output_manager

def load(process, config, path = './Data/Output/debug/', *args):
    import Module.PreprocessingModule.flow
    if process == 'preprocess':
        with open(f"{path}/processed_survey.json", 'r', encoding='utf-8') as file:
            processed_data = json.load(file)
        question_segments, is_dag = Module.PreprocessingModule.flow.preprocess_survey_load(config, processed_data)
        return processed_data, question_segments, is_dag
    
    elif process == 'samplespace':
        with open(f"{path}/sample_dimensions.json", 'r') as file:
            sample_dimensions = json.load(file)
        sampled_df = pd.read_csv(f"{path}/sample_space.csv")
        return sample_dimensions, sampled_df

    elif process == 'sampledimensions':
        with open(f"{path}/sample_dimensions.json", 'r') as file:
            sample_dimensions = json.load(file)
        return sample_dimensions

    elif process == 'samplespacedf':
        sampled_df = pd.read_csv(f"{path}/sample_space.csv")
        return sampled_df