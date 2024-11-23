You are tasked with extracting project names from speech-to-text input. I will provide a list of "Existing Projects" as a reference. I will try to say the word "projekt" or "project" before mentioning a project name. The project name may be misspelled due to the nature of speech-to-text conversion. Note that the answer must be in the same language as the input.

Existing Projects:
"""
{projects_names}
"""

Format Instruction: 
"""
{json_format}
"""

Requirements:
- If a project name matches one from the "Existing Projects" list (even approximately), extract the corrected name.
- If a project name is not found in the "Existing Projects" list, treat it as a new project and add it to the list, too.

Maintain all extracted project names as accurately as possible.


Input:
"""
{input}
"""

Beware:
- Consider approximate matches for project names (e.g., typo tolerance). Use the "Existing Projects" context for validation or correction.
- Ensure no duplicate project names are added to the list.

