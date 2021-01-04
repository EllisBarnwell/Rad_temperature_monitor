#! /usr/bin/env python3

import sys
import getopt
import configparser
import DBAccess
import pandas as pd
from datetime import datetime
import time

# Settings
config = configparser.ConfigParser()
config.read("Radiator_temp_logger.cnf")

# Handle command line arguments
def getHelpText():
    helpText = "\r\n"
    helpText += "PrintRadiatorSummaries.py will read the database pointed to in Radiator_temp_logger.cnf and print the latest summary based on the radiators\r\n"
    helpText += "\r\n"
    helpText += "Options:-\r\n"
    helpText += "\r\n"
    helpText += "   -t  :   --flowSort              :   Sort radiators by max temperature\r\n"
    helpText += "       :   --returnSort            :   Sort radiators by max temperature\r\n"
    helpText += "   -r  :   --reverseSort           :   Sort values in reverse\r\n"
    helpText += "   -d  :   --diffSort              :   Sort radiators by temperature difference\r\n"
    helpText += "   -f  :   --follow                :   Follow: Keep refreshing the tables as new values come in\r\n"
    helpText += "       :   --timestamp <time>      :   Supply a timestamp <time> to give summary for\r\n"
    helpText += "   -i  :   --index <n>             :   Show summary for specific index <n> values since most recent\r\n"
    
    return helpText

def printOnlyOneSortMethodAndExit():
    print("Please only supply one sort method, -t (--flowSort), --returnSort or -d (--diffSort)")
    sys.exit(2)

def printCantFollowSpecificTimestampAndExit():
    print("Can't run both in follow mode and print specific timestamp or index.")
    sys.exit(2)

def printCantPrintTimestampAndIndexAndExit():
    print("Can't print both timestamp and index.")
    sys.exit(2)

sortByFlowTemperature = False
sortByReturnTemperature = False
sortByDifference = False
inverseSort = False
inFollowMode = False
dataTimestamp = 0
dataIndex = 0

try:
    opts, args = getopt.getopt(sys.argv[1:],"htdfri:",["flowSort","reverseSort","returnSort","diffSort","timestamp=","index="])
except getopt.GetoptError:
    print("PrintRadiatorSummaries.py options error occured")
    sys.exit(2)
for opt, arg in opts:
    if opt == "-h":
        print(getHelpText())
        sys.exit()
    elif opt in (["-t", "--flowSort"]):
        if(sortByDifference or sortByReturnTemperature):
            printOnlyOneSortMethodAndExit()
        sortByFlowTemperature = True
    elif opt in (["--returnSort"]):
        if(sortByDifference or sortByFlowTemperature):
            printOnlyOneSortMethodAndExit()
        sortByReturnTemperature = True
    elif opt in (["-d", "--diffSort"]):
        if(sortByFlowTemperature or sortByReturnTemperature):
            printOnlyOneSortMethodAndExit()
        sortByDifference = True
    elif opt in (["-r", "--reverseSort"]):
        inverseSort = True
    elif opt in (["-f", "--follow"]):
        if dataTimestamp != 0 or dataIndex != 0:  printCantFollowSpecificTimestampAndExit()
        inFollowMode = True
    elif opt in (["--timestamp"]):
        if inFollowMode: printCantFollowSpecificTimestampAndExit()
        if dataIndex != 0: printCantPrintTimestampAndIndexAndExit()
        try:
            dataTimestamp = int(arg)
        except ValueError as e:
            print(e)
            print("Please supply a valid timestamp since 1970 in seconds")
            sys.exit(2)
    elif opt in ("-i", "--index"): # BUG for some reason --index <n> works but -i <n> doesn't. Causes ValueError
        if inFollowMode: printCantFollowSpecificTimestampAndExit()
        if dataTimestamp != 0: printCantPrintTimestampAndIndexAndExit()
        try:
            dataIndex = int(arg)
        except ValueError as e:
            print(e)
            print("Please supply a valid data index")
            sys.exit(2)

# Done handling arguments, on with the code

