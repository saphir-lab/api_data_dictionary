### Import standard modules
from cmath import nan
import hashlib
from pathlib import Path

### Import external modules
import pandas as pd

### Import personal modules
from console import Console
from coloredlog import ColorLogger, get_logger, LOGLEVEL_SUCCESS, LOGLEVEL_DISABLE

### Read & write CSV File using Pandas dataframes
class CSVFile():
    def __init__(self, csv_filename:Path="", sep:str=";", chunksize:int=10000, logger:ColorLogger=None):
        self.filename = csv_filename
        self.separator = sep
        self.chunksize = chunksize
        self.content = pd.DataFrame()
        self.logger = ColorLogger()
        self.stat = pd.DataFrame()

        self.VALID_HASHING = ["blake2s", "blake2b", "md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha3_224", "sha3_256", "sha3_384", "sha3_512"]
        self.VALID_ALGORITHM = ["index", "length"] + self.VALID_HASHING
        
        if logger is None:
            self.logger = get_logger(logger_name="ParameterFile", console_loglevel=LOGLEVEL_DISABLE)
        else:
            self.logger = logger

    def get_chunk_iterator(self, chunksize:int):
        """

        Returns:
            [DataFrame iterator : [iterator to go to different chunk of DataFrame with CSV File content]
        """
        if not chunksize:
            chunksize = self.chunksize
        try:
            df_iterator = pd.read_csv(self.filename, 
                                        encoding="utf-8", 
                                        encoding_errors="ignore", 
                                        delimiter=self.separator, 
                                        low_memory=False, 
                                        dtype=str,
                                        chunksize=chunksize)
            # self.content = 
        except Exception as e:
            self.logger.error(f"Fail to load chunk iterator from CSV file '{self.filename}':")
            self.logger.error(f"{str(e)}")
        return df_iterator

    def get_stat(self) -> pd.DataFrame():
        """Return a DataFrame with various info on every columns from a source dataframe

        Args:
            df (DataFrame): Source DataFrame to Analyze

        Returns:
            DataFrame: A dataFrame with some statistics on each columns
        """
        self.stat = pd.DataFrame()
        if not self.content.empty:
            self.stat["column_name"]=list(self.content.columns)
            self.stat["nb_value"] = list(self.content.count())
            self.stat["nb_unique_value"] = list(self.content.nunique())
            
            df_len = self.content.applymap(lambda x: len(x), na_action="ignore")
            self.stat["min_length"]  = list(df_len.min())
            self.stat["max_length"] = list(df_len.max())
            self.stat["nb_unique_length"] = list(df_len.nunique())
            self.stat[["min_length", "max_length"]] = self.stat[["min_length", "max_length"]].fillna("0").astype(int)   ## Necessary step as numeric column with NaN value are considered as float
        return self.stat

    def hash_content(self, fields_to_transform:list, algorithm:str="blake2s", salt:str="", display_salt:bool=True) -> pd.DataFrame():
        # TO DO: Check if not better to transform the content of the object instead of returning an other Data Frame and not modifying object
        df_transformed = pd.DataFrame()
        algorithm_hash = ""
        missing_value = ""
        distinct_values = []
        VALID_HASHING = ["blake2s", "blake2b", "md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha3_224", "sha3_256", "sha3_384", "sha3_512"]

        if fields_to_transform:
            if algorithm in VALID_HASHING:
                if display_salt:
                    print(f"Salt: {salt}")
                if salt is None:
                    salt=""
                algorithm_hash = f"hashlib.{algorithm}(salt.encode() + x.encode()).hexdigest()"
                missing_value = nan
            elif algorithm=="length":
                algorithm_hash = f"len(x)"
                missing_value = 0
            elif algorithm=="index":
                for el in fields_to_transform:
                    distinct_value_col = self.content[el].dropna().unique()
                    distinct_values = distinct_values + list(set(distinct_value_col).difference(distinct_values))
                algorithm_hash = f"{distinct_values}.index(x)+1"
                missing_value = 0
            else:
                self.logger.error(f"Unknown Algorithm specified: {algorithm}")
            df_transformed = self.content[fields_to_transform].fillna("").applymap(
                lambda x: 
                    eval(algorithm_hash,{"hashlib":hashlib},{"salt":salt, "x":x}) if not x == "" else missing_value
            )
        return df_transformed

    def load(self) -> pd.DataFrame():
        """[Load and return a CSV file content as a pandas dataframe]

        Returns:
            [DataFrame]: [DataFrame with CSV File content]
        """
        try:
