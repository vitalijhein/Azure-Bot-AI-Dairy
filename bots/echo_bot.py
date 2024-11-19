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

NOTION_API_KEY = os.environ.get("NotionAPIKey", "")  # Set your Notion API key in the environment
DATABASE_ID = os.environ.get("NotionDatabaseId", "")  # Set your Notion database ID in the environment
OPENAI_KEY = os.environ.get("OpenAIKey", "")



class EchoBot(ActivityHandler):
    async def on_members_added_activity(
       self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        #for member in members_added:
        #   if member.id != turn_context.activity.recipient.id:
        #       await turn_context.send_activity("Hello and welcome!")
        pass

    async def on_message_activity(self, turn_context: TurnContext):
        raw_diary = turn_context.activity.text
        structured_summary = self.generate_dairy(raw_diary)
        next_steps = self.generate_next_steps(structured_summary)
        final_analysis = f"{structured_summary}\n\n---\n\n{next_steps}"
        result_response = self.create_notion_page_with_case_study(final_analysis, raw_diary)

        return await turn_context.send_activity(
            MessageFactory.text(f"{result_response}\n\n{final_analysis}")
        )
        
        
    def read_md_to_formattable_string(self, file_path):
        """
        Read a markdown file and return its content as a string.

        Args:
            file_path (str): The path to the markdown file.

        Returns:
            str: The content of the markdown file, or an empty string if an error occurs.
        """
        try: 
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return content
        except Exception as e:
            logging.error(f"Error while reading markdown file {file_path}: {e}")
            return "" 
        
    def generate_dairy(self, dairy_txt) -> str:
        """
        Generate a case study based on the provided placeholder.

        Args:
            req (func.HttpRequest): The HTTP request containing the placeholder in parameters or JSON body.

        Returns:
            str: The generated case study, or an empty string if an error occurs.
        """
        try:
            model = ChatOpenAI(model_name='chatgpt-4o-latest', temperature = 1, api_key=OPENAI_KEY)
            dairy_example_input = self.read_md_to_formattable_string(os.path.join('data', 'example_input.md'))
            dairy_example_output = self.read_md_to_formattable_string(os.path.join('data', 'example_output.md'))

            dairy_prompt = self.read_md_to_formattable_string(os.path.join('data', 'dairy_summary_prompt copy 2.md'))
            #prompt_template = ChatPromptTemplate.from_messages([("system", dairy_prompt), "user", dairy_txt])
            prompt_template = ChatPromptTemplate.from_messages([("system", dairy_prompt)])

            parser = StrOutputParser()
            chain = prompt_template | model | parser
            
            #result = chain.invoke({"dairy_example_input": dairy_example_input, "dairy_example_output": dairy_example_output})
            result = chain.invoke({"raw_dairy": dairy_txt})

            return result
           
        except Exception as e:
            logging.error(f"Error generating case study: {e}")
            return ""
        
    def generate_next_steps(self, structured_summary) -> str:
        """
        Generate a case study based on the provided placeholder.

        Args:
            req (func.HttpRequest): The HTTP request containing the placeholder in parameters or JSON body.

        Returns:
            str: The generated case study, or an empty string if an error occurs.
        """
        try:
            model = ChatOpenAI(model_name='chatgpt-4o-latest', temperature = 0.5, api_key=OPENAI_KEY)
            next_steps_prompt = self.read_md_to_formattable_string(os.path.join('data', 'dairy_next_steps_prompt.md'))
            prompt_template = ChatPromptTemplate.from_messages([("system", next_steps_prompt), "user", structured_summary])
            parser = StrOutputParser()
            chain = prompt_template | model | parser
            
            result = chain.invoke({})
            return result
           
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
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
        
    def markdown_to_notion_blocks(self, markdown_text: str):
        """
        Converts a Markdown string to a list of Notion blocks.
        
        Args:
            markdown_text (str): The Markdown text to convert.
        
        Returns:
            list: A list of Notion blocks.
        """
        blocks = []
        
        lines = markdown_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Convert headings
            if line.startswith("### "):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            elif line.startswith("## "):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith("# "):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            
            # Convert unordered list items
            elif line.startswith("- ") or line.startswith("* "):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            
            # Convert thematic break
            elif line == "---":
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
            
            # Convert inline code
            elif line.startswith("`") and line.endswith("`"):
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line[1:-1], "code": True}}]
                    }
                })
            
            # Default to a paragraph
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })
        
        return blocks

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
            return "Subpage created successfully."
        else:
            logging.error(f"Failed to create subpage: {response.status_code} {response.text}")
            return "Failed to create subpage."

    
    def create_notion_page_with_case_study(self, dairy_txt, raw_diary: str):
        """
        Creates a new page in a Notion database with today's date as the title
        and inserts the generated case study content, formatted from Markdown.
        
        Args:
            case_study (str): The content to be added to the new Notion page.
        
        Returns:
            dict: The response from the Notion API.
        """
        # Format today's date as the title
        today_title = datetime.now().strftime("%d.%m.%Y")
        
        # Convert Markdown to Notion blocks
        blocks = self.markdown_to_notion_blocks(dairy_txt)
        
        # Define the request payload
        payload = {
            "parent": {"database_id": DATABASE_ID},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": today_title}}]
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
        
        # Make the POST request to create the page
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            # Get the ID of the created page
            page_id = response.json().get("id")
            
            # Split the raw diary text into chunks
            text_chunks = self.split_text_into_chunks(raw_diary)
            
            # Create a subpage under the main page with the raw diary text
            subpage_title = "Raw Diary Text"
            subpage_result = self.create_notion_subpage(page_id, subpage_title, text_chunks)
            
            
            return "Page created successfully."
        else:
            return "Failed to create page."
        #return response.json()


# gunicorn --bind 0.0.0.0 --worker-class aiohttp.worker.GunicornWebWorker app:APP