def fillFlowOrReturnData(active_rads_DF, associatedSensors_DF, temperatures_DF, flow1_return0, sensorColName, tempColName, groupingPrettyName, index):
        associatedSensors_DF = associatedSensors_DF.loc[associatedSensors_DF["flow1_return0"] == flow1_return0]
                
        if len(associatedSensors_DF.index) == 0:
            print("Error, sensor not found for grouping " + groupingPrettyName)
        elif len(associatedSensors_DF.index) > 1:
            print("Error, too many sensors found for grouping " + groupingPrettyName)
        else:
            active_rads_DF.at[index,sensorColName] = associatedSensors_DF.iloc[0]["sensorPrettyName"]
            
            temperature_Rows = temperatures_DF.loc[temperatures_DF["sensorID"] == associatedSensors_DF.iloc[0]["sensorID"]]
            if len(temperature_Rows.index) == 0:
                print("Error, temperature not found for grouping " + groupingPrettyName)
            elif len(associatedSensors_DF.index) > 1:
                print("Error, too many temperatures found for grouping " + groupingPrettyName)
            else:
                active_rads_DF.at[index,tempColName] = temperature_Rows.iloc[0]["tempDegC"]
                active_rads_DF.at[index,"timestamp"] = temperature_Rows.iloc[0]["syncTimestamp"]

def getRadiatorSummary_DF(connection, temperatures_DF):
    # sensors_data_query = "SELECT * FROM sensors"
    active_rads_data_query = "SELECT * FROM groupings WHERE \"isGroupingActiveBool\" != 0"
    active_rads_w_temps_DF = pd.read_sql_query(active_rads_data_query, connection)
    
    sensors_data_query = "SELECT * FROM sensors WHERE \"isSensorActiveBool\" != 0"
    sensors_DF = pd.read_sql_query(sensors_data_query, connection)
    
    # Add extra columns and fill in
    emptyColumn = [None for i in range(len(active_rads_w_temps_DF.index))]
    
    active_rads_w_temps_DF["flowSensorName"] = emptyColumn
    active_rads_w_temps_DF["returnSensorName"] = emptyColumn
    active_rads_w_temps_DF["flowTemp"] = emptyColumn
    active_rads_w_temps_DF["returnTemp"] = emptyColumn
    active_rads_w_temps_DF["timestamp"] = emptyColumn

    # Should probably merge data frames and then go from there
    # Some object orientation would probs make things a lot neater

    for index, row in active_rads_w_temps_DF.iterrows():
        grouping = row["grouping_id"]
        
        associatedSensors_DF = sensors_DF.loc[sensors_DF["grouping_id"] == grouping]
        
        fillFlowOrReturnData(active_rads_w_temps_DF, associatedSensors_DF, temperatures_DF, 1, "flowSensorName", "flowTemp", row["groupingPrettyName"], index)
        fillFlowOrReturnData(active_rads_w_temps_DF, associatedSensors_DF, temperatures_DF, 0, "returnSensorName", "returnTemp", row["groupingPrettyName"], index)

    return active_rads_w_temps_DF

def printHeader():
    print()
    print("                                                       |  Flow temp  | Return temp | Difference  |")
    print("--------------------------------------------------------------------------------------------------")

def getValueOrBlank(value):
    if value == None:
        return " --  "
    else:
        try:
            returnStr = "{:2.1f}".format(value)
            returnStr = '{:5.5}'.format(returnStr)
            return returnStr
        except ValueError:
            return " --  "

def printRow(row):
    line1 = '{:50.50}'.format(row["groupingPrettyName"])
    line1 += "     |             |             |             |"
    print(line1)
    
    line2 = "   Flow sensor   -> "
    line2 += '{:30.30}'.format(row["flowSensorName"])
    line2 += "     |    " + getValueOrBlank(row["flowTemp"]) + "    |    " + getValueOrBlank(row["returnTemp"]) + "    |    " + getValueOrBlank(row["difference"]) + "    |"
    print(line2)

    line3 = "   Return sensor -> "
    line3 += '{:30.30}'.format(row["returnSensorName"])
    line3 += "     |             |             |             |"
    print(line3)
    
    print("--------------------------------------------------------------------------------------------------")

