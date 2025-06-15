# Databricks Retail DLT Pipeline Setup (Databricks Free Edition)

This project sets up a **Delta Live Tables (DLT) pipeline** using a **Databricks Asset Bundle (DAB)**. Its main goal is to ingest raw retail data into a **Raw data layer** within Unity Catalog, with intelligent partitioning.

---

## What the project is about :

Developed a robust solution to process retail data:

-   **Project Structure**: Organized files within a `DAB/` folder, including the `databricks.yaml` configuration and `src/retail_raw_dlt_pipeline.ipynb` for the DLT code.
-   **DLT Pipeline**: Created a DLT pipeline focused on ingesting `raw_orders`, `raw_customers`, and `raw_products` data.
-   **Serverless Compute**: Configured the DLT pipeline to use Databricks' **serverless compute** for efficient resource management.
-   **Data Partitioning**: Implemented logic to dynamically partition `raw_orders` data based on date extracted from filenames, even for monthly files.
-   **Job Trigger**: Set up a Databricks Job to trigger the DLT pipeline manually.
-   **Unity Catalog**: Ensured all tables are published to a specified **Unity Catalog** (e.g., `users` catalog).

---

## What's Required

To use and deploy this project, you'll need:

-   **Project Files**:
    -   `DAB/databricks.yaml`: The main bundle configuration.
    -   `DAB/src/retail_raw_dlt_pipeline.ipynb`: Your DLT pipeline notebook.
-   **Databricks CLI (Version 0.200.0+)**: The new Databricks CLI is essential for `bundle` commands.
    -   **Installation**: Can be installed via `pip` (e.g., `pip install databricks-cli`) or `brew` within WSL (e.g., `brew install databricks`). Brew is the safer option. 
    -   **Authentication**: Configure the CLI with your Databricks workspace URL and a Personal Access Token (`databricks configure`).
    -   **Enterprise Note**: In enterprise environments, the `databricks.exe` executable might be directly included in the DAB folder for easier execution in lower environments without relying on system-wide PATH configurations or WSL.
-   **Databricks Workspace**: An active Databricks workspace with Unity Catalog enabled.
-   **Unity Catalog Volume**: Raw data files (orders, customers, products) should be present in the `/Volumes/dbndev/raw/inbound` path within your Unity Catalog.
-   **Deploy Command**: To deploy the job also, we need to execute the command 'databricks bundle deploy -t dev' as our YAML is structured that way. For the pipeline, 'databricks bundle deploy' is enough. 

---

## Key Errors Faced & Resolutions

Encountered and resolved several critical errors during development:

-   **"No such command 'bundle'"**:
    -   **Cause**: Using an older Databricks CLI version (e.g., 0.18.0) that lacked DAB support.
    -   **Resolution**: Upgraded the CLI to version 0.200.0 or higher using `brew` in WSL.
-   **`databricks.yaml` Configuration Issues**:
    -   **`storage_location` warning**: Removed this field as DLT automatically manages storage in Unity Catalog.
    -   **Incorrect `libraries` syntax**: Adjusted the syntax for DLT pipelines to correctly reference the notebook file (`notebook: path:`).
    -   **Cluster/Serverless Conflict**: Removed the explicit `clusters` block, relying solely on `serverless: true` for DLT's automatic compute management.
-   **DLT `TypeError: table() got an unexpected keyword argument 'partition_by'`**:
    -   **Cause**: Attempting to use `partition_by` directly as an argument for the `@dlt.table` decorator (it's not supported there).
    -   **Resolution**: Removed `partition_by` from the decorator. DLT applies partitioning based on the data in the DataFrame.
-   **Unity Catalog `AnalysisException` (`input_file_name` / `_corrupt_record`)**:
    -   **Cause**: `input_file_name()` is not supported in Unity Catalog, and schema inference failed for empty/malformed raw JSON files.
    -   **Resolution**: Replaced `F.input_file_name()` with **`F.col("_metadata.file_path")`** and added **explicit schemas** for all raw JSON tables (`raw_orders`, `raw_customers`, `raw_products`).

This README provides a concise overview of the project's setup and the solutions implemented.