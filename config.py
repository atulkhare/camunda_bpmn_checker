import os
from dotenv import load_dotenv

load_dotenv()

SOURCE_CAMUNDA_REST_URL = os.getenv("SOURCE_CAMUNDA_REST_URL", "http://localhost:8080/engine-rest")
TARGET_CAMUNDA_REST_URL = os.getenv("TARGET_CAMUNDA_REST_URL", "http://localhost:8081/engine-rest")
GIT_REPO_PATH = os.getenv("GIT_REPO_PATH", ".")

# Set default to match the exact requirement folder path
CAMUNDA_BASE_URL = os.getenv("CAMUNDA_BASE_URL", "http://localhost:8080")
TECHNICAL_FOLDER_PATH = os.getenv(
    "TECHNICAL_FOLDER_PATH", 
    r"C:\Users\Vidmay\Documents\projects\camunda_bpmn_checker\Technical Folder"
)
