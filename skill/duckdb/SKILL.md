---
name: duckdb
description: DuckDB - Fast in-memory analytical database system. Use this skill when working with DuckDB, analytical SQL queries, data import/export (CSV, Parquet, JSON), Python integration, or high-performance data analysis.
---

# DuckDB - Fast Analytical Database

## Quick Overview

DuckDB is a **fast in-memory analytical database** with:
- **SQL-first** - PostgreSQL-compatible SQL dialect
- **Zero-copy integration** - Pandas, Arrow, Polars
- **Columnar execution** - Vectorized query processing
- **No server needed** - Embedded in your application
- **Single file storage** - Or in-memory for analysis

## Installation

```bash
# Python
pip install duckdb

# CLI
brew install duckdb  # macOS
# Or download from https://duckdb.org
```

## Python Integration

### Basic Usage

```python
import duckdb

# In-memory database
con = duckdb.connect()

# File-based database
con = duckdb.connect('my_database.db')

# Execute SQL
result = con.execute("SELECT * FROM table").fetchall()

# Convert to pandas
import pandas as pd
df = con.execute("SELECT * FROM table").df()
```

### SQL on Pandas

```python
import duckdb
import pandas as pd

df = pd.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})

# Query pandas with SQL
result = duckdb.query("SELECT a, b FROM df WHERE a > 1").to_df()

# Or using connection
con = duckdb.connect()
result = con.execute("SELECT * FROM df").df()
```

### Import/Export with Pandas

```python
# Import pandas to DuckDB
con.execute("CREATE TABLE items AS SELECT * FROM df")

# Export DuckDB to pandas
df = con.execute("SELECT * FROM items").df()

# Using relation API
rel = con.table("items")
df = rel.filter("a > 1").project("a, b").order("b").df()
```

## SQL Basics

### Creating Tables

```sql
CREATE TABLE weather (
    city    VARCHAR,
    temp_lo INTEGER,
    temp_hi INTEGER,
    prcp    FLOAT,
    date    DATE
);
```

### Inserting Data

```sql
-- Single row
INSERT INTO weather VALUES ('San Francisco', 46, 50, 0.25, '1994-11-27');

-- Multiple rows
INSERT INTO weather VALUES
    ('SF', 43, 57, 0.0, '1994-11-29'),
    ('Hayward', 37, 54, NULL, '1994-11-29');

-- From CSV
COPY weather FROM 'weather.csv';

-- From query
CREATE TABLE new_weather AS SELECT * FROM weather;
```

### Querying Data

```sql
-- All columns
SELECT * FROM weather;

-- Specific columns
SELECT city, (temp_hi + temp_lo) / 2 AS temp_avg, date
FROM weather;

-- Filtering
SELECT * FROM weather
WHERE city = 'San Francisco' AND prcp > 0.0;

-- Sorting
SELECT * FROM weather
ORDER BY city, temp_lo;

-- Distinct
SELECT DISTINCT city FROM weather;
```

## Joins

```sql
-- Inner join
SELECT *
FROM weather, cities
WHERE weather.city = cities.name;

-- Explicit join syntax
SELECT *
FROM weather
INNER JOIN cities ON weather.city = cities.name;

-- Left outer join (includes unmatched rows)
SELECT *
FROM weather
LEFT OUTER JOIN cities ON weather.city = cities.name;
```

## Aggregation

```sql
-- Basic aggregates
SELECT max(temp_lo), min(temp_lo), avg(temp_lo)
FROM weather;

-- Group by
SELECT city, max(temp_lo)
FROM weather
GROUP BY city;

-- Having (filter groups)
SELECT city, max(temp_lo)
FROM weather
GROUP BY city
HAVING max(temp_lo) < 40;

-- With WHERE
SELECT city, max(temp_lo)
FROM weather
WHERE city LIKE 'S%'
GROUP BY city
HAVING max(temp_lo) < 40;
```

## Data Import/Export

### CSV Files

```sql
-- Read CSV
COPY weather FROM 'weather.csv';

-- Read with options
COPY weather FROM 'weather.csv' (HEADER, DELIMITER ',');

-- Export to CSV
COPY (SELECT * FROM weather) TO 'output.csv' (HEADER);
```

### Parquet Files

```sql
-- Read single Parquet
SELECT * FROM 'data.parquet';

-- Read multiple files
SELECT * FROM 'data/*.parquet';

-- Export to Parquet
COPY (SELECT * FROM weather) TO 'output.parquet';
```

### JSON Files

```sql
-- Read JSON (requires httpfs extension or JSON functions)
INSTALL httpfs;
LOAD httpfs;

-- Read JSON lines
SELECT * FROM 'data.jsonl';

-- JSON functions
SELECT json_extract(json_col, '$.name') FROM table;
```

### Querying Directly from Files

```sql
-- Query Parquet files directly
SELECT * FROM 's3://bucket/data*.parquet'
WHERE year = 2024;

-- Glob patterns
SELECT * FROM glob('data/*.parquet');

-- Multiple file types
SELECT * FROM read_csv_auto('data/*.csv');
```

## Working with S3

