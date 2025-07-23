# Simple Serverless Databricks Job Bundle

This DAB deploys a basic Databricks job to a specified workspace, running a notebook on serverless compute.
It demonstrates passing parameters (like `process_date`) from the bundle config to the notebook.

**To Deploy:**
1.  **Update `databricks.yml`**: Replace placeholder host and ensure `profile` matches your CLI setup.
2.  **Navigate to bundle root**: `cd /path/to/Basic_DAB/`
3.  **Validate**: `databricks bundle validate`
4.  **Deploy**: `databricks bundle deploy -t dev`

**To Run the Job (e.g., with overrides):**
`databricks bundle run my_basic_serverless_notebook_job -e dev --params "process_date=2025-07-24"`