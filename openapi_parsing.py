# Standard Python Modules
import json
import re
import sys
from typing import Any

# External Python Modules
from pydantic import Json

# Personal Python Modules
import utils

#Logging module configuration
logger = utils.ColorLogger(name=__name__)

def default(obj):
    if hasattr(obj, 'to_json'):
        return obj.to_json()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

def method_name():
    return sys._getframe(  ).f_back.f_code.co_name

class ApiObject():
    def __init__(self, api_content:Json[Any]):
        logger.debug(f"ApiObject - Start initialization")
        self.api_content:Json[Any] = api_content                    # Prerequisite - All other methosds will pick-up data from this field
        self.api_version:str = api_content.get("openapi",None)      # TODO: Validate it is open API and version 3.x.x
        self.api_info:str = self.get_api_info()
        self.servers:list[str] = self.get_api_servers()
        self.paths:list[str] = self.get_api_paths()
        self.param_ref_dict:dict[str, ApiParameterRef] = self.get_param_references()  # dictionary of param reference name with associated paths & associated & characteristics
        self.param_dict:dict[str, ApiParameterField] = {}    # dictionary of param with associated paths & associated & characteristics
        self.schemas_dict:dict[str, ApiSchema] = {}          # dictionary of Schemas with associated fields
        self.request_fields_dict:dict[str, ApiRequestField] = {}    # dictionary of request fields with associated paths & associated & characteristics
        self._get_api_params()
        self._get_api_request_fields()

    def _extract_info_from_field_properties(self):
        logger.debug(f"{method_name()} - Start")
        for field_name, field_object in sorted(self.request_fields_dict.items()):
            for spec in field_object.properties:
                self.request_fields_dict[field_name].add_description(spec.get("description",""))
                self.request_fields_dict[field_name].add_type(spec.get("type",""))
    
    def _extract_info_from_param_specs(self):
        logger.debug(f"{method_name()} - Start")
        for field_name, field_object in sorted(self.param_dict.items()):
            for spec in field_object.specs:
                self.param_dict[field_name].add_description(spec.get("description",""))
                self.param_dict[field_name].add_required(spec.get("required",False))
                self.param_dict[field_name].add_location(spec.get("in",""))
                self.param_dict[field_name].add_schema(spec.get("schema",{}))
                self.param_dict[field_name].add_schema_type(spec.get("schema",{}).get("type",""))

    def _get_api_params(self):
        logger.debug(f"{method_name()} - Start")
        ### Prereq : self.param_ref_dict populated
        self._get_param_from_references()        # get all parameter name found in parameter reference
        self._get_param_from_path_name()         # get from url name & asssociate path
        self._get_param_from_path_cmd()          # get from path command (get, put, params), asssociate path &  characteristics
        self._extract_info_from_param_specs()    # Parse the specs collected in order to extact additioal dedicated info like description, location, etc
        logger.info(f"{method_name()} - {len(self.param_dict)} parameters found in total.")

    def _get_api_request_fields(self):
        logger.debug(f"{method_name()} - Start")
        self._get_schemas_and_fields()       # get from component/schemas & get characteristics
        self._get_fields_from_path_cmd()     # get from path command (get, put, params) then asssociate path & characteristics
        self._extract_info_from_field_properties()    # Parse the properties collected in order to extact additioal dedicated info like description, type, etc
        logger.info(f"{method_name()} - {len(self.request_fields_dict)} fields found in total.")

    def _get_fields_from_path_cmd(self):
        # goals : add path to 
        #       schemas found ($ref)
        #       fields linked to that schema
        #       fields not related to schema

        # go to "responses/xxx/content" & "requestbody/content"
        # "requestbody/content/"application/json"/schema
        #     - "type": "object"
        #     - "type": "array"
        #     - "$ref": "#/components/schemas/CreateUserInput"
        #     - "oneOf": [{"$ref": "#/components/schemas/UnregisterUserInputEx"}, {"$ref": "#/components/schemas/AdaptiveUnregisterUserInput"}],
        logger.debug(f"{method_name()} - Start")
        for path in self.paths:
            logger.debug(f"{method_name()} - Processing path '{path}'")
            for cmd, cmd_specs in self.api_content["paths"][path].items():
                # cmd_specs can be an array in case body is using multiple templates
                if type(cmd_specs) == dict:
                    cmd_specs= [cmd_specs]  # transfrom single entry as list
                elif type(cmd_specs) == list:
                    pass                    #keep as it is
                else:
                    logger.warning(f"{method_name()} - unknown format for path '{path}', command {cmd}, type:{type(cmd_specs)}")
                    logger.debug(f"{method_name()} - {cmd} details:\n{cmd_specs}")
                
                for spec in cmd_specs:
                    self._parse_requestBody(path, cmd, spec)
                    self._parse_responses(path, cmd, spec)

        logger.info(f"{method_name()} - {len(self.request_fields_dict)} fields found from now.")

    def _get_param_from_path_cmd(self):
        logger.debug(f"{method_name()} - Start")
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
                        logger.warning(f"{method_name()} - Parameter element without $ref nor name.")
                        logger.debug(f"{method_name()} - Parameter details:\n{param}")
                    if param_name and param_name not in self.param_dict:
                        self.param_dict[param_name]=ApiParameterField(param_name)
                    self.param_dict[param_name].add_spec(param_specs)
                    self.param_dict[param_name].add_path(path)
        logger.info(f"{method_name()} - {len(self.param_dict)} parameters found from now.")

    def _get_param_from_path_name(self):
        logger.debug(f"{method_name()} - Start")
        for path in self.paths:
            if "{" in path:
                logger.debug(f"{method_name()} - retrieving parameter(s) from path {path}")
                current_params = re.findall(r"{(.*?)}", path)
                for current_param in current_params:
                    if current_param not in self.param_dict:
                        self.param_dict[current_param]=ApiParameterField(current_param)
                    self.param_dict[current_param].add_path(path)
                    self.param_dict[current_param].add_location("path")

        logger.info(f"{method_name()} - {len(self.param_dict)} parameters found from now.")

    def _get_param_from_references(self):
        logger.debug(f"{method_name()} - Start")
        for ref_name, ref_specs in self.param_ref_dict.items():
            param_specs = ref_specs.specs
            param_name = param_specs.get("name","")
            if not param_name:
                logger.error(f"{method_name()} - parameter with no name: {param_specs}")
            else:
                # Create Param File Object if not exists then add specifications
                if param_name not in self.param_dict:
                    self.param_dict[param_name]=ApiParameterField(param_name)
                self.param_dict[param_name].add_spec(param_specs)
        logger.info(f"{method_name()} - {len(self.param_dict)} parameters found from now.")

    def _get_schemas_and_fields(self):
        logger.debug(f"{method_name()} - Start")
        for schema_name_short, schema_specs in self.api_content.get("components",{}).get("schemas",{}).items():
            # Create Param File Object if not exists
            self._parse_one_schema(schema_name_short, schema_specs)
        logger.info(f"{method_name()} - {len(self.request_fields_dict)} fields found from now.")

    def _parse_one_schema(self, schema_name_short, schema_specs):
            schema_name = "#/components/schemas/" + schema_name_short
            if schema_name not in self.schemas_dict:
                self.schemas_dict[schema_name]=ApiSchema(schema_name)
            self._parse_schema_specs(schema_name, schema_specs)                  

    def _parse_one_schema_field(self, field_name, properties, schema_name):
            #1. Create field if not exists
            if field_name not in self.request_fields_dict:
                self.request_fields_dict[field_name] = ApiRequestField(field_name)
            #2. Link field to schema & schema to field
            if schema_name:
                self.schemas_dict[schema_name].add_field(field_name)                    # Add field_name to the list of fields associated to this schema
                self.request_fields_dict[field_name].add_schema(schema_name)
            #3. Add field properties
            self.request_fields_dict[field_name].add_properties(properties)
            #4. if properties contains schema reference, process that schema
            ref=properties.get("$ref","")
            if not ref:
                ref=properties.get("items",{}).get("$ref","")
            if ref:
                # Get short name, retrieve specs, then process this schema if not yet done
                ref_short= ref[ref.rfind('/')+1:]
                logger.debug(f"Schema {schema_name} - Processing Schema reference {ref} --> {ref_short}")
                schema_specs = self.api_content.get("components",{}).get("schemas",{}).get(ref_short,{})
                if ref not in self.schemas_dict:
                    self._parse_one_schema(schema_name_short=ref_short, schema_specs=schema_specs)
                # add fields of referenced schema to current one
                if schema_name:
                    for field_ref in self.schemas_dict.get(ref,ApiSchema(ref)).fields:
                        self.schemas_dict[schema_name].add_field(field_ref)                    # Add field_name to the list of fields associated to this schema
                        self.request_fields_dict[field_ref].add_schema(schema_name)
    
    def _parse_requestBody(self, path, cmd, spec):
        body_content = spec.get("requestBody",{}).get("content",{})
        for media_type, media_object in body_content.items():
            body_schema = media_object.get("schema",{})
            body_schema_type = body_schema.get("type", "")
            body_schema_ref = body_schema.get("$ref", "")
            full_path = f"{path}/{cmd}/requestBody/content/{media_type}"

            fields_to_add_path = []
            if body_schema_ref:
                self.schemas_dict[body_schema_ref].add_path(path)             # Associate path to the schema
                fields_to_add_path = self.schemas_dict[body_schema_ref].fields
            elif body_schema_type:                                       
                if body_schema_type == "object":
                    fields_to_add_path = self._parse_schema_type_object(schema_name="", schema_specs=body_schema)
                elif body_schema_type == "array":
                    fields_to_add_path = self._parse_schema_type_array(schema_name="", schema_specs=body_schema)
                else:
                    logger.warning(f"{method_name()} - {full_path} - schema type '{body_schema_type}' doesn't not contains field name. Considered as a bad practive for body part")
                    logger.debug(f"{method_name()} - Schema details: {body_schema}")
            else:
                logger.warning(f"{method_name()} - {full_path} - schema without $ref or type.")
                logger.debug(f"{method_name()} - Schema details\n{body_schema}")
            
            # Associate path to all fields of the schema
            logger.debug(f"{method_name()} - Add path {path} to fields {fields_to_add_path}")
            for field in fields_to_add_path:                     
                self.request_fields_dict.get(field, ApiRequestField(field)).add_path(path)

    def _parse_responses(self, path, cmd, spec):
        #TODO: Parse responses ?
        pass

    def _parse_schema_specs(self, schema_name="", schema_specs={}):
        schema_type = schema_specs.get("type",None)
        schema_lst = schema_specs.get("allOf",None) or schema_specs.get("oneOf",None)
        if schema_type:
            if schema_type == "object":
                self._parse_schema_type_object(schema_name, schema_specs)
            elif schema_type == "string":
                # skip as this represents a format for fields but not a field itself.
                logger.debug(f"{method_name()} - Schema '{schema_name}' of type '{schema_type}' not supported/parsed")
            elif schema_type == "array":
                self._parse_schema_type_array(schema_name, schema_specs)
            else:
                logger.warning(f"{method_name()} - Schema '{schema_name}' of type '{schema_type}' not supported/parsed")
        elif schema_lst:
            # TODO: allOf / oneOf
            logger.debug(f"{method_name()} - Schema '{schema_name}' with allOf / oneOf")

        else:
            logger.warning(f"{method_name()} - Schema '{schema_name}' doesn't have 1 of the following properties ['type', 'oneOf', 'allOf'] -> type='object' format assumed.")
            logger.debug(f"{method_name()} - Schema '{schema_name}' details:\n{schema_specs}")
            self._parse_schema_type_object(schema_name, schema_specs)
     
    def _parse_schema_type_array(self, schema_name="", schema_specs={}):
        fields_parsed=[]
        ref=schema_specs.get("items", "").get("$ref","")
        fields_parsed = self.schemas_dict.get(ref,ApiSchema(ref)).fields
        # add fields of referenced schema to current one
        if schema_name:
            for field_ref in self.schemas_dict.get(ref,ApiSchema(ref)).fields:
                self.schemas_dict[schema_name].add_field(field_ref)                    # Add field_name to the list of fields associated to this schema
                self.request_fields_dict[field_ref].add_schema(schema_name)

        return fields_parsed

    def _parse_schema_type_object(self, schema_name, schema_specs):
        fields_parsed=[]
        # Loop through all fields for this schema object definition
        for field_name, properties in schema_specs.get("properties",{}).items():
            fields_parsed.append(field_name)
            self._parse_one_schema_field(field_name, properties, schema_name)
        
        for field_name in schema_specs.get("required",[]):                          # Flag all fields specified as required
            if field_name not in self.request_fields_dict:                          # Create new field object if not exists yet
                self.request_fields_dict[field_name] = ApiRequestField(field_name)
            self.request_fields_dict[field_name].required = True
        return fields_parsed

    def get_api_info(self):
        logger.debug(f"{method_name()} - Start")
        api_info_dic = self.api_content.get("info",{})
        return api_info_dic.get("title", "") + " v" + api_info_dic.get("version", "")

    def get_api_paths(self):
        logger.debug(f"{method_name()} - Start")
        api_obj = self.api_content.get("paths",{})
        obj_type = type(api_obj)
        if obj_type == dict:
            return_value = sorted(api_obj.keys())
        elif obj_type == list:
            return_value = api_obj
        else:
            return_value = None
        if return_value:
            logger.info(f"{method_name()} - {len(return_value)} paths found.")
        else:
            logger.warning(f"{method_name()} - No paths found !!!") 
        return return_value
  
    def get_api_schemas(self):
        logger.debug(f"{method_name()} - Start")
        api_schema_dic = self.api_content.get("components",{}).get("schemas",{})
        if api_schema_dic:
            logger.info(f"{method_name()} - {len(api_schema_dic)} schemas found.")
        else:
            logger.warning(f"{method_name()} - No schemas found !!!")
        return sorted(api_schema_dic.keys())
    
    def get_api_servers(self):
        logger.debug(f"{method_name()} - Start")
        api_servers_url_lst = [srv.get("url","") for srv in self.api_content.get("servers",[])]
        return sorted(api_servers_url_lst)    
  
    def get_param_references(self):
        logger.debug(f"{method_name()} - Start")
        param_ref_dict = {}
        for param_ref_name_short, param_specs in self.api_content.get("components",{}).get("parameters",{}).items():
            # Create Param File Object if not exists
            param_ref_name = "#/components/parameters/" + param_ref_name_short
            if param_ref_name not in param_ref_dict:
                param_ref_dict[param_ref_name]=ApiParameterRef(param_ref_name)
            param_ref_dict[param_ref_name].add_spec(param_specs)
        return param_ref_dict

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        
class ApiParameterRef():
    def __init__(self, ref_name:str):
        self.ref_name:str = ref_name
        self.specs:dict = {}

    def __str__(self):
        return self.ref_name

    def __repr__(self):
        return self.__str__()

    def add_spec(self, spec:dict):       
        self.specs = spec
 
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class ApiParameterField():
    def __init__(self, fieldname:str):
        self.fieldname:str = fieldname
        self.descriptions:set(str) = set()
        # self.examples:list() = []         # TODO 'example' calue can be of different type (int, str, but also object). Skip forthe moment as don't know how it will behave
        self.locations:set(str) = set()
        self.paths:set(str) = set()
        self.required:bool = False
        self.schemas:list(dict) = []
        self.schema_types:set(str) = set()
        self.specs:list[dict] = []

    def __iter__(self):
        yield from {
            "fieldname": self.fieldname,
            "descriptions": self.descriptions,
            "locations": self.locations,
            "paths": self.paths,
            "required": self.required,
            "schemas": self.schemas,
            "schema_types": self.schema_types,
            "spec": self.specs
        }.items()

    def __str__(self):
        return self.fieldname

    def __repr__(self):
        return self.__str__()

    def add_description(self, description:str):
        if description:
            self.descriptions.add(description)
    
    def add_location(self, location:str):
        if location:
            self.locations.add(location)

    def add_path(self, path:str):
        if path:
            self.paths.add(path)
    
    def add_required(self, required:bool):
        if bool:
            self.required=required

    def add_schema(self, schema:dict):
        if schema and schema not in self.schemas:
            self.schemas.append(schema)

    def add_schema_type(self, schema_type:str):
        if schema_type:
            self.schema_types.add(schema_type)

    def add_spec(self, spec:dict):       
        if spec and spec not in self.specs:
            self.specs.append(spec)

    def to_json(self, indent=None):
        to_return = {"fieldname": self.fieldname, "descriptions": list(self.descriptions), "locations":list(self.locations), "paths": list(self.paths), "required":self.required,
                     "schemas": list(self.schemas), "schema_types": list(self.schema_types), "specs": list(self.specs)
                     }
        return json.dumps(to_return, indent=indent)

