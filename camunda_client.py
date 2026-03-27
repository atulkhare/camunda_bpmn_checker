import requests
from config import CAMUNDA_REST_URL

def get_latest_process_definitions():
    """
    Returns a list of the latest process definitions deployed in Camunda.
    """
    url = f"{CAMUNDA_REST_URL}/process-definition"
    params = {"latestVersion": "true"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def get_process_definition_xml(process_definition_id):
    """
    Returns the BPMN XML string for a given process definition ID.
    """
    url = f"{CAMUNDA_REST_URL}/process-definition/{process_definition_id}/xml"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("bpmn20Xml")
