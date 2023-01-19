# Release Notes

## v 1.0.0 - 19/01/2023

Version using **new python_boilerplate of 01/2023** with objects able to use same logfile as root
Functionalities:
- Able to parse openapi 3.X files (both yaml or json format).
- Generate output file with information about Schemas, Parameters & Fields present in openapi file.
- Each parameter/field is collected with following information:
    - Name
    - Required (Y/N).
    - Types (string, array, boolean, number, ...).
    - API path where used.
    - Description (list of all descriptions found on all API path).
    - Schema (useful to see additional information like sample value, accepted pattern, list of possible values (enum), etc.)
- Catalog can be generated as XLSX (default), Html or Json

