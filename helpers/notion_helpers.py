import logging
import os 
import requests
from datetime import datetime


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

class NotionHelpers:
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

    def markdown_to_notion_blocks(self, markdown_text: str) -> list:
        """
        Converts a Markdown string into a list of Notion-compatible block objects.

        Args:
            markdown_text (str): The Markdown string to be converted.

        Returns:
            list: A list of Notion block objects.
        """
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
            self.logger.error("Error converting markdown to Notion blocks", exc_info=True)
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
            self.logger.error(f"Error retrieving tasks for project {project_id}: {e}")
            return []
        
    # def get_tasks_by_project(self, project_id: str) -> List[str]:
    #     """
    #     Retrieves all task names associated with a specific project by its ID.

    #     Args:
    #         project_id (str): The ID of the project to retrieve tasks for.

    #     Returns:
    #         List[str]: A list of task names associated with the project.
    #     """
    #     url = f"https://api.notion.com/v1/databases/{TASKS_DATABASE_ID}/query"
    #     headers = {
    #         "Authorization": f"Bearer {NOTION_API_KEY}",
    #         "Content-Type": "application/json",
    #         "Notion-Version": "2022-06-28",
    #     }
        
    #     try:
    #         # Query the database for tasks
    #         response = requests.post(url, headers=headers, json={
    #             "filter": {
    #                 "property": "Project",
    #                 "relation": {
    #                     "contains": project_id
    #                 }
    #             }
    #         })
    #         response.raise_for_status()
            
    #         # Parse the response
    #         tasks = response.json().get("results", [])
    #         task_names = []
    #         for task in tasks:
    #             task_name = task.get("properties", {}).get("Task name", {}).get("title", [])
    #             if task_name:
    #                 task_names.append(task_name[0].get("plain_text", ""))
            
    #         return task_names

    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"Error retrieving tasks for project {project_id}: {e}")
    #         return []

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
                 # Default `due_date` to today's date if not provided
                due_date = task.get("due_date")
                if not due_date:
                    due_date = datetime.today().strftime('%Y-%m-%d')
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
    
        # Default `dates` to today's date if not provided
        if dates is None:
            today = datetime.today().strftime('%Y-%m-%d')
            dates = {"start": today, "end": None}
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
