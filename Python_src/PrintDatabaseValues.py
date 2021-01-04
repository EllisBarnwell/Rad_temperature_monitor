#! /usr/bin/env python3

import configparser
import DBAccess
import pandas as pd
import time
from datetime import datetime
import sys

# Settings
config = configparser.ConfigParser()
config.read("Radiator_temp_logger.cnf")

databasePath = config["DatabaseSettings"].get("databasePath")
dbConnection = DBAccess.create_connection(databasePath)

nRowsToPrint = config["PrintSettings"].getint("nRowsToPrint")
printHeaderEveryNRows = config["PrintSettings"].getint("printHeaderEveryNRows")

sensors_data_query = "SELECT * FROM sensors"

# Note, to make a neat table, each column will take up 4 spaces so we can have temperatures with one decimal place
# Please ensure short names are no longer than 4 characters, if they're not they will be truncated
# Short names are 0 by default so must be changed (This can be done easily using a program like DB Browser)

def printHeader(sensors_data_DF):
    print()
    printString = "Sensor Name         : "; # 19 chars long + " : "
    
    # Order columns by name
    sensors_data_DF.sort_values("sensorShortName", inplace=True)
    
    # Only show if active
    sensors_data_DF = sensors_data_DF.loc[sensors_data_DF["isSensorActiveBool"] == 1]
    
    for index, row in sensors_data_DF.iterrows():
        printString += '{:4.4}'.format(row["sensorShortName"]) # Pad and truncate to length 4
        printString += "  "
    
    print(printString)
    
    underline = "---------------------" # 21 + 5 * len sensors_data_DF
    
    for i in range(len(sensors_data_DF)):
        underline += "------"
    
    print(underline)
    
    return list(sensors_data_DF["sensorID"]) # Pass this back so it can be used when printing rows

def printRow(temperature_data_rows, sensorHeadersOrder):
    timestamp = temperature_data_rows.iloc[0, temperature_data_rows.columns.get_loc("syncTimestamp")]
    printString = datetime.utcfromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S") # 19 chars long

    printString += " : "
    
    for sensorID in sensorHeadersOrder:
        sensorDatToPrint_df = temperature_data_rows.loc[temperature_data_rows['sensorID'] == sensorID]
        
        nSensorDatToPrint = len(sensorDatToPrint_df.index)
        
        if nSensorDatToPrint == 0:
            printString += " -- "
        elif nSensorDatToPrint == 1:
            datToPrint = sensorDatToPrint_df.iloc[0]
            printString += "{:2.1f}".format(datToPrint["tempDegC"]) # Fix length to 4 characters
        else:
            raise ValueError

        printString += "  "
    
    print(printString)

# What happens when nRowsToPrint > nRows???
def printLastNRows(nRowsToPrint, temperature_DF_w_sensors, sensorHeadersOrder, sensors_data_DF, rowCounter):
    uniqueSyncTimestamps = set(temperature_DF_w_sensors["syncTimestamp"])
    sortedUniqueSyncTimestamps = sorted(uniqueSyncTimestamps)
    
    if(nRowsToPrint < 0):
        lastNTimestamps = sortedUniqueSyncTimestamps
    else:
        lastNTimestamps = sortedUniqueSyncTimestamps[-nRowsToPrint:]
    
    for timestamp in lastNTimestamps:
        if rowCounter >= printHeaderEveryNRows:
            rowCounter = 0
            printHeader(sensors_data_DF)
        rows = temperature_DF_w_sensors.loc[temperature_DF_w_sensors["syncTimestamp"] == timestamp]
        try:
            printRow(rows, sensorHeadersOrder)
            rowCounter += 1
        except ValueError:
            print("Error, multiple values for a specific sensorID and syncTimestamp")
    
    lastTimestamp = 0
    if len(sortedUniqueSyncTimestamps) > 0:
        lastTimestamp = sortedUniqueSyncTimestamps[-1]
    
    return lastTimestamp, rowCounter # latest data point printed

def loadInitialDataAndPrint(rowCounter):
    # Get sensor info
    sensors_data_DF = pd.read_sql_query(sensors_data_query, dbConnection)
    
    # Get temperature data
    temperature_data_query = "SELECT * FROM temperature_data"
    temperature_data_DF = pd.read_sql_query(temperature_data_query, dbConnection, index_col = "data_id")
    
    # Merge sensor info into temperature data
    temperature_DF_w_sensors = pd.merge(temperature_data_DF, sensors_data_DF, on="sensorID")

    sensorHeadersOrder = printHeader(sensors_data_DF)     
    lastTimestamp, rowCounter = printLastNRows(nRowsToPrint, temperature_DF_w_sensors, sensorHeadersOrder, sensors_data_DF, rowCounter)
    
    return sensors_data_DF, sensorHeadersOrder, lastTimestamp, rowCounter

if __name__ == "__main__":
    print()
    rowCounter = 0;
    sensors_data_DF, sensorHeadersOrder, lastTimestamp, rowCounter = loadInitialDataAndPrint(rowCounter)
    
    while True:
        # Todo - Check if DB sensor set up has changed when in loop, reprint headers if so
        time.sleep(1)
        
        sensors_data_DF_NEW = pd.read_sql_query(sensors_data_query, dbConnection)

        if (not sensors_data_DF_NEW["isSensorActiveBool"].equals(sensors_data_DF.sort_index()["isSensorActiveBool"])
                or not sensors_data_DF_NEW["sensorShortName"].equals(sensors_data_DF.sort_index()["sensorShortName"])
                or not sensors_data_DF_NEW["grouping_id"].equals(sensors_data_DF.sort_index()["grouping_id"]) ):
            rowCounter = 0
            sensors_data_DF = sensors_data_DF_NEW
            sensorHeadersOrder = printHeader(sensors_data_DF)
        
        # Get temperature data
        temperature_data_query = f"SELECT * FROM temperature_data WHERE \"syncTimestamp\" > {lastTimestamp}"
        temperature_data_DF = pd.read_sql_query(temperature_data_query, dbConnection, index_col = "data_id")
        
        if(len(temperature_data_DF.index)) > 0:
            time.sleep(10) # Sleep to ensure database has been fully updated
            
            timestampCol = temperature_data_DF["syncTimestamp"]
            maxTimestamp = timestampCol.max()
            
            temperature_data_query = f"SELECT * FROM temperature_data WHERE \"syncTimestamp\" BETWEEN {lastTimestamp+1} AND {maxTimestamp}"
            temperature_data_DF = pd.read_sql_query(temperature_data_query, dbConnection, index_col = "data_id")
            
            # Merge sensor info into temperature data
            temperature_DF_w_sensors = pd.merge(temperature_data_DF, sensors_data_DF, on='sensorID')
            
            lastTimestamp, rowCounter = printLastNRows(-1, temperature_DF_w_sensors, sensorHeadersOrder, sensors_data_DF, rowCounter)
