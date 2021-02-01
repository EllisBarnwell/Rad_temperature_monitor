#! /usr/bin/env python3

import DBAccess
import configparser
import pandas as pd

config = configparser.ConfigParser()
config.read("Radiator_temp_logger.cnf")

databasePath = config["DatabaseSettings"].get("databasePath")
dbConnection = DBAccess.create_connection(databasePath)

allData_DF = DBAccess.getAllData_DF(dbConnection)

# Export allData_DF as csv
allData_DF.to_csv ("export.csv", index = False, header=True)
