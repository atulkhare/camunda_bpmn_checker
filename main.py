import sys
import argparse
from core import run_check, prepare_sync, execute_sync, compare_servers
from config import SOURCE_CAMUNDA_REST_URL, TARGET_CAMUNDA_REST_URL

def check_command():
    print("Starting Camunda BPMN Checker [Check Mode]...")
    print(f"Fetching deployed process definitions from Source Camunda ({SOURCE_CAMUNDA_REST_URL})...")
    
    result = run_check()
    
    if result.get("error"):
        print(result["error"])
        sys.exit(1)
        
    print(f"Found {result['deployments_checked']} deployed process definitions.")
    
    for ms in result["matches"]:
        print(f"  [OK] Matches Git file '{ms['git_path']}'")
        
    for ms in result["mismatches"]:
        print(f"  [X] MISMATCH with Git file '{ms['git_path']}'")
        
    for ms in result["missing_in_git"]:
        res_error = ms.get("error", "")
        if res_error:
            print(f"  [!] Error fetching '{ms['resource']}': {res_error}")
        else:
            print(f"  [!] Missing in Git repository: {ms['resource']}")

    print("\n--- Summary ---")
    print(f"Deployed processes checked: {result['deployments_checked']}")
    print(f"Matches: {len(result['matches'])}")
    print(f"Mismatches: {len(result['mismatches'])}")
    print(f"Missing in Git: {len(result['missing_in_git'])}")
    
    if len(result['mismatches']) > 0 or len(result['missing_in_git']) > 0:
        sys.exit(1)

def sync_command():
    print("Starting Camunda BPMN Checker [Sync Mode]...")
    print(f"Source: {SOURCE_CAMUNDA_REST_URL}")
    print(f"Target: {TARGET_CAMUNDA_REST_URL}")
    print("\nFetching latest definitions securely...")
    
    prep_res = prepare_sync()
    if prep_res.get("error"):
        print(prep_res["error"])
        sys.exit(1)
        
    deployments = prep_res["deployments_to_sync"]
    if not deployments:
        print("No definitions found to sync. Exiting.")
        return
        
    print("\n--- Deployments to Sync ---")
    total_files = 0
    for dep_name, files in deployments.items():
        print(f"Deployment: '{dep_name}' ({len(files)} files)")
        for filename in files.keys():
            print(f"  - {filename}")
        total_files += len(files)
        
    print(f"\nTotal files: {total_files} grouped into {len(deployments)} deployments.")
    confirm = input(f"Do you want to deploy these groups to the target server ({TARGET_CAMUNDA_REST_URL})? [y/N]: ")
    
    if confirm.lower() in ('y', 'yes'):
        print("\nDeploying to target server...")
        res = execute_sync(deployments)
        
        for success in res["success"]:
            print(f"  [OK] Success! '{success['deployment_name']}' ID: {success['id']}")
            
        if res["failed"]:
            print("\n--- Deployment Failures ---")
            for fail in res["failed"]:
                print(f" - {fail['deployment_name']}: {fail['error']}")
            sys.exit(1)
        else:
            print("\nAll deployments successful!")
    else:
        print("Sync cancelled by user.")
def compare_servers_command():
    print("Comparing Source Server to Target Server by Deployment Key...")
    result = compare_servers()
    
    if result.get("error"):
        print(result["error"])
        sys.exit(1)
        
    print("\n--- Differences Found ---")
    diff_count = 0
    for f in result["modified"]:
        print(f" [Modified (Content mismatch)] {f['resource']} (Key: {f['key']})")
        print("   --- Diff ---")
        for line in f['diff'].split('\n')[:20]: # Show up to 20 lines of diff
            print(f"   {line}")
        if len(f['diff'].split('\n')) > 20:
            print("   ... (diff truncated)")
        print()
        diff_count += 1
    for f in result["missing_in_target"]:
        print(f" [Missing in Target] {f['resource']} (Key: {f['key']})")
        diff_count += 1
        
    if diff_count == 0:
        print("Servers are perfectly synced!")
    else:
        print(f"\nTotal differences: {diff_count}")
        sys.exit(1)

def ui_command():
    print("Starting Web UI...")
    from app import start_server
    start_server()

def main():
    parser = argparse.ArgumentParser(description="Camunda BPMN Checker & Sync Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("check", help="Check if Camunda deployed definitions match local Git files")
    subparsers.add_parser("sync", help="Download from Source Camunda and deploy to Target")
    subparsers.add_parser("compare-servers", help="Show files that differ between Source and Target servers")
    subparsers.add_parser("ui", help="Start the modern Web UI dashboard")

    args = parser.parse_args()

    if args.command == "check":
        check_command()
    elif args.command == "sync":
        sync_command()
    elif args.command == "compare-servers":
        compare_servers_command()
    elif args.command == "ui":
        ui_command()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
