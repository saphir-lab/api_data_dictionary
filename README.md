# api_data_dictionary
This script builds a data dictionary from openapi/swagger documentation (version 3.x)

The dictionary contains all the parameters/fields name discovered in the openapi file together with their characteristics (Required (Y/N), Types (string, array, boolean, number, ...), API path where used, list of descriptions, ...)

## Usage
You need to specify at least one argument in order tu run the script(path of the openapi file):

```bash
python main.py openapi.json
```


>**Note**: *for more information about possible parameters, type:*
>
> ```bash
> python main.py --help
> ```
