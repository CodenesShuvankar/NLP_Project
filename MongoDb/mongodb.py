
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


# Create a new client and connect to the server
client = MongoClient("mongodb://localhost:27017/")

db = client['document_db']
collection = db['metadata']

def save_metadata_to_mongodb(metadata):
    collection.insert_one(metadata)

def get_metadata_from_mongodb(file_name):
    return collection.find_one({"file_name": file_name})

dic ={"empy":"Sonar","Salary":"91219291"}
save_metadata_to_mongodb(dic)
