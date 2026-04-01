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

def prepare_sync(source_url=None, target_url=None):
    comp = compare_servers(source_url, target_url)
    if comp.get("error"):
        return {"error": comp["error"]}
        
    deployments = {}
    
    for item in comp.get("missing_in_target", []) + comp.get("modified", []):
        app = item["app"]
        if app not in deployments: 
            deployments[app] = {}
        if item.get("source_xml"):
            deployments[app][item["resource"]] = item["source_xml"]
            
    deployments = {k: v for k, v in deployments.items() if v}
    
    if not deployments:
        return {"error": "No new or modified files found to deploy!"}
        
    return {"deployments_to_sync": deployments}

def execute_sync(payload, base_url=None):
    """
    Takes the deployment payload and hits the specific mapped URLs on the target.
    payload: { "AppName": {"file.bpmn": "<xml>", "rule.dmn": "<xml>"} }
    """
    if not base_url:
        base_url = TARGET_CAMUNDA_REST_URL
        
    mappings = get_mappings()
    results = {"success": [], "failed": []}
    
    for app_name, files_dict in payload.items():
        if app_name not in mappings:
            results["failed"].append({"app": app_name, "error": f"Mapping missing for {app_name}!"})
            continue
            
        ctx = mappings[app_name].strip('/')
        if ctx.endswith('engine-rest'):
            ctx = ctx[:-11].strip('/')
            
        target_url = f"{base_url.rstrip('/')}/{ctx}/engine-rest"
        deployment_name = app_name
        
        try:
            resp = deploy_to_camunda(target_url, deployment_name, files_dict)
            results["success"].append({
                "app": app_name,
                "id": resp.get("id"),
                "files_deployed": list(files_dict.keys())
            })
        except Exception as e:
            results["failed"].append({"app": app_name, "error": str(e)})
            
    return results

def compare_servers(source_url=None, target_url=None):
    source_url = source_url or SOURCE_CAMUNDA_REST_URL
    target_url = target_url or TARGET_CAMUNDA_REST_URL
    
    result = {
        "apps_checked": 0,
        "matches": [],
        "modified": [],
        "missing_in_target": [],
        "error": None,
        "failed_connections": []
    }
    
    mappings = get_mappings()
    if not mappings:
        result["error"] = "No app mappings defined in configuration."
        return result
        
    import difflib
    from comparator import canonicalize_xml

    for app_name, context_path in mappings.items():
        ctx = context_path.strip('/')
        if ctx.endswith('engine-rest'):
            ctx = ctx[:-11].strip('/')
            
        s_url = f"{source_url.rstrip('/')}/{ctx}/engine-rest"
        t_url = f"{target_url.rstrip('/')}/{ctx}/engine-rest"
        
        try:
            source_process_defs = get_latest_process_definitions(s_url)
            source_decision_defs = get_latest_decision_definitions(s_url)
        except Exception as e:
            result["failed_connections"].append({"app": app_name, "error": f"Source fetch failed: {e}", "url": s_url})
            continue
            
        try:
            target_process_defs = get_latest_process_definitions(t_url)
            target_decision_defs = get_latest_decision_definitions(t_url)
        except Exception as e:
            result["failed_connections"].append({"app": app_name, "error": f"Target fetch failed: {e}", "url": t_url})
            continue

        result["apps_checked"] += 1
        
        target_defs = {}
        for p in target_process_defs:
            if p.get("key"): target_defs[p.get("key")] = {"id": p.get("id"), "type": "process", "resource": p.get("resource")}
        for d in target_decision_defs:
            if d.get("key"): target_defs[d.get("key")] = {"id": d.get("id"), "type": "decision", "resource": d.get("resource")}
            
        source_defs = []
        for p in source_process_defs:
            if p.get("key"): source_defs.append({"key": p.get("key"), "resource": p.get("resource"), "id": p.get("id"), "type": "process"})
        for d in source_decision_defs:
            if d.get("key"): source_defs.append({"key": d.get("key"), "resource": d.get("resource"), "id": d.get("id"), "type": "decision"})
            
        for s_def in source_defs:
            key = s_def["key"]
            resource_name = s_def["resource"]
            
            if key not in target_defs:
                try:
                    if s_def["type"] == "process":
                        s_xml = get_process_definition_xml(s_url, s_def["id"])
                    else:
                        s_xml = get_decision_definition_xml(s_url, s_def["id"])
                except Exception:
                    s_xml = ""
                result["missing_in_target"].append({"app": app_name, "key": key, "resource": resource_name, "source_xml": s_xml})
                continue
                
            t_def = target_defs[key]
            
            try:
                if s_def["type"] == "process":
                    s_xml = get_process_definition_xml(s_url, s_def["id"])
                    t_xml = get_process_definition_xml(t_url, t_def["id"])
                else:
                    s_xml = get_decision_definition_xml(s_url, s_def["id"])
                    t_xml = get_decision_definition_xml(t_url, t_def["id"])
            except Exception as e:
                continue
                
            if compare_bpmn(s_xml, t_xml):
                result["matches"].append({"app": app_name, "key": key, "resource": resource_name})
            else:
                s_lines = canonicalize_xml(s_xml).splitlines()
                t_lines = canonicalize_xml(t_xml).splitlines()
                diff_text = "\n".join(difflib.unified_diff(
                    t_lines, s_lines, 
                    fromfile=f"Target ({t_def['resource']})", 
                    tofile=f"Source ({resource_name})"
                ))
                result["modified"].append({
                    "app": app_name,
                    "key": key,
                    "resource": resource_name,
                    "type": s_def["type"],
                    "diff": diff_text,
                    "source_xml": s_xml,
                    "target_xml": t_xml
                })
                
    return result

