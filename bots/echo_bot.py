# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import ChannelAccount
from typing import List
import json
import logging
import openai
import os
import sys
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import requests
from datetime import datetime
import os
import re
from typing import List, Optional
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain.output_parsers import OutputFixingParser
from datetime import date



# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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


def validate_env_variables():
    missing_vars = [key for key, value in REQUIRED_ENV_VARS.items() if not value]
    if missing_vars:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")


validate_env_variables()

class Task(BaseModel):
    project_name: str = Field(description="Name of the project.")
    task_name: str = Field(..., description="Name of the task.")
    status: str = Field(default="Not Started")#, description="Current status of the task.")
    due_date: Optional[date] = Field(..., description="Due date for the task in ISO 8601 format (YYYY-MM-DD).")
    new_task: bool = Field(description="Indicates if this is a new task.")

class ProjectOutput(BaseModel):
    project_id: Optional[str] = Field(description="Id of the project of existing project.") 
    project_name: str = Field(description="Name of the project.")
    summary: str = Field(description="Brief description or summary of the project.")
    new_project: bool = Field(description="Indicates if this is a new project.")

class EchoBot(ActivityHandler):
    async def on_members_added_activity(
       self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        #for member in members_added:
        #   if member.id != turn_context.activity.recipient.id:
        #       await turn_context.send_activity("Hello and welcome!")
        pass

    async def on_message_activity(self, turn_context: TurnContext):
        try:
            raw_diary = turn_context.activity.text
            logger.info(f"Received raw diary entry: {raw_diary}")

            structured_summary = self.generate_dairy(raw_diary)
            next_steps = self.generate_next_steps(structured_summary)
            final_analysis = f"{structured_summary}\n\n---\n\n{next_steps}"
            result_response = self.create_notion_page_with_case_study(final_analysis, raw_diary)
            self.generate_projects_and_tasks_in_notion(raw_diary)
            await turn_context.send_activity(
                MessageFactory.text(f"{result_response}\n\n{final_analysis}")
                #MessageFactory.text(f"done")

            )
        except Exception as e:
            logger.error(f"Error in on_message_activity: {e}")
            await turn_context.send_activity(
                MessageFactory.text("An error occurred while processing your raw diary entry.")
            )
        
        
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

    def markdown_to_notion_blocks(self, markdown_text: str):
        """ Converts Markdown to Notion blocks."""
        blocks = []
        try:
            lines = markdown_text.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("### "):
                    blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}})
                elif line.startswith("## "):
                    blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
                elif line.startswith("# "):
                    blocks.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
                elif line.startswith("- ") or line.startswith("* "):
                    blocks.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
                elif line == "---":
                    blocks.append({"object": "block", "type": "divider", "divider": {}})
                else:
                    blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}})
            return blocks
        except Exception as e:
            logger.error("Error converting markdown to Notion blocks", exc_info=True)
            return []

    def get_tasks_by_project(self, project_id: str) -> List[str]:
        """
        Retrieves all task names associated with a specific project by its ID.

        Args:
            project_id (str): The ID of the project to retrieve tasks for.

        Returns:
            List[str]: A list of task names associated with the project.
        """
        url = f"https://api.notion.com/v1/databases/{TASKS_DATABASE_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        
        try:
            # Query the database for tasks
            response = requests.post(url, headers=headers, json={
                "filter": {
                    "property": "Project",
                    "relation": {
                        "contains": project_id
                    }
                }
            })
            response.raise_for_status()
            
            # Parse the response
            tasks = response.json().get("results", [])
            task_names = []
            for task in tasks:
                task_name = task.get("properties", {}).get("Task name", {}).get("title", [])
                if task_name:
                    task_names.append(task_name[0].get("plain_text", ""))
            
            return task_names

        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving tasks for project {project_id}: {e}")
            return []
    
        
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
        
        

    
    def split_text_into_chunks(self, text: str, chunk_size: int = 1900):
        """
        Split the input text into smaller chunks of a given size.

        Args:
            text (str): The text to be split.
            chunk_size (int): The maximum size of each chunk.

        Returns:
            list: A list of text chunks.
        """
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        logger.debug(f"Split text into {len(chunks)} chunks.")
        return chunks
                
    def create_notion_subpage(self, parent_page_id: str, title: str, text_chunks: List[str]):
        """
        Create a subpage under the given parent page with text content split into blocks.

        Args:
            parent_page_id (str): The ID of the parent page.
            title (str): The title of the subpage.
            text_chunks (list): A list of text chunks to be added to the subpage.
        
        Returns:
            str: Result message indicating success or failure.
        """
        # Convert text chunks to Notion blocks
        blocks = []
        try:

            for chunk in text_chunks:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })

            # Define the request payload
            payload = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "Name": {
                        "title": [{"text": {"content": title}}]
                    }
                },
                "children": blocks
            }

            # Define the API endpoint and headers
            url = "https://api.notion.com/v1/pages"
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }

            # Make the POST request to create the subpage
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                logger.info("Subpage created successfully.")
                return "Subpage created successfully."
            else:
                logging.error(f"Failed to create subpage: {response.status_code} {response.text}")
                return "Failed to create subpage."
        except Exception as e:
            logger.error(f"Error creating subpage: {e}")
            return "Failed to create subpage."

    
    def create_notion_page_with_case_study(self, dairy_txt, raw_diary: str):
        """ Creates a new page in a Notion database with the provided diary text."""
        try:
            today_title = datetime.now().strftime("%d.%m.%Y")
            blocks = self.markdown_to_notion_blocks(dairy_txt)
            payload = {
                "parent": {"database_id": DATABASE_ID},
                "properties": {"Name": {"title": [{"text": {"content": today_title}}]}},
                "children": blocks
            }
            url = "https://api.notion.com/v1/pages"
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                page_id = response.json().get("id")
                logger.info(f"Created Notion page with ID: {page_id}")
                text_chunks = self.split_text_into_chunks(raw_diary)
                subpage_title = "Raw Diary Text"
                _ = self.create_notion_subpage(page_id, subpage_title, text_chunks)
                return "Page created successfully."
            else:
                return "Failed to create page."
        except Exception as e:
            logger.error(f"Error in create_notion_page_with_case_study: {e}")
            return "An error occurred while creating the Notion page."

    def query_all_projects(self):
        """
        Queries all projects from the Notion Projects database and extracts all available details.

        Returns:
            list: A list of dictionaries containing detailed project information, or an empty list if an error occurs.
        """
        url = f"https://api.notion.com/v1/databases/{PROJECTS_DATABASE_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            projects = data.get("results", [])
            project_details = []

            for project in projects:
                properties = project.get("properties", {})

                # Extract metadata and core project details
                project_id = project.get("id", "") or ""
                created_time = project.get("created_time", "") or ""
                last_edited_time = project.get("last_edited_time", "") or ""
                created_by = (project.get("created_by", {}) or {}).get("id", "") or ""
                last_edited_by = (project.get("last_edited_by", {}) or {}).get("id", "") or ""
                archived = project.get("archived", False)
                icon = (project.get("icon", {}) or {}).get("emoji", "") or ""
                cover = project.get("cover", None)
                parent = (project.get("parent", {}) or {}).get("type", "") or ""
                parent_id = (project.get("parent", {}) or {}).get("database_id", "") or ""
                url = project.get("url", "") or ""
                public_url = project.get("public_url", None)

                # Safely extract project-specific fields from properties
                project_name = (properties.get("Project name", {}).get("title", [{}])[0].get("plain_text", "") or "")
                status = (properties.get("Status", {}).get("status", {}) or {}).get("name", "") or ""
                status_color = (properties.get("Status", {}).get("status", {}) or {}).get("color", "") or ""
                owner = [person.get("id", "") for person in (properties.get("Owner", {}).get("people", []) or [])]
                completion_percentage = (properties.get("Completion", {}).get("rollup", {}) or {}).get("number", None)
                dates = properties.get("Dates", {}).get("date", {}) or {}
                priority = (properties.get("Priority", {}).get("select", {}) or {}).get("name", "") or ""
                priority_color = (properties.get("Priority", {}).get("select", {}) or {}).get("color", "") or ""
                summary = (properties.get("Summary", {}).get("rich_text", [{}])[0].get("plain_text", "") or "")
                tasks = [task.get("id", "") for task in (properties.get("Tasks", {}).get("relation", []) or [])]
                is_blocking = [relation.get("id", "") for relation in (properties.get("Is Blocking", {}).get("relation", []) or [])]
                blocked_by = [relation.get("id", "") for relation in (properties.get("Blocked By", {}).get("relation", []) or [])]
                sign_off_project = properties.get("Sign off project?", {}).get("type", "") or ""

                # Fetch page content and task details
                page_content = self.get_page_content(project_id)
                task_details = self.get_all_tasks(tasks)           
                # Append all extracted data to the project details list
                project_details.append({
                    # Metadata
                    "project_id": project_id,
                    "created_time": created_time,
                    "last_edited_time": last_edited_time,
                    "created_by": created_by,
                    "last_edited_by": last_edited_by,
                    "archived": archived,
                    "icon": icon,
                    "cover": cover,
                    "parent": parent,
                    "parent_id": parent_id,
                    "url": url,
                    "public_url": public_url,

                    # Project Properties
                    "project_name": project_name,
                    "status": status,
                    "status_color": status_color,
                    "owner": owner,
                    "completion_percentage": completion_percentage,
                    "dates": dates,
                    "priority": priority,
                    "priority_color": priority_color,
                    "summary": summary,
                    "tasks": tasks,
                    "is_blocking": is_blocking,
                    "blocked_by": blocked_by,
                    "sign_off_project": sign_off_project,
                    "page_content": page_content,
                    "tasks_details": task_details
                })               

            return project_details

        except requests.exceptions.RequestException as e:
            logging.error(f"Error querying projects: {e}")
            return []   


    def query_all_tasks(self):
        """
        Queries all tasks from the Notion Tasks database.

        Returns:
            list: A list of task objects, or an empty list if an error occurs.
        """
        url = f"https://api.notion.com/v1/databases/{TASKS_DATABASE_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            tasks = data.get("results", [])
            return tasks
        except requests.exceptions.RequestException as e:
            logging.error(f"Error querying tasks: {e}")
            return []

    def get_all_tasks(self, task_ids):
        """
        Retrieves details for all tasks associated with a project.

        Args:
            task_ids (list): A list of task IDs.

        Returns:
            list: A list of dictionaries containing task details.
        """
        tasks = []
        for task_id in task_ids:
            task_details = self.get_task_details(task_id)
            if task_details:
                tasks.append(task_details)
        return tasks


    
    def get_task_details(self, task_id):
        """
        Retrieves detailed information for a single task, including custom properties.

        Args:
            task_id (str): The ID of the task page.

        Returns:
            dict: A dictionary containing task details, or None if an error occurs.
        """
        url = f"https://api.notion.com/v1/pages/{task_id}"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            task = response.json()

            # Extract task properties
            properties = task.get("properties", {})
            completed_on_date = properties.get("Completed on", {}).get("date", None)
            completed_on = completed_on_date.get("start", "") if completed_on_date else ""
            # Extract all fields with default fallbacks
            task_details = {
                "task_id": task_id,
                "task_name": (properties.get("Task name", {}).get("title", [{}])[0].get("plain_text", "") or ""),
                "status": (properties.get("Status", {}).get("status", {}) or {}).get("name", "") or "",
                "status_color": (properties.get("Status", {}).get("status", {}) or {}).get("color", "") or "",
                "due_date": (properties.get("Due", {}).get("date", {}) or {}).get("start", "") or "",
                "completed_on": (properties.get("Completed on", {}).get("date", {}) or {}).get("start", "") or "",
                "priority": (properties.get("Priority", {}).get("select", {}) or {}).get("name", "") or "",
                "priority_color": (properties.get("Priority", {}).get("select", {}) or {}).get("color", "") or "",
                "tags": [tag.get("name", "") for tag in (properties.get("Tags", {}).get("multi_select", []) or [])],
                "assignee": [person.get("id", "") for person in (properties.get("Assignee", {}).get("people", []) or [])],
                "delay": (properties.get("Delay", {}).get("formula", {}) or {}).get("number", "") or "",
                "sub_tasks": [sub_task.get("id", "") for sub_task in (properties.get("Sub-tasks", {}).get("relation", []) or [])],
                "parent_task": [parent_task.get("id", "") for parent_task in (properties.get("Parent-task", {}).get("relation", []) or [])],
                "project": [project.get("id", "") for project in (properties.get("Project", {}).get("relation", []) or [])],
            }


            return task_details

        except requests.exceptions.RequestException as e:
            logging.error(f"Error retrieving task {task_id}: {e}")
            return None
        except AttributeError as e:
            logging.error(f"Attribute error in task {task_id}: {e}")
            return None




    
        
    def get_project_by_id(self, project_id):
        """
        Retrieves details of a specific project by its ID.

        Args:
            project_id (str): The ID of the project to retrieve.

        Returns:
            dict: A dictionary containing detailed project information, or None if the project is not found or an error occurs.
        """
        url = f"https://api.notion.com/v1/pages/{project_id}"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        try:
            # Make the GET request to retrieve the project
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            project = response.json()

            # Extract properties
            properties = project.get("properties", {})
            project_details = {
                "project_id": project.get("id", ""),
                "created_time": project.get("created_time", ""),
                "last_edited_time": project.get("last_edited_time", ""),
                "created_by": project.get("created_by", {}).get("id", ""),
                "last_edited_by": project.get("last_edited_by", {}).get("id", ""),
                "archived": project.get("archived", False),
                "icon": project.get("icon", {}).get("emoji", ""),
                "cover": project.get("cover", None),
                "parent_type": project.get("parent", {}).get("type", ""),
                "parent_id": project.get("parent", {}).get("database_id", ""),
                "url": project.get("url", ""),
                "project_name": properties.get("Project name", {}).get("title", [{}])[0].get("plain_text", ""),
                "status": properties.get("Status", {}).get("status", {}).get("name", ""),
                "status_color": properties.get("Status", {}).get("status", {}).get("color", ""),
                "owner": [person.get("id") for person in properties.get("Owner", {}).get("people", [])],
                "dates": properties.get("Dates", {}).get("date", {}),
                "priority": properties.get("Priority", {}).get("select", {}).get("name", ""),
                "priority_color": properties.get("Priority", {}).get("select", {}).get("color", ""),
                "summary": properties.get("Summary", {}).get("rich_text", [{}])[0].get("plain_text", ""),
            }

            return project_details

        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving project {project_id}: {e}")
            return None
        
        

    def get_page_content(self, page_id):
        """
        Retrieves and extracts only the text content from a Notion page, ignoring empty or irrelevant blocks.

        Args:
            page_id (str): The unique ID of the Notion page.

        Returns:
            list: A list of strings containing the page's text content.
        """
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            blocks = data.get("results", [])
            
            # Extract text content from blocks
            page_content = []
            for block in blocks:
                block_type = block.get("type", "")
                block_data = block.get(block_type, {})
                rich_text_list = block_data.get("rich_text", [])

                # Concatenate all plain text from rich_text fields
                block_text = "".join([item.get("plain_text", "") for item in rich_text_list])

                # Only include non-empty text
                if block_text.strip():
                    page_content.append(block_text)

            return page_content

        except requests.exceptions.RequestException as e:
            logging.error(f"Error retrieving page content: {e}")
            return []
    
    def get_page_content_block_id(self, page_id):
        """
        Retrieves the detailed content of a Notion page, including written text and blocks.

        Args:
            page_id (str): The unique ID of the Notion page.

        Returns:
            list: A list of dictionaries containing the page's block content, or an empty list if an error occurs.
        """
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            blocks = data.get("results", [])
            
            # Process block content
            page_content = []
            for block in blocks:
                block_type = block.get("type", "")
                block_data = block.get(block_type, {})
                text = ""

                # Extract text from text blocks
                if "text" in block_data:
                    text = "".join(
                        [item["plain_text"] for item in block_data.get("text", [])]
                    )
                
                page_content.append({
                    "block_id": block.get("id", ""),
                    "type": block_type,
                    "text": text,
                    "data": block_data,
                })

            return page_content

        except requests.exceptions.RequestException as e:
            logging.error(f"Error retrieving page content: {e}")
            return []

    def add_tasks_to_project(self, project_id, tasks):
        """
        Adds one or more tasks to a project in the Notion database.

        Args:
            project_id (str): The ID of the project to which the tasks will be linked.
            tasks (list of dict): A list of task dictionaries. Each dictionary contains task details, such as:
                - task_name (str): The name of the task.
                - status (str, optional): The status of the task.
                - due_date (str, optional): The due date in ISO 8601 format (YYYY-MM-DD).
                - priority (str, optional): The priority of the task.
                - assignee (list, optional): List of assignee IDs.

        Returns:
            str: A message indicating success or failure for each task.
        """
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        results = []

        for task in tasks:
            try:
                # Build the task properties
                properties = {
                    "Task name": {
                        "title": [{"text": {"content": task["task_name"]}}]
                    },
                    "Project": {
                        "relation": [{"id": project_id}]
                    },
                    "Status": {
                        "status": {"name": task.get("status")} if task.get("status") else None
                    },
                    "Due": {
                        "date": {"start": task.get("due_date")} if task.get("due_date") else None
                    },
                    "Priority": {
                        "select": {"name": task.get("priority")} if task.get("priority") else None
                    },
                    "Assignee": {
                        "people": [{"id": person_id} for person_id in (task.get("assignee") or [])]
                    }
                }

                # Remove None properties
                properties = {k: v for k, v in properties.items() if v is not None}

                # Define the request payload
                payload = {
                    "parent": {"database_id": TASKS_DATABASE_ID},
                    "properties": properties
                }

                # Make the POST request to create the task
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()

                # Parse the response
                task_id = response.json().get("id", "")
                results.append(f"Task '{task['task_name']}' created successfully with ID: {task_id}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error creating task '{task['task_name']}': {e}")
                results.append(f"Failed to create task '{task['task_name']}': {e}")

        return "\n".join(results)

    def add_project(self, project_name, status=None, owner=None, dates=None, priority=None, summary=None):
        """
        Adds a new project to the Notion Projects database.

        Args:
            project_name (str): The name of the project (required).
            status (str): The status of the project (optional).
            owner (list): List of owner IDs (optional).
            completion (float): Completion percentage (optional).
            dates (dict): A dictionary with "start" and "end" keys for project dates (optional).
            priority (str): The priority of the project (optional).
            summary (str): A brief summary of the project (optional).

        Returns:
            str: A message indicating success or failure.
        """
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        try:
            # Build the properties payload
            properties = {
                "Project name": {
                    "title": [{"text": {"content": project_name}}]
                },
                "Status": {
                    "status": {"name": status} if status else None
                },
                "Owner": {
                    "people": [{"id": person_id} for person_id in (owner or [])]
                },
                "Dates": {
                    "date": {"start": dates.get("start", ""), "end": dates.get("end", "")} if dates else None
                },
                "Priority": {
                    "select": {"name": priority} if priority else None
                },
                "Summary": {
                    "rich_text": [{"text": {"content": summary}}] if summary else None
                },
            }

            # Clean up the properties by removing None values
            properties = {key: value for key, value in properties.items() if value is not None}

            # Define the request payload
            payload = {
                "parent": {"database_id": PROJECTS_DATABASE_ID},
                "properties": properties  
            }

            # Make the POST request to add the project
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            # Parse response
            data = response.json()
            project_id = data.get("id", "")
            logger.info(f"Project '{project_name}' created successfully with ID: {project_id}")
            return project_id, f"Project '{project_name}' created successfully with ID: {project_id}"

        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding project '{project_name}': {e}")
            if e.response:
                logger.error(f"Response content: {e.response.text}")
            return f"Failed to add project '{project_name}': {e}"

    def generate_projects_and_tasks_in_notion(self, dairy_txt):
        try: 
            # Step 1: Query all existing projects
            logger.info("Querying all projects from Notion.")
            projects = self.query_all_projects()
            project_names = [
                f"Project-Id: {project['project_id']}, Project-Name: {project['project_name']}\n"
                for project in projects
            ]
    
            # Step 2: Extract projects based on the diary text
            logger.info("Extracting projects from diary text.")
            results = self.extract_projects(project_names, dairy_txt)
            if not results:
                logger.warning("No projects were extracted from the diary text.")        
            
            # Step 3: Process each result
            for result in results:
                if result.get("new_project") == True:
                    try: 

                        project_name=result.get("project_name")
                        logger.info(f"Adding new project: {project_name}.")

                        project_id, status = self.add_project(
                            project_name=project_name,
                            status="Backlog",
                            owner=["4ec785d6-aaa2-473f-b892-2dab634925b0"],  # Replace with actual user ID(s)
                            priority="Low",
                            summary=result.get("summary")
                        )

                        task_names_list = self.get_tasks_by_project(project_id) 
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
                            result = self.add_tasks_to_project(project_id, tasks)
                            logger.debug(f"Add tasks result: {result}")
                    except Exception as e:
                        logger.error(f"Error while processing new project {result.get('project_name')}: {e}", exc_info=True)
                     
                elif result.get("new_project") == False:
                    try:
                        project_id = result.get("project_id")
                        project_name=result.get("project_name")
                        task_names_list = self.get_tasks_by_project(project_id) 
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
                            result = self.add_tasks_to_project(project_id, tasks)
                            logger.debug(f"Add tasks result: {result}")
                    except Exception as e:
                        logger.error(f"Error while updating project {result.get('project_name')} (ID: {project_id}): {e}", exc_info=True)
                else:
                    logger.warning(f"Unexpected result format: {result}")
        except Exception as e:
            logger.critical(f"Critical failure in generate_projects_and_tasks_in_notion: {e}", exc_info=True)  


