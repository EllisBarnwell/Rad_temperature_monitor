#! /usr/bin/env python3

import configparser
import DBAccess

def createDBTables(connection):
    # Also add cal info for this sensor
    create_sensors_table = """
    CREATE TABLE IF NOT EXISTS sensors (
      sensorID TEXT PRIMARY KEY,
      sensorPrettyName TEXT,
      sensorShortName TEXT,
      isSensorActiveBool INTEGER,
      grouping_id INTEGER NOT NULL REFERENCES groupings(grouping_id),
      flow1_return0 INTEGER,
      calibrationCorrection REAL
    );
    """
    DBAccess.execute_query(connection, create_sensors_table)

    # Contemplate having a separate ID rather than having timestamp as primary key
    create_data_entry_table = """
    CREATE TABLE IF NOT EXISTS temperature_data (
      data_id INTEGER PRIMARY KEY AUTOINCREMENT,
      syncTimestamp INTEGER,
      timestamp REAL,
      sensorID TEXT NOT NULL REFERENCES sensors(sensorID),
      tempDegC REAL
    );
    """
    DBAccess.execute_query(connection, create_data_entry_table)
    
    # CreateGroupingsTable
    # Things to add are IPAddress and MAC address, assuming one grouping is form one NodeMCU
    # Note, these need to be kept up to date. This could happen when reading each IP address
    create_groupings_table = """
    CREATE TABLE IF NOT EXISTS groupings (
      grouping_id INTEGER PRIMARY KEY AUTOINCREMENT,
      groupingPrettyName TEXT,
      groupingShortName TEXT,
      isGroupingActiveBool INTEGER
    );
    """
    DBAccess.execute_query(connection, create_groupings_table)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("Radiator_temp_logger.cnf")
    databasePath = config["DatabaseSettings"].get("databasePath")
    
    connection = DBAccess.create_connection(databasePath)
    
    createDBTables(connection)
