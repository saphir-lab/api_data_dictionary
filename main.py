# Standard Python Modules
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict

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

def get_df_params(api_object:openapi_parsing.ApiObject):
    columns = [
    "Name",
    "Required",
    "Locations",
    "Types",
    "Nb Path",
    "Paths",
    "Descriptions",
    "Schemas",
    # "Specs"
    ]
    rows = []
    for field_name, field_object in sorted(api_object.param_dict.items()):
        schemas_str = ""
        for schema in field_object.schemas:
            schemas_str += "- " + str(schema) + "\n"
        spec_str = ""
        for spec in field_object.specs:
            spec_str += "- " + str(spec) + "\n"
        
        row = [
            field_name,
            field_object.required,
            "\n".join(sorted(field_object.locations)),
            "\n".join(sorted(field_object.schema_types)),
            len(field_object.paths),
            "\n- ".join(sorted(field_object.paths)),
            "\n- ".join(field_object.descriptions),
            schemas_str,
            # spec_str
            ]
        for i in (5,6):
            if row[i]:
                row[i] = "- " + row[i]

        rows.append(row)
    
    df_params = pd.DataFrame(rows, columns=columns)
    return df_params

def get_df_fields(api_object:openapi_parsing.ApiObject):
    columns = [
    "Name",
    "Required",
    "Types",
    "Nb Path",
    "Paths",
    "Descriptions",
    "Schemas"
    ]
    rows = []

    for field_name, field_object in sorted(api_object.request_fields_dict.items()):
        schemas_str = ""
        for schema in field_object.properties:
            schemas_str += "- " + str(schema) + "\n"
       
        row = [
            field_name,
            field_object.required,
            "\n".join(sorted(field_object.types)),
            len(field_object.paths),
            "\n- ".join(sorted(field_object.paths)),
            "\n- ".join(field_object.descriptions),
            schemas_str,
            # spec_str
            ]
        for i in (4,5):
            if row[i]:
                row[i] = "- " + row[i]
        rows.append(row)
    df_fields = pd.DataFrame(rows, columns=columns)
    return df_fields

def report_table_summary(api_object:openapi_parsing.ApiObject):
    df_params = get_df_params(api_object)  
    df_fields = get_df_fields(api_object)
    df_common = pd.merge(df_params, df_fields, how="inner", on="Name", suffixes=('\n(param)', '\n(field)'))

    writer = pd.ExcelWriter("out/outcome.xlsx", engine= "xlsxwriter")
    df_params.to_excel(writer, index=False, sheet_name='Params', freeze_panes=(1,1))
    df_fields.to_excel(writer, index=False, sheet_name='Fields', freeze_panes=(1,1))
    df_common.to_excel(writer, index=False, sheet_name='Common', freeze_panes=(1,1))
   
    # TODO: pass do_formatting as parameter
    do_formatting=True
    if do_formatting:
        xls_formatting(writer=writer, sheet_name="Params", column_names=df_params.columns.values, settings={"A:A":30, "B:E":10, "F:H":100})
        xls_formatting(writer=writer, sheet_name="Fields", column_names=df_fields.columns.values, settings={"A:A":30, "B:D":10, "E:G":100})
        xls_formatting(writer=writer, sheet_name="Common", column_names=df_common.columns.values, settings={"A:A":30, "B:E":10, "F:H":100,"I:K":10, "L:N":100})

    writer.close()

def xls_formatting(writer:pd.ExcelWriter, sheet_name:str, column_names:list, settings:dict):
    wb = writer.book
    ws = writer.sheets[sheet_name]

    fmt_cells = wb.add_format({"text_wrap": True, "valign": "top"})
    for k, v in settings.items():
        ws.set_column(k,v,fmt_cells)
    # ws.autofilter('A1:H1')
    ws.autofilter(0,0,0,len(column_names)-1)

    fmt_header = wb.add_format({
    "bold": True,
    "text_wrap": True,
    "valign": "top",
    "fg_color": "#4F81BD",
    "font_color": "#FFFFFF",
    "border": 1})
    for col , value in enumerate(column_names):
        ws.write(0, col, value, fmt_header)

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
    report_table_summary(api_object)
    
if __name__ == "__main__":
    console.clear_screen()
    print(console.get_app_banner(selection="random", banner_lst=banner_lst, appversion=APP_VERSION, creator=DESIGNED_BY))
    typer.run(main)