#            self.content = pd.read_csv(self.filename, encoding="UTF-8", delimiter=self.separator, low_memory=False, dtype=str)  # Force all columns as string
#           change encoding to "unicode_escape" in order to solve following error : utf-8' codec can't decode byte 0xae in position xxx: invalid start byte
#           come back to utf8 - but add parameter to ignore errors (seems encofing is not exactly utf-8)
            self.content = pd.read_csv(self.filename, encoding="utf-8", encoding_errors="ignore", delimiter=self.separator, low_memory=False, dtype=str)  # Force all columns as string
        except Exception as e:
            self.logger.error(f"Fail to load CSV file '{self.filename}':")
            self.logger.error(f"{str(e)}")
        else:
            (nb_rows, nb_columns) = self.content.shape
            self.logger.log(LOGLEVEL_SUCCESS, f"Successfully load CSV file '{self.filename}'")
            print(f"- File contains {nb_columns} columns and {nb_rows} lines")
        return self.content

    def load_sample(self, skiprows:int=0, nrows:int=10) -> pd.DataFrame():
        """[Load a part of CSV file and return content as a pandas dataframe]

        Returns:
            [DataFrame]: [DataFrame with CSV File content]
        """
        try:
            self.content = pd.read_csv(self.filename, 
                                        encoding="utf-8", 
                                        encoding_errors="ignore", 
                                        delimiter=self.separator, 
                                        low_memory=False, 
                                        dtype=str,
                                        skiprows=skiprows,
                                        nrows=nrows)
        except Exception as e:
            self.logger.error(f"Fail to load sample lines from CSV file '{self.filename}':")
            self.logger.error(f"{str(e)}")
        else:
            (nb_rows, nb_columns) = self.content.shape
            self.logger.log(LOGLEVEL_SUCCESS, f"Successfully load sample lines from CSV file '{self.filename}'")
            print(f"- File contains {nb_columns} columns")
        return self.content

    def save_content(self, csv_filename:Path, csv_separator:str="", header:bool=True, mode:str="w") -> bool:
        """[Save a pandas dataframe as CSV File]
            mode = 'w' will overwrite existing file (default)
            mode = 'a' will append to existing file (to be used in case of chunk)
        Returns:
            [Boolean]: True when successfully saved. False otherwise
        """
        if not csv_separator:
            csv_separator = self.separator
        try:
            self.content.to_csv(csv_filename, encoding="UTF-8", index=False, sep=csv_separator, header=header, mode=mode)
        except Exception as e:
            if mode == "w":
                self.logger.error(f"Fail to create CSV file '{csv_filename}':")
            elif mode == "a":
                self.logger.error(f"Fail to append content to CSV file '{csv_filename}':")
            else:
                pass
            self.logger.error(f"{str(e)}")
            return False
        else:
            if mode == "w":
                self.logger.log(LOGLEVEL_SUCCESS, f"Successfully create CSV file '{csv_filename}':")
            elif mode == "a":
                self.logger.log(LOGLEVEL_SUCCESS, f"Successfully append content to CSV file '{csv_filename}':")
            else:
                pass
            return True
    
    def save_stat(self, csv_filename:Path, csv_separator:str="") -> bool:
        """[Save a pandas statistics dataframe as CSV File]

        Returns:
            [Boolean]: True when successfully saved. False otherwise
        """
        if not csv_separator:
            csv_separator = self.separator
        try:
            self.stat.to_csv(csv_filename, encoding="UTF-8", index=False, sep=csv_separator)
        except Exception as e:
            self.logger.error(f"Fail to save CSV file '{csv_filename}':")
            self.logger.error(f"{str(e)}")
            return False
        else:
            self.logger.log(LOGLEVEL_SUCCESS, f"Successfully save CSV file '{csv_filename}'")
            return True
    

if __name__ == "__main__":
    import os
    CUR_DIR=os.path.dirname(os.path.abspath(__file__))
    APPNAME, _ = os.path.splitext(os.path.basename(__file__))
    OUT_DIR=os.path.join(CUR_DIR,"../out")
    OUTFILE1 = os.path.join(OUT_DIR,APPNAME+"_stat.csv")
    OUTFILE2 = os.path.join(OUT_DIR,APPNAME+"_hashed.csv")

    LOG_DIR=os.path.join(CUR_DIR,"../log")
    LOGFILE = None      # os.path.join(LOG_DIR,APPNAME+".log")
    logger = get_logger(logfile=LOGFILE)

    csvfile = os.path.join(CUR_DIR,"../data/sample.csv")
    csv_object =CSVFile(csvfile, sep=",", logger=logger)
    csv_object.load()
    # csv_object.get_stat()
    # csv_object.save_stat(OUTFILE1)
    # csv_object.content = csv_object.hash_content(fields_to_transform=["Country"])
    # csv_object.save_content(OUTFILE2)