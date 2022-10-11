# -*- coding: utf-8 -*-
__author__ = 'P. Saint-Amand'
__version__ = 'V 0.3.0'

# Standard Python Modules
import json
import logging
from operator import contains
import os
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
all_args={}

def callback_format(value:str):
    if value.lower() not in VALID_OUTPUT_FORMAT:
        raise typer.BadParameter(f"Possible values for format are: {VALID_OUTPUT_FORMAT}")
    return value.lower()

def callback_version(value:bool):
    if value:
        print(f"Data Dictionary Builder version: {__version__}")
        raise typer.Exit()

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

def get_df_schemas(api_object:openapi_parsing.ApiObject):
    columns = [
    "Name",
    "Type",
    "Fields",
    "Paths"
    ]
    rows = []
    for schema_name, schema_object in sorted(api_object.schemas_dict.items()):      
        row = [
            schema_name,
            schema_object.type,
            "\n- ".join(sorted(schema_object.fields)),
            "\n- ".join(sorted(schema_object.paths)),
            ]
        for i in (2,3):
            if row[i]:
                row[i] = "- " + row[i]
        rows.append(row)
    
    df_schemas = pd.DataFrame(rows, columns=columns)
    return df_schemas

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
        logger.error(f"while retrieving file name elements using '{fullpath}':")
        logger.error(f"{str(e)}")
        raise typer.Abort()    
    return filename_elements

def get_logger(console_logging_level:int=0, logfile:Path=None):
    global SUCCESS

    SUCCESS = 25
    APPNAME, _ = os.path.splitext(os.path.basename(__file__))
    # CUR_DIR=os.path.dirname(os.path.abspath(__file__))
    # LOG_DIR=os.path.join(CUR_DIR,"log")
    # LOGFILE = os.path.join(LOG_DIR,APPNAME+".log")
    
    if not console_logging_level:
        console_logging_level=SUCCESS

    # Sample loggin creation with logging entries
    logging.addLevelName(SUCCESS, 'SUCCESS')
    log_options = utils.ColorLoggerOptions(logfile_name=logfile, console_logging_level=console_logging_level)
    logger = utils.ColorLogger(name=APPNAME, options=log_options)
    # save_logger_options(log_options)
    return logger

def load_openapi_file(filename):
    fe = get_filename_elements(filename)
    filetype = fe["fileextension"].lower()
    if filetype not in VALID_OPENAPI_EXTENSIONS:
            logger.error(f"Parameter file supports only following format: json, yml, yaml.")
            raise typer.Abort()
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
            raise typer.Abort()
        else:
            logger.log(SUCCESS, f"File '{filename}' successfuly loaded")
            return f

def report_overview(api_object:openapi_parsing.ApiObject):
    print(f"- Number of parameters : {len(api_object.param_dict)}")
    print(f"- Number of fields : {len(api_object.request_fields_dict)}")
    same_field_name = list(set(api_object.param_dict.keys()).intersection(api_object.request_fields_dict.keys()))
    print(f"- Number of Parameters with same name as a field: {len(same_field_name)}")
    print(f"{same_field_name}")

def report_table_summary(api_object:openapi_parsing.ApiObject, format:str, outfile:Path):
    df_schemas = get_df_schemas(api_object)  
    df_params = get_df_params(api_object)  
    df_fields = get_df_fields(api_object)
    df_common = pd.merge(df_params, df_fields, how="inner", on="Name", suffixes=('\n(param)', '\n(field)'))

    try:
        if format == "xlsx":
            save_to_xlsx(df_schemas, df_params, df_fields, df_common, outfile)
        elif format == "html":
            save_to_html(df_schemas, "Schemas", "out/schemas.html")
            save_to_html(df_params, "Params", "out/params.html")
            save_to_html(df_fields, "Fields", "out/fields.html")
            save_to_html(df_common, "Common Fields", "out/common.html")
        elif format == "json":
            save_to_json(api_object, outfile)
    except Exception as e:
        logger.error(f"Cannot save result to file '{outfile}'")
        logger.error(f"{str(e)}")
        raise typer.Abort()
    else:
        logger.log(SUCCESS,f"Result saved to file: '{outfile}'")

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

def save_to_xlsx(df_schemas, df_params, df_fields, df_common, outfile):
    writer = pd.ExcelWriter(outfile, engine= "xlsxwriter")
    df_schemas.to_excel(writer, index=False, sheet_name='Schemas', freeze_panes=(1,1))
    df_params.to_excel(writer, index=False, sheet_name='Params', freeze_panes=(1,1))
    df_fields.to_excel(writer, index=False, sheet_name='Fields', freeze_panes=(1,1))
    df_common.to_excel(writer, index=False, sheet_name='Common', freeze_panes=(1,1))
    
    if all_args["excel_with_layout"]:
        try:
            xls_formatting(writer=writer, sheet_name="Schemas", column_names=df_schemas.columns.values, settings={"A:A":50, "B:B":10, "C:C":35, "D:D":100})
            xls_formatting(writer=writer, sheet_name="Params", column_names=df_params.columns.values, settings={"A:A":30, "B:E":10, "F:H":100})
            xls_formatting(writer=writer, sheet_name="Fields", column_names=df_fields.columns.values, settings={"A:A":30, "B:D":10, "E:G":100})
            xls_formatting(writer=writer, sheet_name="Common", column_names=df_common.columns.values, settings={"A:A":30, "B:E":10, "F:H":100,"I:K":10, "L:N":100})
        except Exception as e:
            logger.error(f"Cannot customize excel file '{outfile}'")
            logger.error(f"{str(e)}")
        else:
            logger.log(SUCCESS,f"Extra layout/formatting applied to excel file")
    writer.close()

