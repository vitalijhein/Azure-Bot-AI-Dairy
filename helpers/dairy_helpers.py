import logging
import os 
import requests
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from typing import List

# Initialize logger
logger = logging.getLogger(__name__)


# Validate environment variables
NOTION_API_KEY = os.getenv("NotionAPIKey")
DATABASE_ID = os.getenv("NotionDatabaseId")
OPENAI_KEY = os.getenv("OpenAIKey")
PROJECTS_DATABASE_ID = os.getenv("ProjectsDatabaseId")
TASKS_DATABASE_ID = os.getenv("TasksDatabaseId")

REQUIRED_ENV_VARS = {
    "NotionAPIKey": NOTION_API_KEY,
    "NotionDatabaseId": DATABASE_ID,
    "OpenAIKey": OPENAI_KEY,
    "ProjectsDatabaseId": PROJECTS_DATABASE_ID,
    "TasksDatabaseId": TASKS_DATABASE_ID
}

class DairyHelpers:
    """
    A helper class for 
    """
    def __init__(self):
        """
        Initializes the NotionHelpers class.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.StreamHandler()
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        
    def generate_dairy(self, dairy_txt) -> str:
        """ Generate a structured summary based on the provided diary text."""
        try:
            model = ChatOpenAI(model_name='chatgpt-4o-latest', temperature = 0, api_key=OPENAI_KEY)
            dairy_prompt = self.read_md_to_formattable_string(os.path.join('data', 'dairy_summary_prompt copy 2.md'))
            prompt_template = ChatPromptTemplate.from_messages([("user", dairy_prompt)])
            parser = StrOutputParser()
            chain = prompt_template | model | parser
            result = chain.invoke({"raw_dairy": dairy_txt})
            return result
           
        except Exception as e:
            logging.error(f"Error generating diary summary: {e}", exc_info=True)
            return ""
        
    def generate_next_steps(self, structured_summary) -> str:
        """ Generate next steps based on the structured summary."""
        try:
            model = ChatOpenAI(model_name='chatgpt-4o-latest', temperature = 0.5, api_key=OPENAI_KEY)
            next_steps_prompt = self.read_md_to_formattable_string(os.path.join('data', 'dairy_next_steps_prompt.md'))
            prompt_template = ChatPromptTemplate.from_messages([("system", next_steps_prompt), "user", structured_summary])
            parser = StrOutputParser()
            chain = prompt_template | model | parser
            result = chain.invoke({})
            logger.debug("Generated next steps successfully.")
            return result
           
        except Exception as e:
            logging.error(f"Error generating case study: {e}")
            return ""
        
    def read_md_to_formattable_string(self, file_path):
        """
        Read a markdown file and return its content as a string.
        """
        try: 
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            logger.debug(f"Successfully read markdown file: {file_path}")
            return content
        except Exception as e:
            logging.error(f"Error while reading markdown file {file_path}: {e}")
            return "" 