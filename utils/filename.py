### Import standard modules
import datetime
import os

### Import external modules

### Import personal modules

### Retrieve various filename elements from a fullpath (path, name, extension, etc.)
class FileName():
    def __init__(self, fullpath="", colored=True):
        self.fullpath=fullpath
        self.fullpath_noextension=""
        self.filepath=""
        self.filename=""
        self.filename_noextension=""
        self.fileextension=""
        if fullpath:
            self.set_filename_elements(fullpath)

    def print_filename_details(self):
        print("- fullpath: " + self.fullpath)
        print("- fullpath no extension: " + self.fullpath_noextension)
        print("- filepath: " + self.filepath)
        print("- filename: " + self.filename)
        print("- filename no extension: " + self.filename_noextension)
        print("- file extension: " + self.fileextension)
        print()

    def set_filename_elements(self, fullpath):
        """ Retrieve various filename elements from a fullpath (path, name, extension, etc.) and initialize object
        """
        self.fullpath = fullpath
        try:
            self.filepath = os.path.dirname(self.fullpath)
            self.filename = os.path.basename(self.fullpath)
            self.filename_noextension, self.fileextension = os.path.splitext(self.filename)
            if self.filepath:
                self.fullpath_noextension = self.filepath + os.path.sep + self.filename_noextension
            else:
                self.fullpath_noextension = self.filename_noextension
        except Exception as e:
            print("ERROR", f"{str(e)}")

### Transform filename
    def change_filepath(self, new_filepath):
        """Change the location of current filename with new_filepath>
        """
        if new_filepath:
            new_fullpath = new_filepath + os.path.sep + self.filename
        else:
            new_fullpath = self.filename
        self.set_filename_elements(new_fullpath)
        return new_fullpath
 
    def add_subname(self, subname, sep="_"):
        """Add free text at the end of the filename using an optional text separator (default separator "_")
        """
        new_fullpath = self.fullpath_noextension + sep + subname + self.fileextension
        self.set_filename_elements(new_fullpath)
        return new_fullpath

    def add_dayonly(self, sep="_"):
        """Add date (YYMMDD) at the end of the filename using an optional text separator (default separator "_")
        """
        dt = datetime.datetime.now()      
        new_fullpath = self.fullpath_noextension + sep + dt.strftime('%Y%m%d') + self.fileextension
        self.set_filename_elements(new_fullpath)
        return new_fullpath

    def add_datetime(self, sep="_"):
        """Add timestamp (YYMMDD HHMMSS) at the end of the filename using an optional text separator (default separator "_")
        """
        dt = datetime.datetime.now()      
        new_fullpath = self.fullpath_noextension + sep + dt.strftime('%Y%m%d') + sep + dt.strftime('%H%M%S') + self.fileextension
        self.set_filename_elements(new_fullpath)
        return new_fullpath

if __name__ == "__main__":
    print("*** FileName details")
    filename = FileName(__file__)
    filename.print_filename_details()

    print("*** FileName modified details")
    filename.add_subname("subname")
    filename.add_datetime()
    filename.print_filename_details()

    #filename_modified = FileName(FileName(filename.add_subname("subname")).add_datetime())
    #filename_modified.print_filename_details()
