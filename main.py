### Import standard modules
import datetime
import json
import os
import re
import sys
from pathlib import Path
from pprint import pprint

### Import external modules
# from rich import print
from rich.console import Console
# from rich import print

import typer
import yaml

### Import personal modules
from constants import *
import utils

### Variables
console=utils.Console(colored=True)
err_console = Console(stderr=True)

def get_api_info(api_content):
    api_info_dic = api_content.get("info",{})
    api_info = api_info_dic.get("title", "") + " v" + api_info_dic.get("version", "")
    return api_info

def get_api_objects_presence(api_content):
    api_obj_presence_dict ={}
    for obj in API_OBJECTS:
        api_obj_presence_dict[obj] = bool(api_content.get(obj,{}))
    return api_obj_presence_dict

def get_api_paths(api_content):
    api_paths_dic = api_content.get("paths",{})
    api_paths = sorted(api_paths_dic.keys())
    return api_paths

def get_api_version(api_content):
    return api_content.get("openapi",None)

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

def get_url_params(api_content, api_paths):
    url_params={}
    for api_path in api_paths:
        if "{" in api_path:
            current_params = re.findall(r"{(.*?)}", api_path)
            for current_param in current_params:
                if url_params.get(current_param,[]):
                    url_params[current_param].append(api_path)
                else:
                    url_params[current_param] = [api_path]
    return url_params

def load_openapi_file(filename):
    fe = get_filename_elements(filename)
    filetype = fe["fileextension"].lower()
    if filetype not in VALID_OPENAPI_EXTENSIONS:
            console.print_msg("ERROR",f"Parameter file supports following format only: json, yml, yaml.")
    else:
        try:
            if filetype in VALID_JSON_EXTENSIONS:
                with open(filename, encoding="UTF-8", errors="ignore") as config_file:
                    f = json.load(config_file)
            elif filetype in VALID_YAML_EXTENSIONS:
                with open(filename, encoding="UTF-8", errors="ignore") as config_file:
                    f = yaml.safe_load(config_file)
        except Exception as e:
            console.print_msg("ERROR",f"with Parameter File '{filename}':")
            console.print_msg("ERROR",f"{str(e)}")
        else:
            console.print_msg("SUCCESS",f"Parameter file '{filename}' successfuly loaded")
            return f

def main(open_api_file: Path = typer.Argument(..., 
                                            exists=True,
                                            readable=True,
                                            resolve_path=True,
                                            help="The file path of the file to be analyzed. Both json and yaml formats are supported.")
                                            ):
    """Read an open API documentation file then extact all fields, parameter, etc.\n
        with format and definition then produce a matrix with different fields discovered with related API where they are used.\n
    """
    # err_console.print(f"Hello [bold red]{open_api_file}[/bold red]")
    api_content = load_openapi_file(open_api_file)
    
    api_info = get_api_info(api_content)
    print (api_info)

    api_paths = get_api_paths(api_content)
    print (f"{len(api_paths)} paths found")
    for i, api_path in enumerate(api_paths):
        print (f"{i+1}. {api_path}")
    print ("-"*20)

    url_params_with_path = get_url_params(api_content, api_paths)
    print (f"{len(url_params_with_path)} url params found")
    i=0
    for  url_param, paths_with_url in sorted(url_params_with_path.items()):
        i+=1
        print (f"{i}. {url_param} - found in {paths_with_url}")
    print ("-"*20)


    api_objects_exists = get_api_objects_presence(api_content)
    print (api_objects_exists)

    exit()
    cnt=0
    for i, api_path in enumerate(api_paths):
        for j, api_path_cmd in enumerate(api_content["paths"][api_path].keys()):  # Retrieve possible commands with this path (get, put, delete, etc)
            cnt += 1
            std_parameters = api_content["paths"][api_path][api_path_cmd].get("parameters",[]) # Retrieve list of standard parameters for that command
            sec_parameters = api_content["paths"][api_path][api_path_cmd].get("security",[])   # Retrieve list of security parameters for that command
            print (f"{cnt} - {i+1}.{j+1} {api_path_cmd} {api_path}")
            std_parameters_list = []
            ref_parameters_list = []
            for param in std_parameters:
                param_name = param.get("name","")                                              # Case of parameter description at that  level
                if param_name:
                    std_parameters_list.append(param_name)
                
                param_ref = param.get("$ref","")                                               # Case of parameter description in other place (usually 'component' level)
                if param_ref:
                    ref_parameters_list.append(param_ref)
            print (f"\t std_parameters_list: {std_parameters_list}")
            print (f"\t ref_parameters_list: {ref_parameters_list}")
            print (f"\t sec_parameters: {sec_parameters}")

if __name__ == "__main__":
    console.clear_screen()
    print(console.get_app_banner(selection="random", banner_lst=banner_lst, appversion=APP_VERSION, creator=DESIGNED_BY))
    typer.run(main)