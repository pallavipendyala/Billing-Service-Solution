import logging
import os
import json
from azure.functions import HttpRequest, HttpResponse
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
import datetime

# --- Configuration from environment variables ---
AZURE_STORAGE_CONNECTION_STRING = os.environ['AZURE_STORAGE_CONNECTION_STRING']
BLOB_CONTAINER_NAME = os.environ['BLOB_CONTAINER_NAME']

def main(req: HttpRequest) -> HttpResponse:
    """
    Azure Function to retrieve a billing record from Blob Storage.
    This function is called by the API service.
    """
    record_id = req.route_params.get('id')
    if not record_id:
        return HttpResponse("Please pass a record ID in the URL path.", status_code=400)
        
    logging.info(f'Retrieval request received for record ID: {record_id}')
    
    try:
        # --- Connect to Azure Blob Storage ---
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

        # --- Search for the blob (requires knowing the path, which we can deduce from ID) ---
        # The archival logic stores records with a date prefix. We need to find the correct blob.
        # This is the most complex part of retrieval. A robust solution would use a search index
        # like Azure Cognitive Search, but for simplicity, we can assume a known path format.
        # A simple approach is to iterate through potential date folders.
        
        # Pseudocode for finding the blob:
        # We need a way to map record_id to a created date.
        # For this example, let's assume the API provides the creation date, or we iterate.
        
        # Let's assume we store the records in a flat structure for simplicity.
        blob_name = f"{record_id}.json" # simplified for demo
        # A better approach would be to store the full date in the path.
        # For a truly robust solution, you might store a mapping in a small, cheap DB (e.g., Azure Table Storage)
        # or use Azure Cognitive Search to index the blobs.
        
        # ---
        # A more realistic path based on the archiver's logic:
        # We don't have the createdAt date from the ID.
        # We can either:
        # 1. Modify the API contract to include the creation date.
        # 2. Search for the blob across different date prefixes.
        # Let's assume the API doesn't change and we have to search.
        
        # This is a less efficient, but contract-compliant retrieval method.
        # A robust solution might use Azure Cognitive Search to index the blob metadata for fast lookups.
        
        blobs_list = blob_container_client.list_blobs()
        blob_found = None
        for blob in blobs_list:
            if blob.name.endswith(f'/{record_id}.json'):
                blob_found = blob.name
                break
        
        if blob_found:
            logging.info(f"Found archived blob at: {blob_found}")
            blob_client = blob_container_client.get_blob_client(blob_found)
            blob_data = blob_client.download_blob().readall()
            
            return HttpResponse(
                blob_data.decode('utf-8'),
                status_code=200,
                mimetype="application/json"
            )
        else:
            logging.warning(f"Record {record_id} not found in Blob Storage.")
            return HttpResponse(
                "Record not found.",
                status_code=404
            )

    except ResourceNotFoundError:
        logging.warning(f"Record {record_id} not found in Blob Storage.")
        return HttpResponse("Record not found.", status_code=404)
    except Exception as e:
        logging.error(f"An error occurred during retrieval: {e}")
        return HttpResponse("Internal server error.", status_code=500)