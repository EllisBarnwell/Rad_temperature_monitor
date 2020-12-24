import DBAccess
import configparser
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Load settings
config = configparser.ConfigParser()
config.read("Radiator_temp_logger.cnf")

def addDateColumn(sensorData):
    sensorData["formatted_timestamp_col"] = sensorData["syncTimestamp"].map(lambda ts: datetime.fromtimestamp(ts))

if __name__ == "__main__":
    databasePath = config["DatabaseSettings"].get("databasePath")
    dbConnection = DBAccess.create_connection(databasePath)

    groupings_data_query = "SELECT * FROM groupings"
    groupings_DF = pd.read_sql_query(groupings_data_query, dbConnection)
    
    active_groupings_DF = groupings_DF.loc[groupings_DF["isGroupingActiveBool"] != 0]
    
    fig, axs = plt.subplots(len(active_groupings_DF.index))
    
    plotIndex = 0
    for index, row in active_groupings_DF.iterrows():
        print("index = " + str(index))
        groupingsData = DBAccess.getDataForGrouping(dbConnection, row["grouping_id"])
        addDateColumn(groupingsData)
        groupingsFlowData = groupingsData.loc[groupingsData["flow1_return0"] == 1]
        groupingsReturnData = groupingsData.loc[groupingsData["flow1_return0"] == 0]
        axs[plotIndex].plot(groupingsFlowData["formatted_timestamp_col"], groupingsFlowData["tempDegC"], label="Flow", color="red")
        axs[plotIndex].plot(groupingsReturnData["formatted_timestamp_col"], groupingsReturnData["tempDegC"], label="Return", color="blue")
        axs[plotIndex].set_title(groupingsReturnData.iloc[0]["groupingPrettyName"], fontsize="10")
        axs[plotIndex].set(ylabel='Temp C')
        plotIndex += 1
    
    axs[0].legend()
    plt.tight_layout()
    plt.show()
