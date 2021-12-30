# Quick setup guide for the NodeMCU radiator sensor

This system is designed to measure the flow and return temperatures of radiators using a set of NodeMCU (ESP8266) units with two DS18B20 temperature sensors attached to each.

The NodeMCU units must be attached to a WiFi connection along with a computer acting as a data logger. This code will query the NodeMCU units and pool data into an sqlite database.

This is a quick guide to setting up the system.

## 1. Set up of the NodeMCU units
    To set up the NodeMCU units, it's advisable to use the Arduino IDE
    
    After installing Arduino IDE, the ESP8266 board URL needs adding. Navigate to preferences and under "Additional Boards Manager URLs" add the following URL, separated by a comma
    
    http://arduino.esp8266.com/stable/package_esp8266com_index.json
    
    Add the ESP8266 boards by selecting Tools -> Board -> Boards Manager and then searching ESP8266.
    
    Install the DallasTemperature, OneWire and ArduinoJson packages
    
    Once this is done, load the code Arduino_src/WS_TemperatureReading/WS_TemperatureReading.ino file into the Arduino IDE
    
    Enter the WiFi SSID and password into the network credentials stored in the header file Arduino_src/WS_TemperatureReading/WS_TemperatureReading.h. Click upload to flash the board.
    
    To get the IP address of the unit, open a serial monitor with Tools -> Serial Monitor. The IP address will be printed as the unit boots. To get the IP to show, either restart the unit or reupload the code with the serial monitor open.
    
    Note, the baud rate should be set to 9600

## 2. Attach sensors

    The sensors must be attached to the pins for 3.3V, GND and a data pin. The data pin used can be changed in the arduino code and the default value is pin 2 (which is marked as D4).
    
    Any number of sensors can be attached in parallel to the same data pin.

## 3. Access data with web services
    Once the NodeMCU unit is powered on, the data can be accessed via a web service using port 80.
    
    Using a tool such as curl, test this web service by typing http://<IPAddress>:80 where the IP address is the unit under test. You should get a response in JSON similar to the following which will give a list of sensorIDs and temperatures
    
    [{"SensorID":"280afa983c190152","TempDegC":29.3125},{"SensorID":"286de379a20103a7","TempDegC":35.0625}]
    
    At this point, you may want to work out the ID of each sensor and make a note so you can keep track later.
    
    Note, if you enter the IP address into a web browser it will by default sent an http request to port 80 so should return the same response

## 4. Python environment
    All python source is contained in the folder Python_src
    
    Be sure to be using at least python 3.7 and install the following packages
    
    - requests
    - matplotlib
    - pandas
    
    These are also present in the requirements.txt file in the python_src folder.
    
    Note, I think more than this may actually needed, e.g. sqlite3. Please feed back if additional requirements are needed

## 5. Set up database tables (CreateDBTables.py)
    If you would like to start with a fresh database, the necessary tables can be set using the command
    
        python CreateDBTables.py
    
    There are 3 tables in the sql database these are
    
        goupings - A group of sensors, in this case this will correspond to a specific radiator
        sensors - This table holds sensor information and is linked to grouping with the grouping_id
        temperature_data - This is where all of the temperature data is stored, it's linked to the sensors table with sensorID

## 6. Setting up the config file (Radiator_temp_logger.cnf)
    Edit this Radiator_temp_logger.cnf file to meet your needs. In particular, the two fields that will need changing are
    
        databasePath - Set this to the path where you want to store the database. This can be anywhere but it's advisable to keep it within the project folder
        ipAddresses - This is the list of IP addresses for all devices in the system. IP addresses must be in quotes, separated by commas and surrounded by square brackets

## 7. Populate the database and set up test (ReadDataIntoDB.py)
    The database is populated by the python script ReadDataIntoDB.py. This script should always be running when you want to be acquiring data. In linux, it may be desireable to set this up as a service.
    
    The first time this script runs it will automatically add all of the sensors into the table and generate a default grouping with index 0.
    
    Now that the sensors are present, you can label them with pretty names and also short names.
    
    You should group the sensors using groupings. For each radiator, add a row into the grouping table. Give the radiator a pretty name and make sure it is set to active (non active groups or sensors may not appear in the software).
    
    In the sensor table, select the grouping_id for the appropriate radiator. Avoid using grouping_id 0 as new sensors will be added with this id. The grouping_id must be present in the grouping table before they can be selected by the sensor.
    
    For each sensor, you must fill in whether it is attached to a flow or return pipe using the code 1 for flow and 0 for return.
    
    In most cases, each radiator will have exactly one flow sensor and one return sensor. Some elements of the software will get confused if this is not the case. It may be desireable to attach multiple sensors to one pipe, for example when testing reliability of sensors or calibrating. This shouldn't be a problem as elements of the software that don't use the flow/return flag will work as normal.
    
## 8. Print database values (PrintDatabaseValues.py)
    The values from the database can be viewed directly as they're acquired using the python script PrintDatabaseValues.py.
    
    The number of database rows to print is set in the .cnf file with nRowsToPrint. If this value is set to -1, it will print all rows in the database.
    
    The header is reprinted periodically and how often this is printed can be set in the config.
    
    The sensor short names should are used as the table headers and should be kept to 4 characters. The order they appear in the table is alphanumeric so if you want them to appear in a particular order, it's advisable to name them 01XX, 02XX etc. A code can be used, for example 01KF and 02KR may be the flow and return sensors in the kitchen.
    
    If data is missing, the space will be filled with the string " -- ".
    
    Only sensors marked with isSensorActiveBool as 1 will show in this table.
    
    It is possible to separate data sets with a duff column. Just add a column into the database with a nonsense sensorID and change the short name so it appears where desired. This can be handy for separating sensors into pairs.

## 9. Plotting data (PlotData.py)
    The data can be plotted using matplotlib with the python script plotData.py.
    
    This package is not fantastic but is very simple to use and will show a set of plots with flow and return temperatures for each grouping marked with isGroupingActiveBool as 1.

## 10. Radiator summaries (PrintRadiatorSummaries.py)
    A summary table showing the flow/return temperatures as well as the difference for each radiator marked with isGroupingActiveBool as 1 can be viewed with the script PrintRadiatorSummaries.py.
    
    This is probably the most useful tool for viewing temperatures when balancing radiators.
    
    This table can be sorted by flow temp, return temp or difference, either ascending or descending.
    
    The data for a particular time can be printed using a unix timestamp (seconds since 1970).
    
    Also, the data can be by index, starting from the most recent entry.
    
    Data can be viewed in follow mode which means it is updated each time a new database entry is added. Note, we generally show the penultimate entry to avoid clashes if the ultimate entry is still being edited. (The ultimate entry can be viewed with the --index 1 option).
    
    Run the following to get the help text
    
    python PrintRadiatorSummaries.py -h
    
## 11. Export to CSV (exportCSV.py)
    A CSV export of the data can be acquired using the exportCSV.py script. When the script is run, all data associated with the current configuration is exported to export.csv in the same directory as the script.
    
## 12. Calibration
    TODO
    
