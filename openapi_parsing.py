#Standard Python Modules
import json
import logging
import re
from typing import Any

#External Python Modules
from pydantic import BaseModel, Json, ValidationError

class ApiObject():
    def __init__(self, api_content:Json[Any]):
        self.api_content:Json[Any] = api_content
        self.api_version:str = api_content.get("openapi",None)      #TODO: Validate it is open API and version 3.x.x
        self.api_info:str = self.get_api_info()
        self.servers:list[str] = self.get_api_servers()
        self.paths:list[str] = self.get_api_objects("paths")
        self.schemas:list[str] = self.get_api_schemas()
        self.param_ref_dict:dict[str, ApiParameterRef] = {}  # dictionary of param reference name with associated paths & associated & characteristics
        self.param_dict:dict[str, ApiParameterField] = {}    # dictionary of param with associated paths & associated & characteristics
        self.schemas_dict:dict[str, ApiSchema] = {}          # dictionary of Schemas with associated characteristics
        self.request_fields_dict:dict[str, ApiRequestField] = {}    # dictionary of request fields with associated paths & associated & characteristics
        self.get_api_params()
        # TODO: get fields from paths request/response  + also schemas
        self.get_api_request_fields()

    def get_api_request_fields(self):
        # 1. get from component / schemas & get characteristics
        self.get_fields_from_schemas()
        # 4. get from path command (get, put, params), asssociate path &  characteristics
        self.get_fields_from_path_cmd()

    def parse_schema_type_object(self, schema_name, schema_specs):
        # Loop through all fields forr this schema object definition
        for field_name, properties in schema_specs.get("properties",{}).items():
            self.schemas_dict[schema_name].fields.append(field_name)                 # Add field_name to the list of fields associatedto this schema
            if field_name not in self.request_fields_dict:                           # Create new field object if not exists yet
                self.request_fields_dict[field_name] = ApiRequestField(field_name)
            self.request_fields_dict[field_name].add_schema(schema_name)
            self.request_fields_dict[field_name].add_properties(properties)
        
        for field_name in schema_specs.get("required",[]):                          # Flag all fields specified as required
            self.request_fields_dict[field_name].required = True
        
        for field_name, field_value in schema_specs.get("example",{}).items():       # Add sample values
            self.request_fields_dict[field_name].add_sample_value

    def get_fields_from_schemas(self):
       for schema_name_short, schema_specs in self.api_content.get("components",{}).get("schemas",{}).items():
            # Create Param File Object if not exists
            schema_name = "#/components/schemas/" + schema_name_short
            if schema_name not in self.schemas_dict:
                self.schemas_dict[schema_name]=ApiSchema(schema_name)
            
            schema_type = schema_specs.get("type",None)
            schema_lst = schema_specs.get("allOf",None) or schema_specs.get("oneOf",None)
            if schema_type:
                if schema_type == "object":
                    self.parse_schema_type_object(schema_name, schema_specs)
                elif schema_type == "string":
                    # skip as this represents a format for fields but not a field itself.
                    # TODO: eventually retrieve sample values
                    logging.debug(f"{schema_name} of type '{schema_type}' not supported/parsed")
                elif schema_type == "array":
                    # skip as this represents a format for fields but not a field itself.
                    # TODO: eventually retrieve sample values
                    logging.debug(f"{schema_name} of type '{schema_type}' not supported/parsed")
                else:
                    logging.warning(f"{schema_name} of type '{schema_type}' not supported/parsed")
            elif schema_lst:
                logging.warning(f"{schema_name} with allOf / oneOf")

            else:
                logging.warning(f"Schema '{schema_name}' doesn't have 1 of the following properties ['type', 'oneOf', 'allOf']\ntype='object' format assumed. Details of schema here after:\n{schema_specs}")
                self.parse_schema_type_object(schema_name, schema_specs)

    def get_field_names_from_schemas(self):
        pass

    def get_fields_from_path_cmd(self):
        # go to "responses/xxx/content" & "requestbody/content"
        # "requestbody/content/"application/json"/schema
        #     - "type": "array"
        #     - "$ref": "#/components/schemas/CreateUserInput"
        #     - "oneOf": [{"$ref": "#/components/schemas/UnregisterUserInputEx"}, {"$ref": "#/components/schemas/AdaptiveUnregisterUserInput"}],
        pass

    def get_api_info(self):
        api_info_dic = self.api_content.get("info",{})
        return api_info_dic.get("title", "") + " v" + api_info_dic.get("version", "")
    
    def get_api_objects(self, obj_name:str):
        api_obj = self.api_content.get(obj_name,{})
        obj_type = type(api_obj)
        if obj_type == dict:
            return sorted(api_obj.keys())
        elif obj_type == list:
            return api_obj
        else:
            return None

    def get_api_params(self):
        # 1. get from component / param & get characteristics
        self.get_param_references()
        # 2. Create all parameter name found in parameter reference
        self.get_param_name_from_references()
        # 3. get from url name & asssociate path
        self.get_param_from_path_name()
        # 4. get from path command (get, put, params), asssociate path &  characteristics
        self.get_param_from_path_cmd()

    def get_api_servers(self):
        api_servers_url_lst = [srv.get("url","") for srv in self.api_content.get("servers",[])]
        return sorted(api_servers_url_lst) 
        
    def get_api_schemas(self):
        api_schema_dic = self.api_content.get("components",{}).get("schemas",{})
        return sorted(api_schema_dic.keys())
      
    def get_param_from_path_cmd(self):
        for path in self.paths:
            for cmd, cmd_specs in self.api_content["paths"][path].items():
                if cmd =="parameters":      # case parameters are specified globally for the path, not per command
                    specs_lst = cmd_specs
                else:                       # case parameters are specified at the command level
                    specs_lst = cmd_specs.get("parameters",{})
                    for param in specs_lst:
                        param_name = param.get("name", "")
                        param_ref_name = param.get("$ref", "")
                        if param_ref_name:
                            param_specs = self.param_ref_dict.get(param_ref_name, ApiParameterRef).specs
                            param_name = param_specs.get("name","")          
                        elif param_name:
                            param_specs = param
                        else:
                            #TODO: Warning of parameter having no ref nor name
                            pass

                        if param_name and param_name not in self.param_dict:
                            self.param_dict[param_name]=ApiParameterField(param_name)
                        self.param_dict[param_name].add_spec(param_specs)
                        self.param_dict[param_name].add_path(path)

    def get_param_from_path_name(self):
        for path in self.paths:
            if "{" in path:
                current_params = re.findall(r"{(.*?)}", path)
                for current_param in current_params:
                    if current_param not in self.param_dict:
                        self.param_dict[current_param]=ApiParameterField(current_param)
                    self.param_dict[current_param].add_path(path)

    def get_param_name_from_references(self):
        for ref_name, ref_specs in self.param_ref_dict.items():
            param_specs = ref_specs.specs
            param_name = param_specs.get("name","")
            if not param_name:
                # TODO: print debug we have a param reference without name
                pass
            else:
                # Create Param File Object if not exists then add specifications
                if param_name not in self.param_dict:
                    self.param_dict[param_name]=ApiParameterField(param_name)
                self.param_dict[param_name].add_spec(param_specs)

    def get_param_references(self):
        for param_ref_name_short, param_specs in self.api_content.get("components",{}).get("parameters",{}).items():
            # Create Param File Object if not exists
            param_ref_name = "#/components/parameters/" + param_ref_name_short
            if param_ref_name not in self.param_ref_dict:
                self.param_ref_dict[param_ref_name]=ApiParameterRef(param_ref_name)
            self.param_ref_dict[param_ref_name].add_spec(param_specs)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        
