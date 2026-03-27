import git
import os
from config import GIT_REPO_PATH

def get_bpmn_files_from_repo():
    """
    Finds and reads all tracked .bpmn files from the configured git repository.
    Returns a dictionary of filepath -> xml_content.
    """
    try:
        repo = git.Repo(GIT_REPO_PATH)
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: Directory '{GIT_REPO_PATH}' is not a valid git repository.")
        return {}
    
    bpmn_files = {}
    
    # Get list of tracked files
    tracked_files = repo.git.ls_files().split('\n')
    for file_path in tracked_files:
        if file_path.endswith('.bpmn') or file_path.endswith('.bpmn20.xml'):
            full_path = os.path.join(repo.working_dir, file_path)
            if os.path.isfile(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    bpmn_files[file_path] = f.read()
                    
    return bpmn_files
