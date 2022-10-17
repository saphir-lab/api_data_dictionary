# -*- coding: utf-8 -*-
__author__ = 'P. Saint-Amand'
__version__ = 'V 0.4.3'

# Standard Python Modules
import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any

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

def build_html_table(title:str, df:pd.DataFrame) -> str:
    div_header =  f"""<div class="accordion-item">
        <h2 class="accordion-header" id="{title}">
          <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse{title}" aria-expanded="false" aria-controls="collapse{title}">
            {title}
          </button>
        </h2>
        <div id="collapse{title}" class="accordion-collapse collapse" aria-labelledby="{title}" data-bs-parent="#accordion_openapi">
          <div class="accordion-body">
    """
    html_tbl = df.to_html(index=False, classes='table table-striped table-sm table-hover text-left', justify="left")
    html_tbl = html_tbl.replace("\\n","<br>")
    html_tbl = html_tbl.replace('<thead>', '<thead class="table-primary", style="vertical-align: middle">')
    html_tbl = html_tbl.replace('<tbody>', '<tbody class="table-group-divider">')
    result = div_header + html_tbl + "</div></div></div>"
    return result

def callback_format(value:str) -> str:
    if value.lower() not in VALID_OUTPUT_FORMAT:
        raise typer.BadParameter(f"Possible values for format are: {VALID_OUTPUT_FORMAT}")
    return value.lower()

def callback_outdir(value:Path) -> Path:
    if value and not value.is_dir() and os.path.splitext(value)[1]:
        raise typer.BadParameter(f"outdir must be a DIRECTORY (not a file)")
    return value

def callback_version(value:bool) -> None:
    if value:
        print(f"Data Dictionary Builder version: {__version__}")
        raise typer.Exit()

def get_df_params(api_object:openapi_parsing.ApiObject) -> pd.DataFrame:
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

def get_df_schemas(api_object:openapi_parsing.ApiObject) -> pd.DataFrame:
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

def get_df_fields(api_object:openapi_parsing.ApiObject) -> pd.DataFrame:
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

def get_filename_elements(fullpath) -> dict[str,str]:
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

def get_logger(console_logging_level:int=0, logfile:Path=None) -> utils.ColorLogger:
    global SUCCESS
    SUCCESS = 25
    APPNAME, _ = os.path.splitext(os.path.basename(__file__))
    
    if not console_logging_level:
        console_logging_level=SUCCESS

    logging.addLevelName(SUCCESS, 'SUCCESS')
    log_options = utils.ColorLoggerOptions(logfile_name=logfile, console_logging_level=console_logging_level)
    logger = utils.ColorLogger(name=APPNAME, options=log_options)
    # save_logger_options(log_options)
    return logger

def load_openapi_file(filename) -> Any:
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

def report_overview(api_object:openapi_parsing.ApiObject) -> None:
    print(f"- Number of parameters : {len(api_object.param_dict)}")
    print(f"- Number of fields : {len(api_object.request_fields_dict)}")
    same_field_name = list(set(api_object.param_dict.keys()).intersection(api_object.request_fields_dict.keys()))
    print(f"- Number of Parameters with same name as a field: {len(same_field_name)}")
    print(f"{same_field_name}")

def report_table_summary(api_object:openapi_parsing.ApiObject, format:str, outfile:Path) -> None:
    df_schemas = get_df_schemas(api_object)  
    df_params = get_df_params(api_object)  
    df_fields = get_df_fields(api_object)
    df_common = pd.merge(df_params, df_fields, how="inner", on="Name", suffixes=('\n(param)', '\n(field)'))

    try:
        if format == "xlsx":
            df_dict = {
                "Schemas": (df_schemas,{"A:A":50, "B:B":10, "C:C":35, "D:D":100}),
                "Parameters": (df_params,{"A:A":30, "B:E":10, "F:H":100}),
                "Fields": (df_fields,{"A:A":30, "B:D":10, "E:G":100}),
                "Common": (df_common, {"A:A":30, "B:E":10, "F:H":100,"I:K":10, "L:N":100})
                }
            save_to_xlsx(df_dict, outfile)
        elif format == "html":
            df_dict = {
                "Parameters": df_params,
                "Fields": df_fields,
                "Common": df_common
                }
            save_to_html(df_dict, outfile)
        elif format == "json":
            save_to_json(api_object, outfile)
    except Exception as e:
        logger.error(f"Cannot save result to file '{outfile}'")
        logger.error(f"{str(e)}")
        raise typer.Abort()
    else:
        logger.log(SUCCESS,f"Result saved to file: '{outfile}'")

def save_logger_options(log_options:utils.ColorLoggerOptions) -> None:
    with open("logger_options.json", "w") as lo:
        lo.write(log_options.to_json(indent=4)) 

