from flask import Flask, jsonify
import os
import requests
import json
from azure.cosmos import CosmosClient
from azure.core.exceptions import CosmosResourceNotFoundError

app = Flask(__name__)

# --- Configuration from environment variables ---
COSMOS_DB_CONNECTION_STRING = os.environ['COSMOS_DB_CONNECTION_STRING']
COSMOS_DB_DATABASE_NAME = os.environ['COSMOS_DB_DATABASE_NAME']
COSMOS_DB_CONTAINER_NAME = os.environ['COSMOS_DB_CONTAINER_NAME']
# This is the URL of our Azure Function for retrieval
RETRIEVER_FUNCTION_URL = os.environ['RETRIEVER_FUNCTION_URL']
RETRIEVER_FUNCTION_KEY = os.environ['RETRIEVER_FUNCTION_KEY'] # Use a Function Key for security

# --- Connect to Cosmos DB ---
cosmos_client = CosmosClient.from_connection_string(COSMOS_DB_CONNECTION_STRING)
database = cosmos_client.get_database_client(COSMOS_DB_DATABASE_NAME)
container = database.get_container_client(COSMOS_DB_CONTAINER_NAME)

@app.route('/records/<id>', methods=['GET'])
def get_record(id):
    """
    API endpoint to retrieve a billing record.
    
    This function implements the 'hot-cold' read logic:
    1. It first queries the 'hot' store (Cosmos DB).
    2. If the record is not found in Cosmos DB (e.g., due to TTL), 
       it then calls the 'cold' retrieval function to check the archive.
    """
    try:
        # --- 1. Attempt to get the record from Cosmos DB (the 'hot' store) ---
        # Assuming 'id' is the unique identifier and partition key
        # In a real app, you might need the partition key value. Let's assume it's the id for simplicity.
        record = container.read_item(item=id, partition_key=id)
        
        # If the record is found in Cosmos DB, return it immediately.
        # This is the low-latency path for recent data.
        return jsonify(record), 200
        
    except CosmosResourceNotFoundError:
        # --- 2. If not found in Cosmos DB, query the retrieval function for the 'cold' store ---
        print(f"Record {id} not found in Cosmos DB. Querying the archival storage via Azure Function...")
        
        headers = {'x-functions-key': RETRIEVER_FUNCTION_KEY}
        # Call the Azure Function with the record ID to fetch it from Blob Storage
        response = requests.get(f"{RETRIEVER_FUNCTION_URL}/{id}", headers=headers)
        
        if response.status_code == 200:
            # Found in cold storage, return the data from the Azure Function's response
            return jsonify(response.json()), 200
        elif response.status_code == 404:
            # Not found in either store (the function returned a 404)
            return jsonify({"error": "Record not found"}), 404
        else:
            # Something went wrong with the retrieval function
            return jsonify({"error": "Failed to retrieve record from archive"}), 500
            
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)