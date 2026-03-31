import os
from dotenv import load_dotenv

load_dotenv()

SOURCE_CAMUNDA_REST_URL = os.getenv("SOURCE_CAMUNDA_REST_URL", os.getenv("CAMUNDA_REST_URL", "http://localhost:8080/engine-rest"))
TARGET_CAMUNDA_REST_URL = os.getenv("TARGET_CAMUNDA_REST_URL", "http://localhost:8081/engine-rest")
GIT_REPO_PATH = os.getenv("GIT_REPO_PATH", "./")