import json
import os
from config import CAMUNDA_BASE_URL, TECHNICAL_FOLDER_PATH
from local_client import get_local_files_by_app

MAPPING_FILE = os.path.join(os.path.dirname(__file__), 'mapping.json')

def get_mappings():
    if not os.path.exists(MAPPING_FILE):
        return {}
    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}
        
def save_mappings(data):
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def run_local_check(base_url=None):
    if not base_url:
        base_url = CAMUNDA_BASE_URL
        
    result = {
        "apps_checked": 0,
        "matches": [],
        "mismatches": [],
        "missing_on_server": [],
        "error": None,
        "unmapped_apps": [],
        "failed_connections": []
    }
    
    apps_data = get_local_files_by_app(TECHNICAL_FOLDER_PATH)
    mappings = get_mappings()
    
    if not apps_data:
        result["error"] = "No applications found in Technical Folder."
        return result
        
    import difflib
    from comparator import canonicalize_xml

    for app_name, app_files in apps_data.items():
        if app_name not in mappings:
            result["unmapped_apps"].append(app_name)
            continue
            
        context_path = mappings[app_name].strip('/')
        if context_path.endswith('engine-rest'):
            context_path = context_path[:-11].strip('/')
            
        target_url = f"{base_url.rstrip('/')}/{context_path}/engine-rest"
        
        try:
            target_process_defs = get_latest_process_definitions(target_url)
            target_decision_defs = get_latest_decision_definitions(target_url)
        except Exception as e:
            result["failed_connections"].append({"app": app_name, "error": str(e), "url": target_url})
            continue
            
        result["apps_checked"] += 1
            
        # Group server definitions by resource filename directly
        server_defs = {}
        for p in target_process_defs:
            res = p.get("resource")
            if res: server_defs[res] = {"id": p.get("id"), "type": "process"}
        for d in target_decision_defs:
            res = d.get("resource")
            if res: server_defs[res] = {"id": d.get("id"), "type": "decision"}
            
        # BPMN
        for file_name, local_xml in app_files.get("BPMN", {}).items():
            matched_key = None
            for s_res in server_defs.keys():
                if s_res.endswith(file_name) or file_name.endswith(s_res):
                    matched_key = s_res
                    break
                    
            if not matched_key:
                result["missing_on_server"].append({"app": app_name, "resource": file_name})
                continue
                
            server_xml = get_process_definition_xml(target_url, server_defs[matched_key]["id"])
            if compare_bpmn(local_xml, server_xml):
                result["matches"].append({"app": app_name, "resource": file_name})
            else:
                s_lines = canonicalize_xml(local_xml).splitlines()
                t_lines = canonicalize_xml(server_xml).splitlines()
                diff_text = "\n".join(difflib.unified_diff(
                    t_lines, s_lines, 
                    fromfile=f"Server ({app_name})", 
                    tofile=f"Local ({file_name})"
                ))
                result["mismatches"].append({
                    "app": app_name,
                    "resource": file_name,
                    "type": "process",
                    "diff": diff_text,
                    "source_xml": local_xml,
                    "target_xml": server_xml
                })
                
        # DMN
        for file_name, local_xml in app_files.get("DMN", {}).items():
            matched_key = None
            for s_res in server_defs.keys():
                if s_res.endswith(file_name) or file_name.endswith(s_res):
                    matched_key = s_res
                    break
                    
            if not matched_key:
                result["missing_on_server"].append({"app": app_name, "resource": file_name})
                continue
                
            server_xml = get_decision_definition_xml(target_url, server_defs[matched_key]["id"])
            if compare_bpmn(local_xml, server_xml):
                result["matches"].append({"app": app_name, "resource": file_name})
            else:
                s_lines = canonicalize_xml(local_xml).splitlines()
                t_lines = canonicalize_xml(server_xml).splitlines()
                diff_text = "\n".join(difflib.unified_diff(
                    t_lines, s_lines, 
                    fromfile=f"Server ({app_name})", 
                    tofile=f"Local ({file_name})"
                ))
                result["mismatches"].append({
                    "app": app_name,
                    "resource": file_name,
                    "type": "decision",
                    "diff": diff_text,
                    "source_xml": local_xml,
                    "target_xml": server_xml
                })

    return result

