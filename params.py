# -*- coding: utf-8 -*-
import logging
import os
from banners import BANNERS
from utils.console import Console
from utils.coloredlog import LOGLEVEL_SUCCESS, LOGLEVEL_DISABLE
CONSOLE = Console(colored=True)
# In case you want to overwrite LOGLEVEL_SUCCESS
LOGLEVEL_SUCCESS = 25

# Some interresting path
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CUR_DIR,"data")
LOG_DIR = os.path.join(CUR_DIR,"log")
OUT_DIR = os.path.join(CUR_DIR,"out")

### Following parameters will be ingnore when using cli verion (as will be entered as parameters)
# Logging
# Possible values for a log level using logging module: CRITICAL:50; ERROR:40; WARNING:30; INFO:20, DEBUG:10
# Possible values for a log level using CONSTANTS (can be adapted in init.py): LOGLEVEL_SUCCESS:15; LOGLEVEL_DISABLE:99999
LOGLEVEL_CONSOLE = LOGLEVEL_SUCCESS
LOGLEVEL_FILE = LOGLEVEL_DISABLE
LOG_FILE = None     #Sample: os.path.join(LOG_DIR,"logfile.log")
OUT_FILE = None     #Sample: os.path.join(OUT_DIR,"output.csv")
IN_FILE = None      #Sample: os.path.join(DATA_DIR,"input.csv")

# Banner settings
BANNER_DISPLAY = True
BANNER_SELECTION = "random"


# List of Valid choices
VALID_JSON_EXTENSIONS =  [".json"]
VALID_YAML_EXTENSIONS =  [".yaml", ".yml"]
VALID_OPENAPI_EXTENSIONS =  VALID_JSON_EXTENSIONS + VALID_YAML_EXTENSIONS
VALID_OUTPUT_FORMAT = ["html", "json", "xlsx"]
INVALID_SEPARATOR = ['<', '>', ':', '"', '/', '\\\\', '|', '?','*']
API_OBJECTS = ["openapi", "info","servers", "paths", "components", "security", "tags", "externalDocs"]

if __name__ == "__main__":  
    CONSOLE.clear_screen()
    if BANNER_DISPLAY:
        print(CONSOLE.get_app_banner(selection=BANNER_SELECTION, banner_lst=BANNERS))

    print(f"- CUR_DIR: '{CUR_DIR}'")
    print(f"- DATA_DIR:'{DATA_DIR}'")
    print(f"- LOG_DIR: '{LOG_DIR}'")
    print(f"- OUT_DIR: '{OUT_DIR}'")