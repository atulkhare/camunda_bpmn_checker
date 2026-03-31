import sys
from config import SOURCE_CAMUNDA_REST_URL, TARGET_CAMUNDA_REST_URL
from camunda_client import (
    get_latest_process_definitions,
    get_process_definition_xml,
    get_latest_decision_definitions,
    get_decision_definition_xml,
    get_deployment,
    deploy_to_camunda
)
from git_client import get_bpmn_files_from_repo
from comparator import compare_bpmn

def run_check():
    result = {
        "deployments_checked": 0,
        "matches": [],
        "mismatches": [],
        "missing_in_git": [],
        "error": None
    }
    
    try:
        deployments = get_latest_process_definitions(SOURCE_CAMUNDA_REST_URL)
    except Exception as e:
        result["error"] = f"Failed to fetch deployments from Camunda: {e}"
        return result
        
    result["deployments_checked"] = len(deployments)
    
    try:
        git_files = get_bpmn_files_from_repo()
    except Exception as e:
        result["error"] = f"Failed to fetch BPMN files from local Git repository: {e}"
        return result

    for process in deployments:
        resource_name = process.get('resource')
        process_id = process.get('id')
        
        if not resource_name:
            continue
            
        try:
            camunda_xml = get_process_definition_xml(SOURCE_CAMUNDA_REST_URL, process_id)
        except Exception as e:
            result["missing_in_git"].append({"resource": resource_name, "error": str(e)})
            continue
        
        git_content = None
        matched_git_path = None
        for git_path, content in git_files.items():
            if git_path.endswith(resource_name) or resource_name.endswith(git_path):
                git_content = content
                matched_git_path = git_path
                break
                
        if not git_content:
            result["missing_in_git"].append({"resource": resource_name})
            continue
            
        is_match = compare_bpmn(camunda_xml, git_content)
        
        if is_match:
            result["matches"].append({"resource": resource_name, "git_path": matched_git_path})
        else:
            result["mismatches"].append({"resource": resource_name, "git_path": matched_git_path})

    return result

def prepare_sync():
    result = {
        "deployments_to_sync": {},
        "error": None
    }
    
    resources_by_deployment_id = {}

    try:
        process_defs = get_latest_process_definitions(SOURCE_CAMUNDA_REST_URL)
        for p in process_defs:
            process_id = p.get("id")
            resource_name = p.get("resource")
            deployment_id = p.get("deploymentId")
            if not resource_name or not deployment_id:
                continue
            xml = get_process_definition_xml(SOURCE_CAMUNDA_REST_URL, process_id)
            if deployment_id not in resources_by_deployment_id:
                resources_by_deployment_id[deployment_id] = []
            resources_by_deployment_id[deployment_id].append((resource_name, xml))
    except Exception as e:
        result["error"] = f"Error fetching process definitions: {e}"
        return result

    try:
        decision_defs = get_latest_decision_definitions(SOURCE_CAMUNDA_REST_URL)
        for d in decision_defs:
            decision_id = d.get("id")
            resource_name = d.get("resource")
            deployment_id = d.get("deploymentId")
            if not resource_name or not deployment_id:
                continue
            xml = get_decision_definition_xml(SOURCE_CAMUNDA_REST_URL, decision_id)
            if deployment_id not in resources_by_deployment_id:
                resources_by_deployment_id[deployment_id] = []
            resources_by_deployment_id[deployment_id].append((resource_name, xml))
    except Exception as e:
        result["error"] = f"Error fetching decision definitions: {e}"
        return result

    deployments_to_sync = {}
    for dep_id, items in resources_by_deployment_id.items():
        try:
            dep_info = get_deployment(SOURCE_CAMUNDA_REST_URL, dep_id)
            dep_name = dep_info.get("name", f"Deployment-{dep_id}")
            
            if dep_name not in deployments_to_sync:
                deployments_to_sync[dep_name] = {}
                
            for resource_name, xml in items:
                deployments_to_sync[dep_name][resource_name] = xml
        except Exception as e:
            # gracefully handle missing deployments
            pass
            
    result["deployments_to_sync"] = deployments_to_sync
    return result

def execute_sync(deployments_to_sync):
    result = {
        "success": [],
        "failed": []
    }
    
    for dep_name, files_dict in deployments_to_sync.items():
        try:
            res = deploy_to_camunda(TARGET_CAMUNDA_REST_URL, dep_name, files_dict)
            result["success"].append({"deployment_name": dep_name, "id": res.get("id")})
        except Exception as e:
            result["failed"].append({"deployment_name": dep_name, "error": str(e)})
            
    return result