def save_to_html(df_dict:dict[str,pd.DataFrame], outfile:Path) -> None:
    html_top = f"""
<!doctype html>
<html lang="en">
<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <!-- Optional meta tags -->
    <meta name="description" content="Data Dictionary from openapi">
    <meta name="author" content="{__author__}">
    <meta name="generator" content="Python script">

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-Zenh87qX5JnK2Jl0vWa8Ck2rdkQ2Bzep5IDxbcnCeuOxjzrPF/et3URy9Bv1WTRi" crossorigin="anonymous">

    <title>Data Dictionary - {os.path.basename(all_args["openapi_file"])}</title>
</head>
<body>
    <h1>Data Dictionary</h1>
    <div style="margin: 2rem;">
    <hr>    
    <article><strong>Source: </strong>{os.path.abspath(all_args["openapi_file"])}</article>
    <article><strong>Generated on: </strong>{datetime.datetime.now()}</article>
    <hr>
    <div class="accordion" id="accordion_openapi">
    """
    html_end = f"""
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.min.js" integrity="sha384-IDwe1+LCz02ROU9k972gdyvl+AESN10+x7tBKgc9I5HFtuNz0wWnPclzo6p9vxnk" crossorigin="anonymous"></script>
</body>
</html>
    """
    with open(outfile, "w") as f:
        f.write(html_top)
        for title, df in df_dict.items():
            f.write(build_html_table(title, df))    
        f.write(html_end)
       
def save_to_json(api_object:openapi_parsing.ApiObject, outfile:Path) -> None:   
    with open(outfile, "w") as f:
        json.dump(api_object.to_dict(), f, indent=4)

def save_to_xlsx(df_dict:dict[str,tuple[pd.DataFrame, dict[str,str]]], outfile=Path) -> None:
    writer = pd.ExcelWriter(outfile, engine= "xlsxwriter")
    for title,(df,col_size) in df_dict.items():
        df
        df.to_excel(writer, index=False, sheet_name=title, freeze_panes=(1,1))
        if all_args["excel_with_layout"]:
            try:
                xls_formatting(writer=writer, sheet_name=title, column_names=df.columns.values, settings=col_size)
            except Exception as e:
                logger.error(f"Cannot customize excel file '{outfile}'")
                logger.error(f"{str(e)}")
            else:
                logger.log(SUCCESS,f"Extra layout/formatting applied on sheet '{title}'")
    writer.close()

def validate_params() -> None:
    # Generate default value for missing outfile and/or outdir parameters
    if all_args["outfile"] and all_args["outdir"]:  # Both parameters have been specified
        all_args["outdir"] = os.path.dirname(os.path.abspath(all_args["outfile"]))
        logger.warning(f"Both outdir and outfile parameters specified. outdir overwrite with path of outfile : {all_args['outdir']}")
    elif all_args["outdir"]:        # only outdir has been specified
        filename, _ = os.path.splitext(os.path.basename(all_args["openapi_file"]))
        filename += "." + all_args["format"]
        all_args["outfile"] = os.path.join(all_args["outdir"],filename)
    elif all_args["outfile"]:       # only outfile has been specified
        all_args["outdir"] = os.path.dirname(os.path.abspath(all_args["outfile"]))
    else:                           # No parameter specified regarding output
        all_args["outdir"] = os.path.dirname(os.path.abspath(all_args["openapi_file"]))
        filename, _ = os.path.splitext(os.path.basename(all_args["openapi_file"]))
        filename += "." + all_args["format"]
        all_args["outfile"] = os.path.join(all_args["outdir"],filename)

    # create output directory if not exists
    outdir=all_args["outdir"]
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

    # Adapt file extension if not correct
    file_name, file_ext = os.path.splitext(all_args["outfile"])
    if not file_ext == "."+all_args["format"]:
        all_args["outfile"]= file_name + "." + all_args["format"]
        logger.warning(f"Outfile extension '{file_ext}' doesn't correspond to requested output format '{'.'+all_args['format']}'")
        logger.warning(f"Outfile has be adapted to '{all_args['outfile']}'")

def xls_formatting(writer:pd.ExcelWriter, sheet_name:str, column_names:list[str], settings:dict[str,str]) -> None:
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
        outdir:Path = typer.Option(None, "--outdir", "-d", exists=False, resolve_path=True, show_default="Same directory as openapi_file", help="Locaton of the output file", callback=callback_outdir),
        outfile:Path = typer.Option(None, "--outfile", "-o", exists=False, resolve_path=True, show_default="Same directory and filename (with new extension) as openapi_file", help="File Name of the output file"),
        banner:bool = typer.Option(True, help="Display a banner at start of the program", rich_help_panel="Customization and Utils"),
        debug:bool = typer.Option(False, help="Enable debug mode on the console", rich_help_panel="Customization and Utils"),
        excel_with_layout:bool = typer.Option(True, help="Do exta-formatting on all excel sheets", rich_help_panel="Customization and Utils"),
        logfile:Path = typer.Option(None, "--logfile", "-l", exists=False, resolve_path=True,  help="logfile of detailed activities (debug mode)", rich_help_panel="Customization and Utils"),
        version:bool = typer.Option(False, "--version", "-v", callback=callback_version, is_eager=True, help="Display version of the program", rich_help_panel="Customization and Utils")
        ) -> None:
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
    global all_args
    all_args["openapi_file"]=openapi_file
    all_args["format"]=format
    all_args["outdir"]=outdir
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