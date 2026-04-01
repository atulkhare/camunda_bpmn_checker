import os

def get_local_files_by_app(technical_folder_path):
    """
    Parses the Technical Folder structure:
    Technical Folder/
        BPMN/
            App1/
                file.bpmn
        DMN/
            App2/
                rule.dmn
                
    Returns a dictionary grouped by application name:
    {
        "App1": {
            "BPMN": {"file.bpmn": "<xml>"},
            "DMN": {}
        }
    }
    """
    apps = {}
    
    if not os.path.exists(technical_folder_path):
        print(f"Warning: Directory not found -> {technical_folder_path}")
        return apps

    for base_dir in ["BPMN", "DMN"]:
        base_path = os.path.join(technical_folder_path, base_dir)
        if not os.path.isdir(base_path):
            continue
            
        for app_name in os.listdir(base_path):
            app_path = os.path.join(base_path, app_name)
            if not os.path.isdir(app_path):
                continue
                
            if app_name not in apps:
                apps[app_name] = {"BPMN": {}, "DMN": {}}
                
            for root, _, files in os.walk(app_path):
                for file_name in files:
                    if (base_dir == "BPMN" and (file_name.endswith('.bpmn') or file_name.endswith('.bpmn20.xml'))) or \
                       (base_dir == "DMN" and file_name.endswith('.dmn')):
                        
                        file_path = os.path.join(root, file_name)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                apps[app_name][base_dir][file_name] = f.read()
                        except Exception as e:
                            print(f"Error reading local file {file_path}: {e}")
                            
    return apps