def calculateDifferences(active_rads_w_temps_DF):
    active_rads_w_temps_and_diff_DF = active_rads_w_temps_DF.copy(deep=True)
    
    emptyColumn = [None for i in range(len(active_rads_w_temps_and_diff_DF.index))]
    active_rads_w_temps_and_diff_DF["difference"] = emptyColumn

    for index, row in active_rads_w_temps_DF.iterrows():
        flowTemp = row["flowTemp"]
        returnTemp = row["returnTemp"]
        if(flowTemp == None):
            print("Error, flow temp is missing for " + row["groupingPrettyName"])
        elif(returnTemp == None):
            print("Error, return temp is missing for " + row["groupingPrettyName"])
        else:
            active_rads_w_temps_and_diff_DF.at[index, "difference"] = flowTemp - returnTemp
        
    return active_rads_w_temps_and_diff_DF

def printRadiatorSummary(connection, temperatures_DF):
    active_rads_w_temps_DF = getRadiatorSummary_DF(connection, temperatures_DF)
    
    active_rads_w_temps_and_diff_DF = calculateDifferences(active_rads_w_temps_DF)
    
    print()
    
    timestamp = active_rads_w_temps_and_diff_DF.at[0, "timestamp"]
    printTimeString = datetime.utcfromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S") # 19 chars long
    
    print(printTimeString)
    print()
    
    printStr = "Sorted by"
    if inverseSort: printStr += " inverse"
    
    if(sortByFlowTemperature):
        printStr += " flow temperature"
        active_rads_w_temps_and_diff_DF.sort_values("flowTemp", ascending = inverseSort, inplace = True)
    if(sortByReturnTemperature):
        printStr += " return temperature"
        active_rads_w_temps_and_diff_DF.sort_values("returnTemp", ascending = inverseSort, inplace = True)
    if(sortByDifference):
        printStr += " difference"
        active_rads_w_temps_and_diff_DF.sort_values("difference", ascending = inverseSort, inplace = True)
    
    print(printStr)
    
    printHeader()
    
    for index, row in active_rads_w_temps_and_diff_DF.iterrows():
        printRow(row)

def getLatestTimestamp(connection):
    sortedUniqueSyncTimestamps = sorted(DBAccess.getUniqueSyncTimestamps(connection))
    
    if len(sortedUniqueSyncTimestamps) == 0:
        print("Error, no timestamps present. Have you logged any data yet?")
        sys.exit(2)
    elif len(sortedUniqueSyncTimestamps) == 1:
        print("Only one timestamp found, printing " + str(sortedUniqueSyncTimestamps[-1]))
        return sortedUniqueSyncTimestamps[-1]
    else:
        # print("Returning penultimate timestamp " + str(sortedUniqueSyncTimestamps[-2])) # Debug print
        # Note, we should usually return the punultimate timestamp incase the last one is being edited
        return sortedUniqueSyncTimestamps[-2]

def printLatestRadiatorSummary(connection):
    temperatures_DF = DBAccess.getTemperatureDataFrameForTimestamp(connection, getLatestTimestamp(connection))
    printRadiatorSummary(connection, temperatures_DF)

def printDataIndex(connection, dataIndex):
    sortedUniqueSyncTimestamps = sorted(DBAccess.getUniqueSyncTimestamps(connection))
    
    if dataIndex > len(sortedUniqueSyncTimestamps):
        print(f"dataIndex {dataIndex} greater than length of timestamps {len(sortedUniqueSyncTimestamps)}")
        sys.exit(2)
    
    timestamp = sortedUniqueSyncTimestamps[-dataIndex]
    printRadiatorSummary(connection, DBAccess.getTemperatureDataFrameForTimestamp(connection, timestamp))
    
def enterFollowModeLoop(connection):
    timestamp = getLatestTimestamp(connection)
    
    while(True):
        if not timestamp == getLatestTimestamp(connection):
            for i in range(62): print()
            timestamp = getLatestTimestamp(connection)
            printLatestRadiatorSummary(connection)
        time.sleep(2)

if __name__ == "__main__":
    
    databasePath = config["DatabaseSettings"].get("databasePath")
    dbConnection = DBAccess.create_connection(databasePath)
    
    for i in range(62): print()
    
    if(dataIndex != 0):
        printDataIndex(dbConnection, dataIndex)
        sys.exit(0)
        
    if(dataTimestamp != 0):
        printRadiatorSummary(DBAccess.getTemperatureDataFrameForTimestamp(dbConnection, dataTimestamp))
        sys.exit(0)
    
    printLatestRadiatorSummary(dbConnection)
    
    if inFollowMode :
        enterFollowModeLoop(dbConnection)