def save_to_html(df:pd.DataFrame, title:str, outfile:str):
    html_top = f"""
<!doctype html>
<html lang="en">
<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-Zenh87qX5JnK2Jl0vWa8Ck2rdkQ2Bzep5IDxbcnCeuOxjzrPF/et3URy9Bv1WTRi" crossorigin="anonymous">

    <title>Data Dictionary - {title}</title>
</head>
<body>
    <h1>Data Dictionary - {title}</h1>
    <div style="margin: 2rem;">
    """
    html_end = f"""
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.min.js" integrity="sha384-IDwe1+LCz02ROU9k972gdyvl+AESN10+x7tBKgc9I5HFtuNz0wWnPclzo6p9vxnk" crossorigin="anonymous"></script>
</body>
</html>
    """
    html_tbl = df.to_html(index=False, classes='table table-striped table-sm table-hover text-left', justify="left")
    html_tbl = html_tbl.replace("\\n","<br>")
    html_tbl = html_tbl.replace('<thead>', '<thead class="table-primary", style="vertical-align: middle">')
    html_tbl = html_tbl.replace('<tbody>', '<tbody class="table-group-divider">')

    with open(outfile, "w") as f:
        f.write(html_top)
        f.write(html_tbl)    
        f.write(html_end)
        
def save_to_json(api_object:openapi_parsing.ApiObject, outfile):   
    to_return={}
    params_lst=[]
    for k,v in sorted(api_object.param_dict.items()):
        params_lst.append(v.to_json())
    to_return["Parameters"]=params_lst

    fields_lst=[]
    for k,v in sorted(api_object.request_fields_dict.items()):
        fields_lst.append(v.to_json())
    to_return["Fields"]=fields_lst

    with open(outfile, "w") as f:
        json.dump(to_return, f, indent=4)

def validate_params():
    if not all_args["outfile"]:
        # output will be same location as input file
        outdir = os.path.dirname(os.path.abspath(all_args["openapi_file"]))
        filename, _ = os.path.splitext(os.path.basename(all_args["openapi_file"]))
        filename += "." + all_args["format"]
        all_args["outfile"] = os.path.join(outdir,filename)
    else:
        # retrieve path of output file specified as parameter
        outdir = os.path.dirname(os.path.abspath(all_args["outfile"]))
    
    # create output directory if not exists
    if not os.path.exists(outdir):
        logger.warning(f"Output directory doesn't exists: '{outdir}'")
        try:
            os.makedirs(outdir)                   
        except Exception as e:
            logger.error(f"Unable to create output directory '{outdir}':")
            logger.error(f"{str(e)}")
            raise typer.Abort()
        else:
            logger.log(SUCCESS, f"Output directory successfully created : '{outdir}'")

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

def main(openapi_file:Path = typer.Argument(..., exists=True, readable=True, resolve_path=True, show_default=False, help="The file name (with path) of the file to be analyzed. Both JSON and YAML formats are supported."),
        format:str = typer.Option("xlsx", "--format", "-f", help="Output format: cli, html, xlsx, json", callback=callback_format),
        outfile:Path = typer.Option(None, "--outfile", "-o", exists=False, resolve_path=True, show_default="Same path and filename (with new extension) as openapi_file", help="File Name of the output file"),
        banner:bool = typer.Option(True, help="Display a banner at start of the program", rich_help_panel="Customization and Utils"),
        debug:bool = typer.Option(False, help="Enable debug mode on the console", rich_help_panel="Customization and Utils"),
        excel_with_layout:bool = typer.Option(True, help="Do exta-formatting on all excel sheets", rich_help_panel="Customization and Utils"),
        logfile:Path = typer.Option(None, "--logfile", "-l", exists=False, resolve_path=True,  help="logfile of detailed activities (debug mode)", rich_help_panel="Customization and Utils"),
        version:bool = typer.Option(False, "--version", "-v", callback=callback_version, is_eager=True, help="Display version of the program", rich_help_panel="Customization and Utils")
        ):
    """
    Read an open API documentation file then extact all fields, parameter, etc.\n
    with format and definition then produce a matrix with different fields discovered with related API where they are used.\n
    """
    if banner:
        print(console.get_app_banner(selection="random", banner_lst=banner_lst, appversion=__version__, creator="Designed by " + __author__))
    #BUG - open_api_parsing doesn't take into account these parameters
    global logger
    if debug:
        logger = get_logger(console_logging_level=logging.DEBUG, logfile=logfile)
    else:
        logger = get_logger(logfile=logfile)
    logger.debug("Debug Mode Activated")

    # Put all arguments in a dictionnary & perform extra validation or default value assigment
    # Needed in order to be able to compare/ use value of other parameters, what was not possible using callback procedure
    all_args["openapi_file"]=openapi_file
    all_args["format"]=format
    all_args["outfile"]=outfile
    all_args["banner"]=banner
    all_args["debug"]=debug
    all_args["excel_with_layout"]=excel_with_layout
    all_args["logfile"]=logfile
    all_args["version"]=version
    validate_params()

    all_args_str=""
    for k,v in all_args.items():
        all_args_str += f"  - {k}: {v}\n"
    logger.debug(f"Parameters :\n{all_args_str}")

    api_content = load_openapi_file(all_args["openapi_file"])
    api_object = openapi_parsing.ApiObject(api_content)
    report_overview(api_object)
    report_table_summary(api_object, all_args["format"], all_args["outfile"])

    if all_args["logfile"]:
        logger.log(SUCCESS, f'logfile available on : {all_args["logfile"]}')
    
if __name__ == "__main__":
    console.clear_screen()
    typer.run(main)