# gunicorn --bind 0.0.0.0 --worker-class aiohttp.worker.GunicornWebWorker app:APP


# if __name__ == "__main__":
#     bot = EchoBot()
#     #bot.get_task_details("147dcd2a-1951-80a4-bae7-f0f495909e9f")
#     # Fetch all project details
#     # List of tasks to add
#     tasks = [
#         {
#             "task_name": "Design Marketing Materials",
#             "status": "Not Started",
#             "due_date": "2024-11-30",
#             "priority": "High",
#             "assignee": ["4ec785d6-aaa2-473f-b892-2dab634925b0"]  # Replace with actual user IDs
#         },
#         {
#             "task_name": "Prepare Budget Plan",
#             "status": "In Progress",
#             "due_date": "2024-12-05",
#             "priority": "Medium",
#             "assignee": []
#         }
#     ]

#     # Add tasks to the project
#     #result = bot.add_tasks_to_project("144dcd2a-1951-81de-9ea3-e31aac824b3f", tasks)
#     #print(result)
#     # Test the add_project_with_template method
#     #project_details = bot.get_project_by_id("144dcd2a-1951-81de-9ea3-e31aac824b3f")
    


#     # if project_details:
#     #     print("Project Details:")
#     #     print(f"Project ID: {project_details['project_id']}")
#     #     print(f"Project Name: {project_details['project_name']}")
#     #     print(f"Status: {project_details['status']} (Color: {project_details['status_color']})")
#     #     print(f"Owner: {project_details['owner']}")
#     #     print(f"Dates: {project_details['dates']}")
#     #     print(f"Priority: {project_details['priority']} (Color: {project_details['priority_color']})")
#     #     print(f"Summary: {project_details['summary']}")
#     #     print(f"Created Time: {project_details['created_time']}")
#     #     print(f"Last Edited Time: {project_details['last_edited_time']}")
#     #     print(f"Created By: {project_details['created_by']}")
#     #     print(f"Last Edited By: {project_details['last_edited_by']}")
#     #     print(f"Archived: {project_details['archived']}")
#     #     print(f"URL: {project_details['url']}")
#     # else:
#     #     print("Project not found or an error occurred.")

    
#     # project_id, result = bot.add_project(
#     #     project_name="New Marketing Campaign 2",
#     #     status="In Progress",
#     #     owner=["4ec785d6-aaa2-473f-b892-2dab634925b0"],  # Replace with actual user ID(s)
#     #     dates={"start": "2024-11-25", "end": "2024-12-15"},
#     #     priority="High",
#     #     summary="A new campaign to promote our latest product."
#     # )  
    
