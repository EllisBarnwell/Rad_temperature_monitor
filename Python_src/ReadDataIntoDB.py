import requests
import json
from datetime import datetime
import configparser
import time
import DBAccess
from requests.exceptions import ConnectionError
from requests.exceptions import ReadTimeout
# import pdb

# Settings
config = configparser.ConfigParser()
config.read("Radiator_temp_logger.cnf")

databasePath = config["DatabaseSettings"].get("databasePath")
ipAddresses = json.loads(config["DeviceSettings"].get("ipAddresses"))
querySensorsTime_sec = config["DEFAULT"].getfloat("querySensorsTime_sec")

def addUngrouptedGroupingIfNotPresent(connection):
    query = f"INSERT OR IGNORE INTO groupings (grouping_id, groupingPrettyName, isGroupingActiveBool) values (0, 'DefaultGroup', 0)" # Note, we're putting this into grouping 0 -> ungrouped
    print("Query to call = " + query)
    DBAccess.execute_query(connection, query)
    
def addSensorIfNotPresent(connection, sensorID):
    query = f"INSERT OR IGNORE INTO sensors (sensorID, sensorPrettyName, sensorShortName, isSensorActiveBool, grouping_id, flow1_return0, calibrationCorrection) values ('{sensorID}', 'NULL', '0', 1, 0, -1, 0)" # Note, we're putting this into grouping 0 -> ungrouped
    print("Query to call = " + query)
    DBAccess.execute_query(connection, query)

def addDataPoint(connection, syncTimestamp, timestamp, sensorID, tempDegC):
    query = f"INSERT INTO temperature_data (syncTimestamp, timestamp, sensorID, tempDegC) values ({syncTimestamp}, {timestamp}, '{sensorID}', {tempDegC})"
    print("Query to call = " + query)
    DBAccess.execute_query(connection, query)
    
# Note used yet but may be handy in case where we don't have sync timestamp 
# def addDataPoint(connection, timestamp, sensorID, tempDegC):
#    syncTimestamp = int(timestamp)
#    addDataPoint(connection, syncTimestamp, timestamp, sensorID, tempDegC)
    
def printData(response):
    print("")
    for entry in response:
        print("sensorID is ")
        print(entry["SensorID"])
        print("TempDegC is ")
        print(entry["TempDegC"])
        print("")

def processResponse(response, connection, syncTimestamp):
    printData(response)
    
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    
    # Todo :- Error checking to see if everything as expected with result
    for aSensorResponse in response:
        sensorID = aSensorResponse["SensorID"]
        tempDegC = aSensorResponse["TempDegC"]
        # Flag some message to say we're adding new sensor 
        # OR if sensor isn't present, flag error thus 
        # relying on all sensors being configured in database separately before this function
        addUngrouptedGroupingIfNotPresent(connection)
        addSensorIfNotPresent(connection, sensorID)
        addDataPoint(connection, syncTimestamp, timestamp, sensorID, tempDegC)

# Remember to add sensors if they're not there
def gatherTempsAndUpdate(connection):
    now = datetime.now()
    syncTimestamp = int(datetime.timestamp(now))
    
    # Think about doing these in threads for synchronicity
    # This would help if one IP address is offline.
    # Make sure threads die properly if a node is offline, possibly be careful not to start new thread if we're awaiting one to finish
    for ipAddress in ipAddresses:
        print()
        print("Processing IP Address: " + ipAddress)
        try:
            r = requests.get("http://" + ipAddress, timeout=5)
        except ConnectionError as e:
            print("Failed to connect to IP address : " + ipAddress)
            print (e)
            continue
        except ReadTimeout as e:
            print("Read timeout IP address : " + ipAddress)
            print (e)
            continue
        response = json.loads(r.text)
        
        processResponse(response, connection, syncTimestamp)

# Create connection
connection = DBAccess.create_connection(databasePath)

while(True):
    print()
    print("Gathering data from sensors and adding to database")
    gatherTempsAndUpdate(connection)
    print()
    print("Sleeping for " + str(querySensorsTime_sec) + " seconds")
    time.sleep(querySensorsTime_sec)
