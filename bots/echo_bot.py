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
from helpers import NotionHelpers, DairyHelpers, ProManHelpers



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
            notion_helper = NotionHelpers()
            dairy_helper = DairyHelpers()
            pm_helpers =  ProManHelpers()
            raw_diary = turn_context.activity.text
            logger.info(f"Received raw diary entry: {raw_diary}")

            structured_summary = dairy_helper.generate_dairy(raw_diary)
            next_steps = dairy_helper.generate_next_steps(structured_summary)
            final_analysis = f"{structured_summary}\n\n---\n\n{next_steps}"
            result_response = notion_helper.create_notion_page_with_case_study(final_analysis, raw_diary)
            pm_helpers.generate_projects_and_tasks_in_notion(notion_helper, raw_diary)
            await turn_context.send_activity(
                MessageFactory.text(f"{result_response}\n\n{final_analysis}")
                #MessageFactory.text(f"done.")

            )
        except Exception as e:
            logger.error(f"Error in on_message_activity: {e}")
            await turn_context.send_activity(
                MessageFactory.text("An error occurred while processing your raw diary entry.")
            )



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

