#!/usr/bin/env python
import psycopg2

def obtain_connection(dbhost, database, username, password):
    # Define our connection.
    conn_string = "host=%s dbname=%s user=%s password='%s'" % (dbhost, database, username, password)
    # Attempt to get a connection
    conn = psycopg2.connect(conn_string)
    return conn

def obtain_data_from_database(connection, query):
    cursor = connection.cursor('my_cursor')
    # Execute the query.
    cursor.execute(query)
    # Grab the results.
    database_data = cursor.fetchall()
    # Close the cursor.
    cursor.close()
    return database_data

def obtain_data_from_database_query_variable(connection, query, query_variable):
    cursor = connection.cursor('my_cursor')
    # Execute the query.
    cursor.execute(query, query_variable)
    # Grab the results.
    database_data = cursor.fetchall()
    # Close the cursor.
    cursor.close()
    return database_data