import requests

def get_latest_process_definitions(base_url):
    """
    Returns a list of the latest process definitions deployed in Camunda.
    """
    url = f"{base_url}/process-definition"
    params = {"latestVersion": "true"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def get_process_definition_xml(base_url, process_definition_id):
    """
    Returns the BPMN XML string for a given process definition ID.
    """
    url = f"{base_url}/process-definition/{process_definition_id}/xml"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("bpmn20Xml")

def get_latest_decision_definitions(base_url):
    """
    Returns a list of the latest decision definitions (DMN) deployed in Camunda.
    """
    url = f"{base_url}/decision-definition"
    params = {"latestVersion": "true"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def get_decision_definition_xml(base_url, decision_definition_id):
    """
    Returns the DMN XML string for a given decision definition ID.
    """
    url = f"{base_url}/decision-definition/{decision_definition_id}/xml"
    response = requests.get(url)
    response.raise_for_status()
    # Camunda REST API returns 'dmnXml' for decision-definition XML
    return response.json().get("dmnXml")

def get_deployment(base_url, deployment_id):
    """
    Returns deployment details for a given deployment ID.
    """
    url = f"{base_url}/deployment/{deployment_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def deploy_to_camunda(base_url, deployment_name, files_dict):
    """
    Deploys a set of files to Camunda.
    files_dict is a mapping of filename -> XML string content.
    """
    url = f"{base_url}/deployment/create"
    data = {"deployment-name": deployment_name, "deployment-source": "camunda-checker-sync"}
    files_to_upload = {name: (name, content) for name, content in files_dict.items()}
    response = requests.post(url, data=data, files=files_to_upload)
    response.raise_for_status()
    return response.json()