#     projects = bot.query_all_projects()
#     project_names = []
#     for project in projects:
#         project_names.append(
#             f"Project-Id: {project['project_id']}, Project-Name: {project['project_name']}\n"

#         )
#     dairy_txt = """ Gestern war der 22.11 2024 es war der Freitag. Gestern habe ich wieder 30 Milligramm Elvanse genommen und Ja, ich war den ganzen Tag sehr gereit, schlecht drauf und mir ging es gar nicht gut damit leider Ich weiß nicht, ob das irgendwie mit der Arbeit zusammenhing, weil ich hier in so einem **** Workshop drin hängen musste und halt zwischen ja. Zuhören musste und eigentlich nicht gebraucht wurde und deswegen einfach nur sinnlos rum saß, aber mich auch nicht auf andere Dinge vereinlassen konnte ich. Teil irgendwie doch sehr schwer, wieder was zu machen und. Ich frag mich ob, ob ich zu wenig nehme oder ob ich jetzt noch mal daran versuchen sollte, nur die Hälfte zu nehmen. Morgen werde ich mal die Hälfte tableternehmen, um zu testen, wie es mir dann geht. Ich denke, ich werde morgen dann auch mal den Kaffee weglassen oder vielleicht nur eine kleine Tasse zwingen? Ich muss mal gucken. Gestern habe ich dann eigentlich den ganzen Tag pokémon gespielt, statt zu arbeiten, weil ich mich auch gar nicht irgendwie wegen dem ganzen Lerne und den Workshop konzentrieren konnte. Ja. Es ärgert mich einfach immer wieder, dass ich meine Medikamente nehme und dann meinen Tag verschwinde für eine Arbeit, die mir nichts bedeutet, die mir keinen Spaß macht, die mir mir die Firma **** ist und ich mir einfach nur denk ihr könnt mich alle mal, ich will mich selbständig machen. Ich will mein eigenes Ding drehen. Ich will in Arbeit Sachen arbeiten, die mir wichtig sind. Und war ich da mit Vanessa in München, Sabrina, der Geburtstag und hat uns zu einem Persischen Restaurant eingeladen? Wir haben dort gegessen, das war sehr lecker. Es hat Spaß gemacht, habe mir klar, da unterhalten Vanessa saß neben mir aber auch hier. Ich war extrem zitiere ich meine Beine haben die ganze Zeit gesprungen, die hat eine Unruhe und eigentlich genau alles das mit was eigentlich von den Medikamenten weg war, ist jetzt wieder da. Ich habe auch das Gefühl, dass es erst wieder da, seit ich eben mehr nehme und diese anfängliche Euphorie weg ist. Seit letztem Donnerstag, das war vor 8 Tagen, also war das der ja 16 oder 17 oder so. Unter der Theorie, die ich habe es, dass ich vielleicht durch den ganzen Zucker, den ich probiert habe, meinen Stoffwechsel so hoch gejagt hat, dass die Medikamente schneller rausgegangen sind. Deswegen werde ich jetzt mal die folgende Woche versuchen, ja. Doch lieber schauen mein Glücksspiel interkontrolle zu halten und morgens dann vielleicht kein ja Zucker und so weiter zu konsumieren, sondern eher bei den Haferflocken zu bleiben. Das muss ich ausprobieren, das ist ein to do für die nächste Woche.
 
