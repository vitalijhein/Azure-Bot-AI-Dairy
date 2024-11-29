import logging
import os
import json 
from datetime import date
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain.output_parsers import OutputFixingParser
from .structured_helper import Task, ProjectOutput
from .notion_helpers import NotionHelpers

from typing import Optional

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

class ProManHelpers:
    """
    A helper class for converting Markdown text into Notion-compatible blocks.
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
    
    def generate_projects_and_tasks_in_notion(self, notion_helper: NotionHelpers, dairy_txt):
        try: 
            
            # Step 1: Query all existing projects
            logger.info("Querying all projects from Notion.")
            projects = notion_helper.query_all_projects()
            project_names = "\n".join(
                f"Project-Id: {project['project_id']}, Project-Name: {project['project_name']}"
                for project in projects
            )
    
            # Step 2: Extract projects based on the diary text
            logger.info("Extracting projects from diary text.")
            extracted_projects = self.extract_projects(project_names, dairy_txt)
            if not extracted_projects:
                logger.warning("No projects were extracted from the diary text.")        
            if isinstance(extracted_projects, dict):
                extracted_projects = [extracted_projects]  # Convert to a single-item list
            elif not isinstance(extracted_projects, list):
                logger.warning(f"Unexpected task_results type: {type(extracted_projects)}. Defaulting to empty list.")
                extracted_projects = extracted_projects
            # Step 3: Process each result
            for result in extracted_projects:
                if result.get("new_project") == True:
                    try: 

                        project_name=result.get("project_name")
                        logger.info(f"Adding new project: {project_name}.")

                        project_id, status = notion_helper.add_project(
                            project_name=project_name,
                            status="Backlog",
                            owner=["4ec785d6-aaa2-473f-b892-2dab634925b0"],  # Replace with actual user ID(s)
                            priority="Low",
                            summary=result.get("summary")
                        )

                        task_names_list = notion_helper.get_tasks_by_project(project_id) 
                        if task_names_list:
                            task_names_string = "\n".join(task_names_list) + "\n"
                            task_results = self.identify_tasks_for_project(project_name, task_names_string, dairy_txt)                
                        elif not task_names_list: 
                            task_results = self.identify_initial_tasks_for_projects(project_name, dairy_txt)
                            
                        tasks = []
                        if isinstance(task_results, dict):
                            task_results = [task_results]  # Convert to a single-item list
                        elif not isinstance(task_results, list):
                            logger.warning(f"Unexpected task_results type: {type(task_results)}. Defaulting to empty list.")
                            task_results = task_results
                        
                        for task in task_results:
                            if task.get("new_task"):
                                task_name= task.get("task_name")
                                tasks.append(
                                    {
                                        "task_name": task_name,
                                        "status": "Not Started",
                                        "priority": "Low",
                                        "assignee": ["4ec785d6-aaa2-473f-b892-2dab634925b0"]  # Replace with actual user IDs
                                    }
                                )
                        if tasks:
                            logger.info(f"Adding {len(tasks)} tasks to project ID {project_id}.")
                            result = notion_helper.add_tasks_to_project(project_id, tasks)
                            logger.debug(f"Add tasks result: {result}")
                    except Exception as e:
                        logger.error(f"Error while processing new project {result.get('project_name')}: {e}", exc_info=True)
                     
                elif result.get("new_project") == False:
                    try:
                        project_id = result.get("project_id")
                        project_name=result.get("project_name")
                        task_names_list = notion_helper.get_tasks_by_project(project_id) 
                        if task_names_list:
                            task_names_string = "\n".join(task_names_list) + "\n"
                            task_results = self.identify_tasks_for_project(project_name, task_names_string, dairy_txt)                
                        elif not task_names_list: 
                            task_results = self.identify_initial_tasks_for_projects(project_name, dairy_txt)
                            
                        tasks = []
                                        # Ensure task_results is a list
                        if isinstance(task_results, dict):
                            task_results = [task_results]  # Convert to a single-item list
                        elif not isinstance(task_results, list):
                            logger.warning(f"Unexpected task_results type: {type(task_results)}. Defaulting to empty list.")
                            task_results = task_results
                        for task in task_results:
                            if task.get("new_task"):
                                task_name= task.get("task_name")
                                tasks.append(
                                    {
                                        "task_name": task_name,
                                        "status": "Not Started",
                                        "priority": "Low",
                                        "assignee": ["4ec785d6-aaa2-473f-b892-2dab634925b0"]  # Replace with actual user IDs
                                    }
                                )
                        if tasks:
                            logger.info(f"Adding {len(tasks)} tasks to project ID {project_id}.")
                            result = notion_helper.add_tasks_to_project(project_id, tasks)
                            logger.debug(f"Add tasks result: {result}")
                    except Exception as e:
                        logger.error(f"Error while updating project {result.get('project_name')} (ID: {project_id}): {e}", exc_info=True)
                else:
                    logger.warning(f"Unexpected result format: {result}")
        except Exception as e:
            logger.critical(f"Critical failure in generate_projects_and_tasks_in_notion: {e}", exc_info=True)  

    def extract_projects(self, projects_names, dairy_txt) -> str:
        """ Extracts project details from diary text."""
        try:
            model = ChatOpenAI(model_name='chatgpt-4o-latest', temperature=0, api_key=OPENAI_KEY)
            if not projects_names:
                extract_prompt = self.read_md_to_formattable_string(os.path.join('data', 'identify_all_projects.md'))
            else:
                extract_prompt = self.read_md_to_formattable_string(os.path.join('data', 'extract_projects_prompt_json.md'))
            prompt_template = ChatPromptTemplate.from_messages([("system", extract_prompt)])
            parser = JsonOutputParser(pydantic_object=ProjectOutput)
            chain = prompt_template | model | parser
           
            result = chain.invoke({"projects_names": projects_names,  "json_format": parser.get_format_instructions(), "input": dairy_txt})

            try: 
                result = json.dumps(result)
            except Exception as json_err:
                logging.error(f"Error converting result to JSON: {json_err}")
                err_fix_parser = OutputFixingParser.from_llm(parser=parser, llm=model)
                result = err_fix_parser.parse(result)
            
            try:
                data = json.loads(result)
                return data
            except json.JSONDecodeError as decode_err:
                logging.error(f"Error decoding JSON: {decode_err}")
                return ""
            except TypeError as type_err:
                logging.error(f"Type error processing JSON data: {type_err}")
                return ""
            except Exception as e:
                logging.error(f"Unexpected error processing JSON data: {e}")
                return ""
            
           
        except Exception as e:
            logging.error(f"Error generating case study: {e}", exc_info=True)
            return "" 
    
    
        
    def identify_tasks_for_project(self, projects_name, existing_tasks, dairy_txt) -> str:
        """
        """
        try:
            if not OPENAI_KEY:
                logger.error("OpenAI API key is not set in environment variables.")
                raise ValueError("OpenAI API key is not set.")
            model = ChatOpenAI(model_name='chatgpt-4o-latest', temperature = 0, api_key=OPENAI_KEY)

            identify_prompt = self.read_md_to_formattable_string(os.path.join('data', 'identify_tasks_for_project.md'))
            #prompt_template = ChatPromptTemplate.from_messages([("system", dairy_prompt), "user", dairy_txt])
            prompt_template = ChatPromptTemplate.from_messages([("system", identify_prompt)])

            parser = JsonOutputParser(pydantic_object=Task)
            chain = prompt_template | model | parser
            
            #result = chain.invoke({"dairy_example_input": dairy_example_input, "dairy_example_output": dairy_example_output})
            result = chain.invoke({"projects_name": projects_name,  "json_format": parser.get_format_instructions(), "input": dairy_txt, "existing_tasks": existing_tasks})

            try: 
                result = json.dumps(result)
            except Exception as json_err:
                logging.error(f"Error converting result to JSON: {json_err}")
                err_fix_parser = OutputFixingParser.from_llm(parser=parser, llm=model)
                result = err_fix_parser.parse(result)
            
            try:
                data = json.loads(result)
                #output_data = {key: "\n".join(value) if isinstance(value, list) else value for key, value in data.items()}
                #output_json = json.dumps(output_data, indent=4)
                return data#, output_json
            except json.JSONDecodeError as decode_err:
                logging.error(f"Error decoding JSON: {decode_err}")
                return ""
            except TypeError as type_err:
                logging.error(f"Type error processing JSON data: {type_err}")
                return ""
            except Exception as e:
                logging.error(f"Unexpected error processing JSON data: {e}")
                return ""
            
           
        except Exception as e:
            logging.error(f"Error generating case study: {e}")
            return ""         
    
    def identify_initial_tasks_for_projects(self, projects_name, dairy_txt) -> str:
        """
        """
        try:
            if not OPENAI_KEY:
                logger.error("OpenAI API key is not set in environment variables.")
                raise ValueError("OpenAI API key is not set.")
            model = ChatOpenAI(model_name='chatgpt-4o-latest', temperature = 0, api_key=OPENAI_KEY)

            identify_prompt = self.read_md_to_formattable_string(os.path.join('data', 'initial_task_creation.md'))
            #prompt_template = ChatPromptTemplate.from_messages([("system", dairy_prompt), "user", dairy_txt])
            prompt_template = ChatPromptTemplate.from_messages([("system", identify_prompt)])

            parser = JsonOutputParser(pydantic_object=Task)
            chain = prompt_template | model | parser
            
            #result = chain.invoke({"dairy_example_input": dairy_example_input, "dairy_example_output": dairy_example_output})
            result = chain.invoke({"projects_name": projects_name,  "json_format": parser.get_format_instructions(), "input": dairy_txt})

            try: 
                result = json.dumps(result)
            except Exception as json_err:
                logging.error(f"Error converting result to JSON: {json_err}")
                err_fix_parser = OutputFixingParser.from_llm(parser=parser, llm=model)
                result = err_fix_parser.parse(result)
            
            try:
                data = json.loads(result)
                #output_data = {key: "\n".join(value) if isinstance(value, list) else value for key, value in data.items()}
                #output_json = json.dumps(output_data, indent=4)
                return data#, output_json
            except json.JSONDecodeError as decode_err:
                logging.error(f"Error decoding JSON: {decode_err}")
                return ""
            except TypeError as type_err:
                logging.error(f"Type error processing JSON data: {type_err}")
                return ""
            except Exception as e:
                logging.error(f"Unexpected error processing JSON data: {e}")
                return ""
            
           
        except Exception as e:
            logging.error(f"Error generating case study: {e}")
            return ""