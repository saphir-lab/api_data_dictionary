# Standard Python Modules
import datetime
import json
import logging
import os
import sys
from pathlib import Path

# External Python Modules
import pandas as pd
import typer
import yaml

# Personal Python Modules
from constants import *
import utils
import openapi_parsing

### Variables
console=utils.Console(colored=True)

def get_filename_elements(fullpath):
    filename_elements={}
    try:
        filename_elements["fullpath"]=fullpath
        filename_elements["filepath"] = os.path.dirname(fullpath)
        filename_elements["filename"] = os.path.basename(fullpath)
        filename_elements["filename_noextension"], filename_elements["fileextension"] = os.path.splitext(filename_elements["filename"])
        if filename_elements["filepath"]:
            filename_elements["fullpath_noextension"] = filename_elements["filepath"] + os.path.sep + filename_elements["filename_noextension"]
        else:
            filename_elements["fullpath_noextension"] = filename_elements["filename_noextension"]
    except Exception as e:
        console.print_msg("ERROR", f"{str(e)}")
    return filename_elements

def load_openapi_file(filename):
    fe = get_filename_elements(filename)
    filetype = fe["fileextension"].lower()
    if filetype not in VALID_OPENAPI_EXTENSIONS:
            logger.error(f"Parameter file supports only following format: json, yml, yaml.")
            #err_console.print(f"[bold red]ERROR [/bold red] - Parameter file supports only following format: json, yml, yaml.")
            exit()      
    else:
        try:
            if filetype in VALID_JSON_EXTENSIONS:
                with open(filename, encoding="UTF-8", errors="ignore") as config_file:
                    f = json.load(config_file)
            elif filetype in VALID_YAML_EXTENSIONS:
                with open(filename, encoding="UTF-8", errors="ignore") as config_file:
                    f = yaml.safe_load(config_file)
        except Exception as e:
            logger.error(f"while loading file '{filename}':")
            logger.error(f"{str(e)}")
        else:
            logger.log(SUCCESS, f"File '{filename}' successfuly loaded")
            return f

def save_logger_options(log_options:utils.ColorLoggerOptions):
    # with open("log_settings.json", "w") as lo:
    #     json.dump(log_options.__dict__ , lo) 
    print (log_options.console_formatter.__class__)
    print (log_options.console_formatter._fmt)
    print (log_options.logfile_formatter._fmt)
    print (log_options.__dict__)

    # for attr in dir(log_options):
    #     print("obj.%s = %r" % (attr, getattr(log_options, attr)))
    pass

def get_logger():
    global SUCCESS

    SUCCESS = 25
    APPNAME, _ = os.path.splitext(os.path.basename(__file__))
    CUR_DIR=os.path.dirname(os.path.abspath(__file__))
    LOG_DIR=os.path.join(CUR_DIR,"log")
    LOGFILE = os.path.join(LOG_DIR,APPNAME+".log")
    # LOGFILE = APPNAME+".log"

    # Sample loggin creation with logging entries
    logging.addLevelName(SUCCESS, 'SUCCESS')
    log_options = utils.ColorLoggerOptions(logfile_name=LOGFILE, console_logging_level=SUCCESS)
    logger = utils.ColorLogger(name=APPNAME, options=log_options)
    # save_logger_options(log_options)
    return logger

def report_overview(api_object:openapi_parsing.ApiObject):
    print(f"- Number of parameters : {len(api_object.param_dict)}")
    print(f"- Number of fields : {len(api_object.request_fields_dict)}")
    same_field_name = list(set(api_object.param_dict.keys()).intersection(api_object.request_fields_dict.keys()))
    print(f"- Number of Parameters with same name as a field: {len(same_field_name)}")
    print(f"{same_field_name}")


def report_params_overview(api_object:openapi_parsing.ApiObject):
    for field_name, field_object in sorted(api_object.param_dict.items()):
        print(f"- {field_name}: {field_object.paths}")

def report_params_summary(api_object:openapi_parsing.ApiObject):
    for field_name, field_object in sorted(api_object.param_dict.items()):
        print(f"Param field '{field_name}':")
        print(f"   - Paths: {field_object.paths}")
        print(f"   - Specifications: {field_object.specs}")
        print()

def report_params_details(api_object:openapi_parsing.ApiObject):
    for field_name, field_object in sorted(api_object.param_dict.items()):
        print(f"Param field '{field_name}':")
        print(f"   - Paths:")
        for path in field_object.paths:
            print (f"      - {path}")
        print(f"   - Specifications:")
        for specs in field_object.specs:
            print (f"      - {specs}")

        print()
        # for specs in field_object.specs:
        #     for k,v in specs.items():
        #         print(f"      {k}:{v}")
        #     print()

def get_df_params_summary(api_object:openapi_parsing.ApiObject):
    param_names = []
    param_nb_paths = []
    param_nb_specs = []
    for field_name, field_object in sorted(api_object.param_dict.items()):
        param_names.append(field_name)
        param_nb_paths.append(len(field_object.paths))
        param_nb_specs.append(len(field_object.specs))
    
    params = {
    "Name": param_names,
    "Param": True,
    "Nb Path (param)": param_nb_paths,
    "Nb Specs (param)": param_nb_specs,
    }
    # df_params = pd.DataFrame(params, index=param_names)
    df_params = pd.DataFrame(params)
    df_params["Param"].astype(bool)
    return df_params

def get_df_fields_summary(api_object:openapi_parsing.ApiObject):
    field_names = []
    field_required = []
    field_nb_paths = []
    field_nb_specs = []
    for field_name, field_object in sorted(api_object.request_fields_dict.items()):
        field_names.append(field_name)
        field_required.append(field_object.required)
        field_nb_paths.append(len(field_object.paths))
        field_nb_specs.append(len(field_object.properties))
    fields = {
    "Name": field_names,
    "Field": True,
    "Required": field_required,
    "Nb Path (field)": field_nb_paths,
    "Nb Specs (field)": field_nb_specs
    }
    df_fields = pd.DataFrame(fields)
    df_fields["Field"].astype(bool)
    return df_fields

def report_table_summary(api_object:openapi_parsing.ApiObject):
    df_params = get_df_params_summary(api_object)
    # print(df_params)
    df_fields = get_df_fields_summary(api_object)
    # print(df_fields)
    df_all = pd.merge(df_params, df_fields, how="outer", on="Name")
    df_all.fillna({"Param":False, "Field":False}, inplace=True)
    print(df_all)
    # print(df_all.describe(include = 'all'))


def main(open_api_file: Path = typer.Argument(..., 
                                            exists=True,
                                            readable=True,
                                            resolve_path=True,
                                            help="The file path of the file to be analyzed. Both json and yaml formats are supported.")
                                            ):
    """Read an open API documentation file then extact all fields, parameter, etc.\n
        with format and definition then produce a matrix with different fields discovered with related API where they are used.\n
    """
    global logger 
    logger = get_logger()
    api_content = load_openapi_file(open_api_file)
    api_object = openapi_parsing.ApiObject(api_content)
    report_overview(api_object)   
    # report_params_overview(api_object)   
    # report_params_summary(api_object)   
    # report_params_details(api_object)
    report_table_summary(api_object)
    
if __name__ == "__main__":
    console.clear_screen()
    print(console.get_app_banner(selection="random", banner_lst=banner_lst, appversion=APP_VERSION, creator=DESIGNED_BY))
    typer.run(main)