# Und heute ist der 23.11 2024 es ist ein Samstag und klar, da schläft ja bei uns und wir haben uns in der Früh sehr schön alle unterhalten. Ich hatte Spaß und haben die Medikamente sehr gut gewirkt. Und weil der Kaffee eben so gut geschmeckt habe ich noch ne zweite Tasse getrunken und danach habe ich eigentlich schon gemerkt, dass es angefangen hat, dass ich mich irgendwie unwohl fühlen und bevor ich da davor dieses Glückliche und wir reden miteinander, das geht mir gut hatte hab ich jetzt halt diese innere Unruhe und auch diesen sowas ich muss mich bewegen und irgendwie ist alles nicht so angenehm. Ja, ich habe jetzt das nochmal was gegessen. Ich hatte eigentlich auch mittags über eine kleine Portion Nudeln gegessen. Jetzt habe ich 4 Brote mit Frischkäse gegessen und ja, jetzt gucken wir mal. Ich habe einen Beruhigungsticket getrunken und ich weiß auf jeden Fall. Die Mädels sind ja heute Abend nicht da, mal gucken, wie es mir da auch geht, wenn das alles ein bisschen abgekommen hat ja. Jetzt sitz ich von meinem Rechner und ich versuche mich irgendwie in Anführungszeichen zu motivieren oder aufzuraffen, was zu machen und irgendwie weiß ich auch nicht wirklich, was ich machen soll. Deswegen werde ich jetzt über das Tagebuch AI Projekt reden. Ich fand's per Lea aktuell sehr cool, einfach hier was zu einzusprechen und ein Tagebuch einschätzen zu bekommen und ich bekomm ja auch schon meine Tous und ähnliches und ich denke, ich würde das ganze Ding ein bisschen weiter schreiben wollen und schauen, dass ich mir jetzt im Endeffekt ne. Anlege, die ich immer weiter ja optimier verbessert et cetera und. Ja, mal gucken, wie sich das Halt anfühlt beziehungsweise wie was ich da machen kann, lass uns über Features für dieses Projekt reden. Feature Nummer 1? Für Tagebuch-KI-Projekt: Ich würde ganz gern dieses Nortion Projekt Template befüllen mit der KI von mein Tagebucheinträgen, aber ich möchte auch noch mal so n Tagesplanung Schnittstelle haben, die im Endeffekt in der Lage ist, einmal Nocion anzusprechen und zu schauen, welche Projekte gibt es denn schon? Anhand dieser Liste soll dann im Endeffekt meine Spracheingabe gecheckt werden und geschaut werden, ob ich über diese Projekte was gesagt habe, wenn ich zu diesem Projekten was gesagt habe, so ein eben innerhalb dieses Projektes neue to do's angelegt werden sollen und ja. Vorher schon meine Zusammenfassung Was am Vortag kann ein alles passiert ist und was ich schon erledigt habe. So herrscht in der Lage tatsächlich mein Tag sehr schnell zu planen und mehr verschiedene Aufgaben anlegen zu lassen, das würde ich dadurch machen, dass ich zum einen eben die Projektteil kenne, wenn Projekte noch nicht da sind, dann müsste tatsächlich geprüft werden, ob ein neues Projekt angelegt werden muss, wenn so, dann sollte es angelegt werden und die neuen to do's damit reingelegt. So habe ich eine iterative Schleife für die nächsten Tage, dass wenn ich eben über diese Projekte rede, dann tatsächlich auch diese Informationen da reingehen. So kann ich im Endeffekt eine komplette KI gesteuert und sprachgesteuert. Cracked Organisation für mich aufsetzen, die so funktioniert, wie ich das gerne hätte und nicht wie irgendwelche. Start UPS dieses für sich überlegt haben ich möchte mein eigenes System und ja, genau. Weiterhin würde ich ganz gern die kostenlose Variante der Sentimentanalyse von Georgia einbauen, um mehr als störungsbarometer über mein Tagebuch zu bekommen. Genau das ist auch ganz cool, ja."""
#     results = bot.extract_projects(project_names, dairy_txt)
    
    
#     for result in results:
#         if result.get("new_project") == True: 
#             project_id, status = bot.add_project(
#                 project_name=result.get("project_name"),
#                 status="Backlog",
#                 owner=["4ec785d6-aaa2-473f-b892-2dab634925b0"],  # Replace with actual user ID(s)
#                 priority="Low",
#                 summary=result.get("summary")
#             )  
#             task_results = bot.identify_tasks_for_project(result.get("project_name"), dairy_txt)
#             tasks = []
#             for task in task_results.get("task_name"): 
#                 tasks.append(
#                     {
#                         "task_name": task,
#                         "status": "Not Started",
#                         "priority": "Low",
#                         "assignee": ["4ec785d6-aaa2-473f-b892-2dab634925b0"]  # Replace with actual user IDs
#                     }
#                 )
#             result = bot.add_tasks_to_project(project_id, tasks)
#             print(result)
#         elif result.get("new_project") == False:
#             project_id = result.get("project_id")
#             project_name=result.get("project_name")
#             task_results = bot.identify_tasks_for_project(result.get("project_name"), dairy_txt)
#             tasks = []
#             for task in task_results.get("task_name"): 
#                 tasks.append(
#                     {
#                         "task_name": task,
#                         "status": "Not Started",
#                         "priority": "Low",
#                         "assignee": ["4ec785d6-aaa2-473f-b892-2dab634925b0"]  # Replace with actual user IDs
#                     }
#                 )
#             result = bot.add_tasks_to_project(project_id, tasks)
#             print(result)
#         #print(str(task_results))
    
    
#     # project_id, result = bot.add_project(
#     #     project_name="New Marketing Campaign 2",
#     #     status="In Progress",
#     #     owner=["4ec785d6-aaa2-473f-b892-2dab634925b0"],  # Replace with actual user ID(s)
#     #     dates={"start": "2024-11-25", "end": "2024-12-15"},
#     #     priority="High",
#     #     summary="A new campaign to promote our latest product."
#     # )  
    
