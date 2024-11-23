You are tasked with extracting all relevant tasks related to a given project from my diary entries. Identify all tasks, actions, or plans mentioned in the diary entry that are relevant to the given project name. Ignore irrelevant details or tasks not related to the specified project. Note that the answer must be in the same language as the input.

Project Name: (This is the name of the project you need to focus on.)
"""
{projects_name} 
"""

Format Instruction: 
"""
{json_format}
"""

Diary Entry: (This contains all the information, including tasks and irrelevant parts.)
"""
{input}
""" 

Beware:
Tasks might not always be explicitly labeled; use context clues to infer relevancy.
Ensure extracted tasks are complete and actionable, maintaining clarity and accuracy.
Ignore headers, footers, intros, outros, or unrelated notes in the diary entry.
