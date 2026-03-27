import sys
from camunda_client import get_latest_process_definitions, get_process_definition_xml
from git_client import get_bpmn_files_from_repo
from comparator import compare_bpmn

def main():
    print("Starting Camunda BPMN Checker...")
    print("Fetching deployed process definitions from Camunda...")
    try:
        deployments = get_latest_process_definitions()
    except Exception as e:
        print(f"Failed to fetch deployments from Camunda: {e}")
        sys.exit(1)
        
    print(f"Found {len(deployments)} deployed process definitions.")
    
    print("Fetching BPMN files from local Git repository...")
    git_files = get_bpmn_files_from_repo()
    print(f"Found {len(git_files)} BPMN files in Git.")

    matches = 0
    mismatches = 0
    missing_in_git = 0
    
    for process in deployments:
        resource_name = process.get('resource')
        process_id = process.get('id')
        
        print(f"\nChecking deployment: {resource_name} (ID: {process_id})")
        
        if not resource_name:
            print(f"  -> Skipping (no resource name)")
            continue
            
        camunda_xml = get_process_definition_xml(process_id)
        
        git_content = None
        matched_git_path = None
        for git_path, content in git_files.items():
            if git_path.endswith(resource_name) or resource_name.endswith(git_path):
                git_content = content
                matched_git_path = git_path
                break
                
        if not git_content:
            print(f"  [!] Missing in Git repository: {resource_name}")
            missing_in_git += 1
            continue
            
        is_match = compare_bpmn(camunda_xml, git_content)
        
        if is_match:
            print(f"  [OK] Matches Git file '{matched_git_path}'")
            matches += 1
        else:
            print(f"  [X] MISMATCH with Git file '{matched_git_path}'")
            mismatches += 1

    print("\n--- Summary ---")
    print(f"Deployed processes checked: {len(deployments)}")
    print(f"Matches: {matches}")
    print(f"Mismatches: {mismatches}")
    print(f"Missing in Git: {missing_in_git}")
    
    if mismatches > 0 or missing_in_git > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