class ApiSchema():
    def __init__(self, schemaname:str):
        self.schemaname:str = schemaname
        self.fields:set(str) = set()
        self.paths:set(str) = set()
        # self.properties:list[dict] = []
        # self.samples:list[dict] = []

    def __str__(self):
        return self.schemaname

    def __repr__(self):
        return self.__str__()
    
    def add_path(self, path:str):
        if path:
            self.paths.add(path)

    def add_field(self, fieldname:str):
        if fieldname:
            self.fields.add(fieldname)
    
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class ApiRequestField():
    def __init__(self, fieldname:str):
        self.fieldname:str = fieldname
        self.descriptions:set(str) = set()
        self.paths:set(str) = set()
        self.properties:list[dict] = []
        self.required:bool = False
        self.schemas:set(str) = set()
        self.types:set(str) = set()
    
    def __str__(self):
        return self.fieldname

    def __repr__(self):
        return self.__str__()

    def add_description(self, description:str):
        if description:
            self.descriptions.add(description)

    def add_path(self, path:str):
        if path:
            self.paths.add(path)

    def add_properties(self, properties:dict):
        if properties and properties not in self.properties:
            self.properties.append(properties)

    def add_schema(self, schema:str):
        if schema:
            self.schemas.add(schema)
    
    def add_type(self, type:str):
        if type:
            self.types.add(type)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
   
