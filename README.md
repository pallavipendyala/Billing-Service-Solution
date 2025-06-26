# Billing Service Cost Optimization Solution

This repository contains the detailed implementation for a serverless hot-cold data storage solution for billing records in Azure.

## Solution Overview

The solution aims to reduce storage costs by offloading old, infrequently accessed billing records from a high-cost Azure Cosmos DB database to a low-cost Azure Blob Storage. It uses Azure Functions to automate the archival and retrieval process, ensuring a seamless experience for API consumers without changing the existing API contracts.

**Key Components:**
- **Azure Cosmos DB:** Stores recent billing records (last 3 months) for low-latency access.
- **Azure Blob Storage:** Serves as the archive for older records, using the Cool tier for cost efficiency.
- **Azure Functions:**
    - `archiver-function`: A timer-triggered function that moves old data from Cosmos DB to Blob Storage.
    - `retriever-function`: A function that retrieves archived data from Blob Storage on demand.
- **Azure Container App:** Hosts the main API, which now queries both Cosmos DB and Blob Storage.

## Setup and Deployment

1. **Prerequisites:**
   - Azure Subscription
   - Azure CLI or Azure Portal access
   - Python 3.9+

2. **Azure Resource Deployment:**
   - Deploy an **Azure Cosmos DB** account (Serverless tier is recommended for cost optimization on spiky workloads).
   - Create a container named `billing-records` with a partition key (e.g., `/customerId`).
   - Enable **Time to Live (TTL)** on the container with a default value of **`null`** initially. We will set TTL on individual items.
   - Deploy an **Azure Storage Account**.
   - Create a container named `billing-archives` and set its access tier to **Cool**.
   - Deploy an **Azure Container App** for the API service.
   - Deploy an **Azure Functions App** with a Python runtime.

3. **Function App Configuration:**
   - Deploy the `archiver-function` and `retriever-function` from this repository to your Azure Functions App.
   - Set up the following Application Settings for the Functions App:
     - `COSMOS_DB_CONNECTION_STRING`: Your Cosmos DB connection string.
     - `COSMOS_DB_DATABASE_NAME`: The name of your database (e.g., `billingdb`).
     - `COSMOS_DB_CONTAINER_NAME`: The name of your container (e.g., `billing-records`).
     - `AZURE_STORAGE_CONNECTION_STRING`: Your Azure Storage account connection string.
     - `BLOB_CONTAINER_NAME`: The name of your blob container (e.g., `billing-archives`).
     - `ARCHIVE_THRESHOLD_DAYS`: `90` (for 3 months).

4. **API Service Deployment:**
   - Deploy the `api-service` (e.g., a FastAPI or Flask app) to your Azure Container App.
   - Ensure the API service has the necessary environment variables and connection strings to connect to both Cosmos DB and Blob Storage.

## Usage

- The API service operates as before.
- The archival process runs automatically based on the timer trigger. ( 1st of the month at 2:00 AM, and for the second run on the 15th of the month at 2:00 AM)
- To test the retrieval of old data, query a record older than the 90-day threshold. The API will seamlessly fetch it from Blob Storage.