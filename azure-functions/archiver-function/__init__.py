import logging
import os
import datetime
import json
from azure.functions import TimerRequest
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient

# --- Configuration from environment variables ---
COSMOS_DB_CONNECTION_STRING = os.environ['COSMOS_DB_CONNECTION_STRING']
COSMOS_DB_DATABASE_NAME = os.environ['COSMOS_DB_DATABASE_NAME']
COSMOS_DB_CONTAINER_NAME = os.environ['COSMOS_DB_CONTAINER_NAME']
AZURE_STORAGE_CONNECTION_STRING = os.environ['AZURE_STORAGE_CONNECTION_STRING']
BLOB_CONTAINER_NAME = os.environ['BLOB_CONTAINER_NAME']
ARCHIVE_THRESHOLD_DAYS = int(os.environ.get('ARCHIVE_THRESHOLD_DAYS', 90))

def main(myTimer: TimerRequest) -> None:
    """
    Azure Function to archive old billing records from Cosmos DB to Blob Storage.
    """
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    logging.info('Archival function started at %s', utc_timestamp.isoformat())

    try:
        # --- Connect to Cosmos DB ---
        cosmos_client = CosmosClient.from_connection_string(COSMOS_DB_CONNECTION_STRING)
        database = cosmos_client.get_database_client(COSMOS_DB_DATABASE_NAME)
        container = database.get_container_client(COSMOS_DB_CONTAINER_NAME)
        
        # --- Connect to Azure Blob Storage ---
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
        
        # --- Query for records older than the threshold ---
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=ARCHIVE_THRESHOLD_DAYS)
        
        # We assume the record has a 'createdAt' timestamp field in ISO format.
        # This query leverages Cosmos DB indexing on 'createdAt'.
        query = f"SELECT * FROM c WHERE c.createdAt < '{threshold_date.isoformat()}'"
        
        records_to_archive = container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
        
        archived_count = 0
        for record in records_to_archive:
            # Construct a unique blob name using a record ID and a date or a unique identifier
            # e.g., '2024/06/billing_record_<id>.json'
            record_id = record['id']
            created_date = datetime.datetime.fromisoformat(record['createdAt']).strftime('%Y/%m/%d')
            blob_name = f"{created_date}/{record_id}.json"
            
            # --- Write the record to Blob Storage ---
            blob_client = blob_container_client.get_blob_client(blob_name)
            
            # Use 'overwrite=False' to prevent accidental overwrites if the function is re-run.
            # You might need to handle this with a check for existence first.
            if not blob_client.exists():
                blob_client.upload_blob(json.dumps(record, indent=2), overwrite=True)
                logging.info(f"Successfully archived record {record_id} to {blob_name}")
                archived_count += 1
            else:
                logging.info(f"Record {record_id} already exists in Blob Storage. Skipping.")
                
            # --- Set TTL on the archived record in Cosmos DB ---
            # Set TTL to 1 second to mark for immediate deletion.
            # This triggers Cosmos DB's background garbage collection.
            record['ttl'] = 1
            container.upsert_item(record)
            
            logging.info(f"Set TTL on record {record_id} in Cosmos DB.")

        logging.info(f"Archival process finished. {archived_count} records archived.")

    except Exception as e:
        logging.error(f"An error occurred during archival: {e}")
        # Add error handling and alerting (e.g., send a notification to Azure Monitor)