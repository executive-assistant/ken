---
name: ducklake
description: DuckLake - An open table format for data lakes that works with DuckDB. Use this skill when working with DuckLake format, managing data lake storage, time travel queries, snapshots, schema evolution, or using DuckDB with DuckLake extension.
---

# DuckLake - Open Table Format for Data Lakes

## Quick Overview

DuckLake is an **open table format for data lakes** that works seamlessly with DuckDB. It provides:

- **ACID transactions** on data lake storage
- **Time travel** - query data as it was at any point in time
- **Schema evolution** - add/modify columns without breaking existing queries
- **Row-level deletes** - efficient deletion without rewriting entire files
- **Snapshots** - track changes to your data over time

## Installation

```sql
-- Requires DuckDB v1.3.0 or later
INSTALL ducklake;
LOAD ducklake;
```

## Basic Usage

### Creating a DuckLake Database

```sql
-- Simple: local metadata + local files
ATTACH 'ducklake:my_ducklake.ducklake' AS my_ducklake;
USE my_ducklake;

-- Custom data path
ATTACH 'ducklake:my_db.ducklake' AS my_db (DATA_PATH 'some/path/');
USE my_db;
```

This creates:
- `my_db.ducklake` - DuckDB file with metadata
- `my_db.ducklake.files/` - Folder with Parquet data files

### Working with Data

```sql
-- Create a table
CREATE TABLE users AS
    FROM 'users.csv';

-- Insert data
INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');

-- Update data (creates delete + insert files)
UPDATE users SET name = 'Alice Updated' WHERE id = 1;

-- Delete data
DELETE FROM users WHERE id = 2;

-- Query normally
SELECT * FROM users;
```

## Time Travel

Query data as it was at any snapshot:

```sql
-- List all snapshots
FROM my_db.snapshots();

-- Query at specific snapshot
SELECT * FROM users AT (VERSION => 1);
SELECT * FROM users AT (TIMESTAMP => '2024-01-15 10:00:00');

-- Time travel with system function
SELECT * FROM users AT (VERSION => snapshots().snapshot_id[0]);
```

## Snapshots

Every write operation creates a snapshot:

```sql
-- Get snapshot information
SELECT * FROM my_db.snapshots();

-- Get changes between snapshots
FROM snapshot_changes('users', 1, 2);
```

## Schema Evolution

Add, rename, or drop columns without rewriting data:

```sql
-- Add column
ALTER TABLE users ADD COLUMN email VARCHAR;

-- Rename column
ALTER TABLE users RANK COLUMN name TO full_name;

-- Drop column
ALTER TABLE users DROP COLUMN old_column;
```

## Upserting

Update-or-insert semantics:

```sql
INSERT OR REPLACE INTO users VALUES (1, 'New Name');

-- Or with ON CONFLICT
INSERT INTO users VALUES (1, 'Name')
ON CONFLICT (id) DO UPDATE SET name = excluded.name;
```

## Partitioning

Organize data by partition values:

```sql
-- Create partitioned table
CREATE TABLE sales (
    id INT,
    date DATE,
    amount DECIMAL(10,2)
) PARTITION BY (date);

-- DuckLake automatically partitions data files
```

## Maintenance

### Recommended Maintenance

```sql
-- Merge adjacent files to reduce file count
CALL merge_files('my_ducklake', 'users');

-- Expire old snapshots
CALL expire_snapshots('my_ducklake', older_than => INTERVAL 7 DAYS);

-- Clean up orphaned files
CALL cleanup_files('my_ducklake');

-- Rewrite files with many deletes
CALL rewrite_files('my_ducklake', 'users');
```

### Checkpoint

Create a consistent snapshot:

```sql
-- Force checkpoint
CALL checkpoint('my_ducklake');
```

## Data Change Feed

Track row-level changes:

```sql
-- Enable change tracking
ALTER TABLE users SET (change_tracking = true);

-- Query changes
FROM changes('users');
```

## Advanced Features

### Constraints

```sql
-- Note: DuckLake doesn't support PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK
-- These are tracked in metadata but not enforced
```

### Views

```sql
CREATE VIEW user_summary AS
    SELECT COUNT(*) as count FROM users;
```

### Encryption

```sql
-- At rest encryption for Parquet files
ATTACH 'ducklake:encrypted.ducklake' AS encrypted (
    DATA_PATH 'encrypted/',
    ENCRYPTION 'AES256'
);
```

## Metadata Tables

DuckLake maintains system tables:

- `ducklake_snapshot` - Snapshot metadata
- `ducklake_table` - Table definitions
- `ducklake_schema` - Schema information
- `ducklake_data_file` - Data file tracking
- `ducklake_delete_file` - Delete file tracking
- `ducklake_column` - Column definitions

```sql
-- List all data files
FROM 'my_ducklake.ducklake.files/**/*.parquet';

-- Using glob to see files
FROM glob('my_ducklake.ducklake.files/**/*');
```

## Detaching

```sql
USE memory;
DETACH my_ducklake;
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Snapshot** | Immutable point-in-time view of data |
| **Manifest** | List of valid data files for a snapshot |
| **Data File** | Parquet file containing row data |
| **Delete File** | Parquet file tracking deleted rows |
| **Schema** | Table structure with evolution support |

## Comparison with Other Formats

| Feature | DuckLake | Delta Lake | Apache Iceberg |
|---------|----------|------------|----------------|
| Database | DuckDB | Spark/Databricks | Spark |
| ACID | ✅ | ✅ | ✅ |
| Time Travel | ✅ | ✅ | ✅ |
| Schema Evolution | ✅ | ✅ | ✅ |
| Row Deletes | ✅ | ✅ | ✅ |
| Open Source | ✅ | ✅ | ✅ |

## When to Use DuckLake

- **Analytics on data lake storage** - Query Parquet files with ACID guarantees
- **Time travel requirements** - Need to query historical data
- **Schema evolution** - Frequently changing table structures
- **DuckDB users** - Native integration with DuckDB
- **Batch + incremental** - Mix of bulk loads and row-level updates

## References

- **[DuckDB Introduction](references/duckdb_introduction.md)** - Getting started guide
- **[Specification](references/specification_introduction.md)** - Full format specification
- **[Usage Guide](references/usage_guide.md)** - Common operations and patterns
- **[Maintenance](references/maintenance.md)** - File management and optimization