class ApiParameterRef():
    def __init__(self, ref_name):
        self.ref_name:str = ref_name
        self.specs:dict = {}

    def add_spec(self, spec={}):       
        self.specs = spec

class ApiParameterField():
    def __init__(self, fieldname):
        self.fieldname:str = fieldname
        self.paths:list[str] = []
        self.specs:list[dict] = []

    def add_path(self, path=""):       
        if path and path not in self.paths:
            self.paths.append(path)
        
    def add_spec(self, spec={}):       
        if spec and spec not in self.specs:
            self.specs.append(spec)

class ApiSchema():
    def __init__(self, schemaname):
        self.schemaname:str = schemaname
        self.fields:list[str] = []
        self.paths:list[str] = []
        # self.properties:list[dict] = []
        # self.samples:list[dict] = []
    
    def add_path(self, path=""):       
        if path and path not in self.paths:
            self.paths.append(path)

class ApiRequestField():
    def __init__(self, fieldname):
        self.fieldname:str = fieldname
        self.schemas:list[str] = []
        self.paths:list[str] = []
        self.properties:list[dict] = []
        self.sample_values:list[str] = []
        self.required:bool = False
    
    def add_path(self, path=""):       
        if path and path not in self.paths:
            self.paths.append(path)

    def add_schema(self, schema=""):
        if schema and schema not in self.schemas:
            self.schemas.append(schema)
    
    def add_properties(self, properties={}):       
        if properties and properties not in self.properties:
            self.properties.append(properties)

    def add_sample_value(self, sample_value=""):       
        if sample_value and sample_value not in self.sample_values:
            self.sample_values.append(sample_value)
        
