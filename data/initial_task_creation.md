You are tasked with extracting all relevant tasks related to a given project from my diary entries. Identify all tasks, actions, or plans mentioned in the diary entry that are relevant to the given project name.
Note that the tasks name must be in the same language as the input.

Project Name: {projects_name}

Format Instruction:
{json_format}

Important Notes:
1. Focus solely on identifying all relevant tasks related to the project from the diary entry.
2. Set "new_task": true`
3. Tasks might not always be explicitly labeled; use context clues to infer relevancy.
4. Ensure extracted tasks are complete, actionable, and avoid duplication.
5. Ignore unrelated notes, headers, footers, or non-task content.
6. Note that the tasks name must be in the same language as the input.

Diary Entry:
{input}