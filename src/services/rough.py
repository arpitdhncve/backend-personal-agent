# #Initializing sql database here
import sqlite3

# Connect to SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('staging-db.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Define the SQL command to drop the table if it exists
drop_table_query = 'DROP TABLE IF EXISTS expenditure_details;'

# Execute the SQL command to drop the table
cursor.execute(drop_table_query)

# Commit the changes to the database
conn.commit()

# Close the cursor and connection
cursor.close()
conn.close()

# # Connect to SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('staging-db.db')

# # Create a cursor object to execute SQL commands
cursor = conn.cursor()

# # Define the SQL command to create a table
create_table_query = '''
CREATE TABLE expenditure_details (
    user_id TEXT,
    amount_paid INTEGER,
    purpose TEXT,
    paid_to TEXT,
    category TEXT,
    date_of_expenditure DATE,
    created_at DATE,
    created_at_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

# # Execute the SQL command to create the table
cursor.execute(create_table_query)

# # Commit the changes and close the connection
conn.commit()
conn.close()

from langchain_community.utilities import SQLDatabase
from sqlalchemy import Executable


sql_database = SQLDatabase.from_uri("sqlite:///staging-db.db")
print(sql_database.dialect)
print(sql_database.get_usable_table_names())
response = sql_database.run("SELECT * FROM expenditure_details")
print(response)