#     ### query_all_projects
#     #projects = bot.query_all_projects()
#     # for project in projects:
#     #     print(f"Project ID: {project['project_id']}")
#     #     print(f"Project Name: {project['project_name']}")
#     #     print(f"Status: {project['status']} (Color: {project['status_color']})")
#     #     print(f"Owner: {project['owner']}")
#     #     print(f"Completion Percentage: {project['completion_percentage']}")
#     #     print(f"Dates: {project['dates']}")
#     #     print(f"Priority: {project['priority']} (Color: {project['priority_color']})")
#     #     print(f"Summary: {project['summary']}")
#     #     print(f"Tasks: {project['tasks']}")
#     #     print(f"Blocking Projects: {project['is_blocking']}")
#     #     print(f"Blocked By Projects: {project['blocked_by']}")
#     #     print(f"Sign Off Project Type: {project['sign_off_project']}")
#     #     print(f"Icon: {project['icon']}")
#     #     print(f"Cover: {project['cover']}")
#     #     print(f"Parent Type: {project['parent']} (ID: {project['parent_id']})")
#     #     print(f"Created Time: {project['created_time']}")
#     #     print(f"Last Edited Time: {project['last_edited_time']}")
#     #     print(f"Created By: {project['created_by']}")
#     #     print(f"Last Edited By: {project['last_edited_by']}")
#     #     print(f"Archived: {project['archived']}")
#     #     print(f"URL: {project['url']}")
#     #     print(f"Public URL: {project['public_url']}")
#     #     print(f"Page Content: {project['page_content']}")
#     #     print(f"Tasks Details:")
#     #     for task in project["tasks_details"]:
#     #         print(f"  - Task Name: {task['task_name']}")
#     #         print(f"    Status: {task['status']}")
#     #         print(f"    Due Date: {task['due_date']}")
#     #         print(f"    Priority: {task['priority']}")
#     #     print("---")
    

    


#     # Query all tasks using the instance
#     # tasks = bot.query_all_tasks()
#     # print("\nTasks:")
#     # for task in tasks:
#     #     #task_name = task["properties"]["Name"]["title"][0]["text"]["content"]
#     #     print(task)