if __name__ == "__main__":
    import yaml
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s : %(levelname)s : %(message)s')

    test_file = "api_doc/oss.yaml"
    # test_file = "api_doc/pet_store.yaml"
    # test_file = "api_doc/tid.json"
    # test_file = "api_doc/WhoisEnrichment.json"
    # test_file = "api_doc/github.yaml"

    with open(test_file, encoding="UTF-8", errors="ignore") as config_file:
        f = yaml.safe_load(config_file)

    oss = ApiObject(f)
    # print (oss.api_info)
    # print (oss.api_version)
    # print("-" * 25, "servers", "-" * 25)
    # print (sorted(oss.servers))
    # print("-" * 25, "paths", "-" * 25)
    # print (oss.paths)
    # print("-" * 25, "schemas", "-" * 25)
    # print (oss.schemas)
    # print("-" * 25, "param_ref_dict_items", "-" * 25)
    # for field_name, field_object in sorted(oss.param_ref_dict.items()):
    #     print(field_object.ref_name, field_object.specs)
    # print("-" * 25, "param_ref_dict", "-" * 25)
    # print (sorted(oss.param_ref_dict))
    # print("-" * 25, "param_dict_items", "-" * 25)
    # for field_name, field_object in sorted(oss.param_dict.items()):
    #     print()
    #     print(field_object.fieldname, field_object.paths, field_object.specs)

    ### Print parameters in a structured way / tree
    ###############################################
    # print("-" * 25, "param_dict", "-" * 25)
    # print (sorted(oss.param_dict))
    # print()
    # for field_name, field_object in sorted(oss.param_dict.items()):
    #     print(f"{field_name}:")
    #     print(f"   Paths: {field_object.paths}")
    #     print(f"   Specifications:")
    #     for specs in field_object.specs:
    #         for k,v in specs.items():
    #             print(f"      {k}:{v}")
    #         print()
  
    ### Print request fields in a structured way / tree
    #####################################################
    print("-" * 25, "request_fields_dict", "-" * 25)
    print (sorted(oss.request_fields_dict))
    print()
    for field_name, field_object in sorted(oss.request_fields_dict.items()):
        print(f"{field_name}:")
        print(f"   Required: {field_object.required}")
        print(f"   Paths: {field_object.paths}")
        print(f"   Properties:")
        for properties in field_object.properties:
            for k,v in properties.items():
                print(f"      {k}:{v}")
            print()

    """
    ApenAPI Terminology:
    - Path param: param in the path (<=> url). Example: /users/{id}
    - Query param: example: /users?id=5
    - Header param
    - Cookie param
    ---- #TODO ---
    - Request Body
    - Response Body
    - Response Header
    - Security

    - Media Types: Media type is a format of a request or response body data. Web service operations can accept and return data in different formats, the most common being JSON, XML and images. You specify the media type in request and response definitions. Here is an example of a response definition:
    under responses.<code>.content.<media_type> 
"""