You are tasked with extracting project names from speech-to-text input. I will try to say the word "projekt" or "project" before mentioning a project name. The project name may be misspelled due to the nature of speech-to-text conversion.  Maintain all extracted project names as accurately as possible. Ensure no duplicate project names are added to the list. Note that the answer must be in the same language as the input. 

Allowed project name structure:
- Company + ProjectName (Reply Tipgeberbot)
- Project (AI Tagebuch)
- Company (Adciting)

Format Instruction: 
"""
{json_format}
"""

Input:
"""
{input}
"""

Beware:
- Consider approximate matches for project names (e.g., typo tolerance).
- Ensure no duplicate project names are added to the list.
- Set "new_project" for every project name always to True.
- There could be multiple projects hidden in the input, identify all.
- Note that the tasks name must be in the same language as the input.