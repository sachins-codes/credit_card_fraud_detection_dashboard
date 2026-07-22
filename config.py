import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATASET_FOLDER = os.path.join(BASE_DIR, "dataset")

MODEL_FOLDER = os.path.join(BASE_DIR, "models")

DATABASE = os.path.join(BASE_DIR, "database", "database.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")