```python
import duckdb

con = duckdb.connect()

# Create secret for S3
con.execute("""
    CREATE SECRET my_s3_secret (
        TYPE S3,
        KEY_ID 'AKIA...',
        SECRET '...',
        REGION 'us-east-1'
    )
""")

# Query S3 data
con.execute("""
    SELECT * FROM 's3://bucket/*.parquet'
    WHERE year = 2024
""")
```

## Advanced Features

### Window Functions

```sql
SELECT
    city,
    temp_lo,
    AVG(temp_lo) OVER (
        PARTITION BY city
        ORDER BY date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_avg
FROM weather;
```

### PIVOT/UNPIVOT

```sql
-- PIVOT
PIVOT temperatures
ON date
USING max(temp_hi)

-- UNPIVOT
UNPIVOT temperatures
ON column1, column2
INTO NAME
VALUE
```

### Macros (User-Defined Functions)

```sql
CREATE MACRO greet(name) AS (
    SELECT 'Hello, ' || name
);

-- Use macro
SELECT * FROM greet('World');
```

### ATTACH/DETACH Databases

```sql
-- Attach another database
ATTACH 'path/to/other.db' AS other_db;

-- Query across databases
SELECT * FROM other_db.schema.table;

-- Detach
DETACH other_db;
```

## Performance Tips

1. **Use Parquet** - Columnar format is fastest for analytics
2. **Filter early** - Put WHERE conditions before aggregations
3. **Avoid SELECT *** - Specify only needed columns
4. **Use indexes** - For large filtered tables
5. **Batch inserts** - Faster than single-row inserts
6. **Use CSV options** - Auto-detection can be slow for large files

## Common Patterns

### Time-Series Analysis

```sql
-- Daily aggregations
SELECT
    date_trunc('day', timestamp) as day,
    COUNT(*) as events
FROM events
GROUP BY day
ORDER BY day;
```

### Data Profiling

```sql
-- Summarize table (get stats on all columns)
SUMMARIZE SELECT * FROM weather;

-- Describe table
DESCRIBE weather;

-- Column statistics
SELECT *
FROM duckdb_columns()
WHERE table_name = 'weather';
```

### EXPLAIN Query Plans

```sql
-- See query plan
EXPLAIN SELECT * FROM weather WHERE city = 'SF';

-- Profile query execution
EXPLAIN ANALYZE SELECT * FROM weather;
```

## Data Types

| Type | Description | Example |
|------|-------------|---------|
| `VARCHAR` | Variable-length text | `'hello'` |
| `INTEGER` | Whole numbers | `42` |
| `BIGINT` | Larger integers | `9223372036854775807` |
| `FLOAT` | Single-precision floating | `3.14` |
| `DOUBLE` | Double-precision floating | `3.1415926535` |
| `DECIMAL(p,s)` | Fixed-precision | `DECIMAL(10,2)` |
| `DATE` | Year-month-day | `DATE '2024-01-15'` |
| `TIMESTAMP` | Date + time | `TIMESTAMP '2024-01-15 10:30:00'` |
| `BOOLEAN` | True/false | `TRUE` |
| `BLOB` | Binary data | `BLOB '...'` |
| `ARRAY` | Arrays | `[1, 2, 3]` |
| `LIST` | Lists (typed arrays) | `[1, 2, 3]::INT[]` |
| `STRUCT` | Nested data | `{'a': 1, 'b': 'x'}` |
| `MAP` | Key-value pairs | `MAP({'a': 1, 'b': 2})` |

## Useful Functions

### String Functions

```sql
-- Pattern matching
WHERE name LIKE 'A%'

-- Regular expressions
WHERE regexp_matches(name, '[A-Z].*')

-- String manipulation
SELECT
    upper(name),
    lower(name),
    substring(name, 1, 3),
    concat(first, ' ', last)
FROM table;
```

### Date/Time Functions

```sql
-- Current date/time
SELECT current_date, current_timestamp;

-- Date arithmetic
SELECT
    date,
    date + INTERVAL '7 days' as next_week,
    EXTRACT('year', date) as year
FROM table;
```

### Array Functions

```sql
-- Array operations
SELECT
    arr[1] as first_element,
    unnest(arr) as exploded,
    array_length(arr) as length,
    list_aggregate(arr, 'sum') as total
FROM table;
```

## Client APIs

- **Python** - `pip install duckdb`
- **R** - `install.packages("duckdb")`
- **Java/JDBC** - ODBC driver
- **C++** - Embedded library
- **Node.js** - `npm install duckdb`
- **Go** - `go get github.com/marcboeker/go-duckdb`
- **Rust** - `cargo add duckdb`

## When to Use DuckDB

- **Analytics** - Fast aggregations on large datasets
- **Data science** - In-process Python/R integration
- **ETL** - Import/transform/export data files
- **Prototyping** - No server setup needed
- **Embedded applications** - Single-file database

## References

- **[Official Docs](https://duckdb.org/docs)** - Complete documentation
- **[Python Guide](https://duckdb.org/docs/stable/guides/python/overview)** - Python integration
- **[SQL Reference](https://duckdb.org/docs/stable/sql/introduction)** - SQL syntax