if __name__ == "__main__":
    import yaml
    # logger.basicConfig(level=logger.DEBUG,format='%(asctime)s : %(levelname)s : %(message)s')
    # logger.basicConfig(level=logger.INFO,format='%(asctime)s : %(levelname)s : %(message)s')

    test_file = "api_doc/oss.yaml"
    # test_file = "api_doc/pet_store.yaml"
    # test_file = "api_doc/tid.json"
    # test_file = "api_doc/WhoisEnrichment.json"
    # test_file = "api_doc/jikan.json"
    # test_file = "api_doc/github.yaml"

    with open(test_file, encoding="UTF-8", errors="ignore") as config_file:
        f = yaml.safe_load(config_file)

    # TODO 1 : Check if when returning __str__ as fieldname for each classes if I cannot change dictionnary of objects as a set of objects instead in ApiObject
    # TODO 2 : serialize different element to json. see endpage of https://changsin.medium.com/how-to-serialize-a-class-object-to-json-in-python-849697a0cd3
    oss = ApiObject(f)
    for k, v in oss.param_dict.items():
        print (f"- {k}: {v.to_json()}\n")
    exit()
   
   
   
   
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
    # # print("-" * 25, "param_ref_dict", "-" * 25)
    # print (sorted(oss.param_ref_dict))
    # print("-" * 25, "param_dict_items", "-" * 25)
    # for field_name, field_object in sorted(oss.param_dict.items()):
    #     print()
    #     print(field_object.fieldname, field_object.paths, field_object.specs)

    ### Print schema in a structured way / tree
    ###############################################
    print("-" * 25, "schemas_dict summary", "-" * 25)
    print (sorted(oss.schemas_dict))
    print(f"{len(oss.schemas_dict)} schemas found.")
    print("-" * 25, "schemas_dict details", "-" * 25)
    for schema_name, schema_object in sorted(oss.schemas_dict.items()):
        print(f"Schema '{schema_name}':")
        print(f"   Paths: {schema_object.paths}")
        print(f"   Fields: {schema_object.fields}")

    ## Print parameters in a structured way / tree
    ##############################################
    print("-" * 25, "param_dict summary", "-" * 25)
    print (sorted(oss.param_dict))
    print(f"{len(oss.param_dict)} parameters found.")
    print("-" * 25, "param_dict details", "-" * 25)
    for field_name, field_object in sorted(oss.param_dict.items()):
        print(f"Param field '{field_name}':")
        print(f"   Paths: {field_object.paths}")
        print(f"   Required: {field_object.required}")
        print(f"   Descriptions: {field_object.descriptions}")
        print(f"   Locations: {field_object.locations}")
        print(f"   types: {field_object.schema_types}")
        print(f"   schemas: {field_object.schemas}")
        print(f"   Specifications: {field_object.specs}")
        # for specs in field_object.specs:
        #     for k,v in specs.items():
        #         print(f"      {k}:{v}")
        #     print()
    
   
    ### Print request fields in a structured way / tree
    #####################################################
    # print("-" * 25, "request_fields_dict summary", "-" * 25)
    # print(sorted(oss.request_fields_dict))
    # print(f"{len(oss.request_fields_dict)} request fields found.")
    # print("-" * 25, "request_fields_dict details", "-" * 25)
    # for field_name, field_object in sorted(oss.request_fields_dict.items()):
    #     print(f"Request field '{field_name}':")
    #     print(f"   Required: {field_object.required}")
    #     print(f"   Schemas: {field_object.schemas}")
    #     print(f"   Paths: {field_object.paths}")
    #     print(f"   Properties: {field_object.properties}")
    #     print(f"   Types: {field_object.types}")
    #     print(f"   Descriptions: {field_object.descriptions}")


    """
    ApenAPI Terminology:
    - Path param: param in the path (<=> url). Example: /users/{id}
    - Query param: example: /users?id=5
    - Header param
    - Cookie param
    - Request Body
    ---- #TODO type of field ---
    - Response Body
    - Response Header
    - Security

    - Media Types: Media type is a format of a request or response body data. Web service operations can accept and return data in different formats, the most common being JSON, XML and images. You specify the media type in request and response definitions. Here is an example of a response definition:
    under responses.<code>.content.<media_type> 
"""