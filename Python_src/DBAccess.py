#! /usr/bin/env python3

import sqlite3
from sqlite3 import Error
import pandas as pd

def create_connection(path):
    # Create file if it doesn't exist
    createFile = open(path, 'a')
    createFile.close()
    
    connection = None
    try:
        connection = sqlite3.connect(path)
        # print("Connection to SQLite DB successful") # Debug printing
    except Error as e:
        print(f"The error '{e}' occurred")

    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query executed successfully")
    except Error as e:
        print(f"The error '{e}' occurred")

# Redundent, replaced with pd.read_sql_query to read directly into pandas data frame
def execute_select_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except Error as e:
        print(f"The error '{e}' occurred")

def getColumnIndex(connection, columnName, tableName):

    getTableColumns = f"PRAGMA table_info({tableName})"
    columns = execute_select_query(connection, getTableColumns)
    
    columnNames = []
    for aColumn in columns:
        columnNames.append(aColumn[1])
    
    try:
        return columnNames.index(columnName)
    except ValueError:
        print("Oops, that's not a legit column name")
        raise
        
def getAllData_DF(connection):
    temperature_data_query = "SELECT * FROM temperature_data"
    temperature_data_DF = pd.read_sql_query(temperature_data_query, connection, index_col = "data_id")
    
    sensors_data_query = "SELECT * FROM sensors"
    sensors_DF = pd.read_sql_query(sensors_data_query, connection)
    
    groupings_data_query = "SELECT * FROM groupings"
    groupings_DF = pd.read_sql_query(groupings_data_query, connection)

    returnDataFrame = pd.merge(temperature_data_DF, sensors_DF, on="sensorID")
    returnDataFrame = pd.merge(returnDataFrame, groupings_DF, on="grouping_id")
    return returnDataFrame

def getFilteredDataForSpecificValue(connection, columnName, value):
    allData = getAllData_DF(connection)
    filteredData = allData.loc[allData[columnName] == value]
    return filteredData

def getDataForSensor(connection, sensorID):
    return getFilteredDataForSpecificValue(connection, "sensorID", sensorID)
    
def getDataForGrouping(connection, grouping):
    return getFilteredDataForSpecificValue(connection, "grouping_id", grouping)
    
def getUniqueSyncTimestamps(connection):
    get_syncTimestamps_query = "SELECT syncTimestamp FROM temperature_data"
    syncTimestamps = pd.read_sql_query(get_syncTimestamps_query, connection)
    syncTimestampsList = syncTimestamps["syncTimestamp"].tolist()
    return set(syncTimestampsList)
    
def getTemperatureDataFrameForTimestamp(connection, aTimestamp):
    uniqueTimestamps = getUniqueSyncTimestamps(connection)
        
    if aTimestamp not in uniqueTimestamps:
        printString = f"Couldn't find exact timestamp {aTimestamp}"
        aTimestamp = min(uniqueTimestamps, key=lambda x:abs(x-aTimestamp))
        printString += f", returning closest one : {aTimestamp}"
        print(printString)
    
    # print("looking up data for timestamp " + str(aTimestamp)) # Debug print
    temperature_data_query = f"SELECT * FROM temperature_data WHERE \"syncTimestamp\" == {aTimestamp}"
    temperature_DF = pd.read_sql_query(temperature_data_query, connection, index_col = "data_id")

    return temperature_DF
