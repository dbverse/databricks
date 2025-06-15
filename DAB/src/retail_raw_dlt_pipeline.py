# COMMAND ----------
# This notebook defines a Delta Live Tables pipeline focusing on the Raw layer
# following the Raw, Conformed, Curated architecture using batch processing.
# Data is ingested from Unity Catalog Volumes, and partitioning is applied to raw_orders.

import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType, DateType

# Define the base Unity Catalog Volume path where your raw data resides
UC_RAW_INBOUND_PATH = "/Volumes/dbndev/raw/inbound"

# Define specific paths for each entity's raw data within the UC Volume
# For orders, point to the directory containing monthly/daily files
RAW_ORDERS_PATH = f"{UC_RAW_INBOUND_PATH}/orders/"
# For customers and products, point directly to the single JSON file
RAW_CUSTOMERS_PATH = f"{UC_RAW_INBOUND_PATH}/customers/customer_data.json"
RAW_PRODUCTS_PATH = f"{UC_RAW_INBOUND_PATH}/products/product_data.json"

# COMMAND ----------
# RAW LAYER TABLES (Ingestion from raw sources)
# These tables will reside in the 'raw' schema when deployed (configured via 'target' in DLT settings)

@dlt.table(
    name="raw_orders", # Renamed from bronze_orders
    comment="Raw customer order data ingested from UC Volume (Raw Layer), partitioned by source date.",
    table_properties={"quality": "raw"}, # Renamed from bronze
    partition_by=["file_date"] # Partition by the derived file_date column
)
def raw_orders():
    """
    Reads raw JSON order data as a batch from the specified UC Volume path.
    Extracts date from filename to use for partitioning (YYYY/MM/DD folder structure).
    - For monthly full loads (e.g., monthly_full_load_2025_01.json), uses YYYY-MM-01.
    - For daily incremental loads (e.g., orders_2025_06_15.json), uses YYYY-MM-DD.
    """
    df = spark.read.format("json").load(RAW_ORDERS_PATH)
    
    # Add a column for the source filename to extract date
    df_with_filename = df.withColumn("source_filename", F.input_file_name())

    # Extract date from filename based on patterns
    # Pattern for daily files: orders_YYYY_MM_DD.json
    # Pattern for monthly full load files: monthly_full_load_YYYY_MM.json
    df_with_date = df_with_filename.withColumn(
        "file_date_str",
        F.when(
            F.col("source_filename").contains("orders_"),
            F.regexp_extract(F.col("source_filename"), r"orders_(\d{4}_\d{2}_\d{2})\.json", 1)
        ).when(
            F.col("source_filename").contains("monthly_full_load_"),
            F.regexp_extract(F.col("source_filename"), r"monthly_full_load_(\d{4}_\d{2})\.json", 1) + "_01" # Add _01 for day
        ).otherwise(
            F.lit("UNKNOWN") # Handle unexpected filenames, or use current date or drop
        )
    )

    # Convert the extracted string date to a proper DateType for partitioning
    # Replace underscores with hyphens for parsing if needed, then cast
    return df_with_date.withColumn(
        "file_date",
        F.to_date(F.regexp_replace(F.col("file_date_str"), "_", "-"), "yyyy-MM-dd").cast(DateType())
    ).drop("source_filename", "file_date_str") # Drop intermediate columns


@dlt.table(
    name="raw_customers", # Renamed from bronze_customers
    comment="Raw customer master data ingested from UC Volume (Raw Layer).",
    table_properties={"quality": "raw"} # Renamed from bronze
)
def raw_customers():
    """Reads raw JSON customer data as a batch from the specified UC Volume file."""
    # Assuming 'customer_data.json' contains all customer records
    return spark.read.format("json").load(RAW_CUSTOMERS_PATH)

@dlt.table(
    name="raw_products", # Renamed from bronze_products
    comment="Raw product catalog data ingested from UC Volume (Raw Layer).",
    table_properties={"quality": "raw"} # Renamed from bronze
)
def raw_products():
    """Reads raw JSON product data as a batch from the specified UC Volume file."""
    # Assuming 'product_data.json' contains all product records
    return spark.read.format("json").load(RAW_PRODUCTS_PATH)