def prepare_local_sync(selected_items):
    """
    Bundles specific selected xml files into a deployment payload grouped by their application name.
    selected_items is a list of {"app": "AppName", "resource": "filename.bpmn"}
    """
    if not selected_items:
        return {"error": "No items selected for sync."}
        
    apps_data = get_local_files_by_app(TECHNICAL_FOLDER_PATH) # We need the source XMLs
    
    # payload: { "AppName": {"file1.bpmn": "<xml>"} }
    deployments = {}
    
    for item in selected_items:
        app_name = item.get("app")
        resource_name = item.get("resource")
        
        if not app_name or not resource_name:
            continue

        if app_name not in deployments:
            deployments[app_name] = {}
            
        xml_content = None
        if app_name in apps_data:
            if resource_name in apps_data[app_name].get("BPMN", {}):
                xml_content = apps_data[app_name]["BPMN"][resource_name]
            elif resource_name in apps_data[app_name].get("DMN", {}):
                xml_content = apps_data[app_name]["DMN"][resource_name]
                
        if xml_content:
            deployments[app_name][resource_name] = xml_content

    # clean empty deployments
    deployments = {k: v for k, v in deployments.items() if v}

    if not deployments:
        return {"error": "No new or modified files found to deploy!"}
        
    return {"deployments_to_sync": deployments}

def execute_local_sync(payload, base_url=None):
    """
    Takes the local deployment payload and hits the specific mapped URLs.
    payload: { "AppName": {"file.bpmn": "<xml>", "rule.dmn": "<xml>"} }
    """
    if not base_url:
        base_url = CAMUNDA_BASE_URL
        
    mappings = get_mappings()
    results = {"success": [], "failed": []}
    
    for app_name, files_dict in payload.items():
        if app_name not in mappings:
            results["failed"].append({"app": app_name, "error": f"Mapping missing for {app_name}!"})
            continue
            
        context_path = mappings[app_name].strip('/')
        if context_path.endswith('engine-rest'):
            context_path = context_path[:-11].strip('/')
            
        target_url = f"{base_url.rstrip('/')}/{context_path}/engine-rest"
        deployment_name = app_name
        
        try:
            resp = deploy_to_camunda(target_url, deployment_name, files_dict)
            results["success"].append({
                "app": app_name,
                "id": resp.get("id"),
                "files_deployed": list(files_dict.keys())
            })
        except Exception as e:
            results["failed"].append({"app": app_name, "error": str(e)})
            
    return results
