#Generic Classes that will need to be adapted by each fork of this API.

import json
import os
import datetime

# API version for metadata; bump as needed when API changes
API_VERSION = "1.0"


class ActionBase:
    #Action Data will be a dictionary containing all relevant information for the action to be performed.  Create one for each case.
    def __init__(self, action_data, on_complete=None, case=None):
        self.action_data = action_data
        # on_complete will be called as on_complete(result, error)
        self.on_complete = on_complete
        # optional reference to CaseClass
        self.case = case

    # Each subclass should implement this method to perform the specific action.
    def perform_action(self):
        raise NotImplementedError("Subclasses should implement this method.")
    
    def mySchema(self):
        raise NotImplementedError("Subclasses should implement this method.")
    
    def correctActionData(self, action_data):
        #Check all action data entries.
        resultantActionData = {}
        for key in action_data:
            if action_data[key] is None:
                raise ValueError(f"Action data key '{key}' cannot be None")
            if not isinstance(action_data[key], dict):
                #This one is older style, make the value into a dictionary with 'value' key
                action_data[key] = {'value': action_data[key]}
            if action_data[key].get('value', None) is None:
                action_data[key]['value'] = ''
            if 'units' not in action_data[key]:
                action_data[key]['units'] = ''
            else:
                #It did come with a Unit.  Now we check the Unit from the mySchema function
                schema = self.mySchema()
                if 'properties' in schema and key in schema['properties']:
                    expected_unit = schema['properties'][key].get('x-units', '')
                    if expected_unit != '' and action_data[key]['units'] != expected_unit:
                        #Determine unit objects for both and see if they are convertible
                        expected_unit_obj = None
                        provided_unit_obj = None
                        for unit in AllUnits:
                            if unit.unitString == expected_unit or expected_unit in unit.alternateStrings:
                                expected_unit_obj = unit
                            if unit.unitString == action_data[key]['units'] or action_data[key]['units'] in unit.alternateStrings:
                                provided_unit_obj = unit
                        if expected_unit_obj is not None and provided_unit_obj is not None:
                            if not expected_unit_obj.convertibleTo(provided_unit_obj):
                                raise ValueError(f"Action data key '{key}' has unit '{action_data[key]['units']}' which is not convertible to expected unit '{expected_unit}'")
                            #Convert the value to the expected unit
                            original_value = action_data[key]['value']
                            converted_value = provided_unit_obj.convertTo(expected_unit_obj, original_value)
                            action_data[key]['value'] = converted_value
                            action_data[key]['units'] = expected_unit
                        else:
                            raise ValueError(f"Action data key '{key}' has unit '{action_data[key]['units']}' which cannot be converted to expected unit '{expected_unit}'")
            resultantActionData[key] = action_data[key]['value']
        return resultantActionData

    def perform_action_async(self):
        import threading

        def _runner():
            try:
                result = self.perform_action()
                if callable(self.on_complete):
                    try:
                        self.on_complete(result, None)
                    except TypeError:
                        # fallback: single-arg callback
                        self.on_complete(result)
            except Exception as e:
                if callable(self.on_complete):
                    try:
                        self.on_complete(None, e)
                    except TypeError:
                        self.on_complete(e)

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        return thread

class ResultsBase:
    #Results Data will be a dictionary containing all relevant information for the results to be processed.  Create one for each case.
    def __init__(self, resultsFolder):
        self.resultsFolder = resultsFolder
        self.resultsType = "Table"  # Default type; subclasses can override

    # Each subclass should implement this method to process the specific results.
    def process_results(self):
        raise NotImplementedError("Subclasses should implement this method.")
    
    def getData(self):
        result_file = os.path.join(self.resultsFolder, "results.json")
        if not os.path.exists(result_file):
            raise FileNotFoundError("Result file not found.")
        with open(result_file, 'r') as f:
            data = json.load(f)
        return data
    

class jobClass:
    #Job Data will be a dictionary containing all relevant information for the job to be handled.
    def __init__(self, ActionClass=None, ResultsClasses=None):
        self.projectID = None
        self.revID = None
        self.batchUUID = None
        self.cases = []
        self.batchFolder = None
        self.dateCreated = None
        self.apiVersion = API_VERSION
        # Store configured classes for use when creating cases
        self.ActionClass = ActionClass if ActionClass is not None else ActionBase
        self.ResultsClasses = ResultsClasses if ResultsClasses is not None else [ResultsBase]
    
    def asJson(self):
        import json
        job_dict = {
            'projectID': self.projectID,
            'revID': self.revID,
            'batchUUID': self.batchUUID,
            'cases': [],
            'status': "Completed"
        }
        for c in self.cases:
            if c.caseStatus != "Completed" and c.caseStatus != "Failed":
                job_dict['status'] = "In Progress"
            else:
                if c.caseStatus == "Failed":
                    job_dict['status'] = "Failed"
            job_dict['cases'].append({
                'caseNumber': getattr(c, 'caseNumber', None),
                'caseStatus': getattr(c, 'caseStatus', None),
                'case_data': getattr(c, 'case_data', {})
            })

        
        return json.dumps(job_dict, indent=2)

    def recreate(self,folderPath):
        #Recreate the job from a given folder path
        import os, json, re
        self.batchFolder = folderPath
        self.batchUUID = os.path.basename(folderPath)

        # Try to load a metadata file first
        meta_file = os.path.join(self.batchFolder, "job_metadata.json")
        self.cases = []
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                self.projectID = meta.get('projectID')
                self.revID = meta.get('revID')
                self.batchUUID = meta.get('batchUUID', self.batchUUID)
                # restore metadata fields if present
                self.dateCreated = meta.get('dateCreated', None)
                self.apiVersion = meta.get('apiVersion', API_VERSION)
                cases_meta = meta.get('cases', [])
                for c in cases_meta:
                    case_num = c.get('caseNumber')
                    case_data = c.get('case_data', {})
                    case_instance = CaseClass(self.batchUUID, case_num, case_data,
                                             ActionClass=self.ActionClass,
                                             ResultsClasses=self.ResultsClasses)
                    case_instance.job = self
                    # restore status if present
                    if 'caseStatus' in c:
                        case_instance.caseStatus = c.get('caseStatus')
                    self.cases.append(case_instance)
                return
            except Exception:
                # fall back to scanning files
                pass

        # Fallback: scan for case_*.json files and rebuild
        try:
            files = os.listdir(self.batchFolder)
        except Exception:
            files = []
        case_files = []
        for fn in files:
            m = re.match(r'case_(\d+)\.json$', fn)
            if m:
                case_files.append((int(m.group(1)), fn))
        case_files.sort()
        for case_num, fn in case_files:
            try:
                with open(os.path.join(self.batchFolder, fn), 'r') as f:
                    case_data = json.load(f)
            except Exception:
                case_data = {}
            case_instance = CaseClass(self.batchUUID, case_num, case_data,
                                     ActionClass=self.ActionClass,
                                     ResultsClasses=self.ResultsClasses)
            case_instance.job = self
            self.cases.append(case_instance)
    def saveToFolder(self):
        import os, json
        if self.batchFolder is None:
            if not getattr(self, 'batchUUID', None):
                self.batchUUID = generateBatchUUID()
            self.batchFolder = generateBatchFolder(self.batchUUID)
        else:
            os.makedirs(self.batchFolder, exist_ok=True)

        # write a status file
        status_file = os.path.join(self.batchFolder, "job_status.txt")
        if not os.path.exists(status_file):
            with open(status_file, "w") as f:
                f.write("Job Created\n")

        # write metadata json for easy recreation (includes caseStatus)
        self._write_metadata()

        # also write individual case files for convenience
        for c in self.cases:
            case_num = getattr(c, 'caseNumber', None)
            case_data = getattr(c, 'case_data', {})
            if case_num is None:
                continue
            case_file = os.path.join(self.batchFolder, f'case_{case_num}.json')
            with open(case_file, 'w') as f:
                json.dump(case_data, f, indent=2)

    def _write_metadata(self):
        import os, json
        if self.batchFolder is None:
            if not getattr(self, 'batchUUID', None):
                self.batchUUID = generateBatchUUID()
            self.batchFolder = generateBatchFolder(self.batchUUID)
        os.makedirs(self.batchFolder, exist_ok=True)
        meta = {
            'projectID': self.projectID,
            'revID': self.revID,
            'batchUUID': self.batchUUID,
            'dateCreated': self.dateCreated,
            'apiVersion': self.apiVersion,
            'cases': []
        }
        for c in self.cases:
            meta['cases'].append({
                'caseNumber': getattr(c, 'caseNumber', None),
                'caseStatus': getattr(c, 'caseStatus', None),
                'case_data': getattr(c, 'case_data', {})
            })

        meta_file = os.path.join(self.batchFolder, 'job_metadata.json')
        with open(meta_file, 'w') as f:
            json.dump(meta, f, indent=2)
    def create(self, projectID, revID, case_data):
        self.projectID = projectID
        self.revID = revID
        self.batchUUID = generateBatchUUID()
        self.cases = []
        self.batchFolder = generateBatchFolder(self.batchUUID)
        # record creation timestamp and API version
        self.dateCreated = datetime.datetime.utcnow().isoformat() + 'Z'
        self.apiVersion = API_VERSION
        for caseNum, case in enumerate(case_data):
            case_instance = CaseClass(self.batchUUID, caseNum, case, 
                                     ActionClass=self.ActionClass, 
                                     ResultsClasses=self.ResultsClasses)
            case_instance.job = self
            self.cases.append(case_instance)
        self._write_metadata()
    def get_cases(self):
        return self.cases
    
    def isCompleted(self):
        for case in self.cases:
            if not case.isCompleted():
                return False
        return True
    
    def get_job_schema(self):
        """Return JSON schema for job creation endpoint"""
        # Get case schema from ActionClass if available
        case_schema = {"type": "object"}
        if self.ActionClass and hasattr(self.ActionClass, 'mySchema'):
            try:
                # Try calling as class method first
                if callable(getattr(self.ActionClass, 'mySchema', None)):
                    # Create temporary instance without validation
                    temp_action = object.__new__(self.ActionClass)
                    case_schema = temp_action.mySchema()
            except:
                case_schema = {"type": "object"}
        # If the action schema defines a 'Lengths' property as an array,
        # mark it with a custom type name so callers can recognise it as
        # a 2D segment array (pairs of points) rather than a generic array.
        try:
            props = case_schema.get('properties', {}) if isinstance(case_schema, dict) else {}
            if 'Lengths' in props and isinstance(props['Lengths'], dict):
                # Keep the schema validation intact (ensure it's still an array)
                props['Lengths'].setdefault('type', 'array')
                # Non-invasive markers for clients to recognise the special array shape
                props['Lengths']['format'] = '2d-segment-array'
                props['Lengths']['x-2dSegmentArray'] = True
                props['Lengths'].setdefault('description', '2D segment array: list of segments, each segment is a pair of points [[x1,y1],[x2,y2]]')
        except Exception:
            # best-effort only; leave case_schema unchanged on error
            pass
        
        return {
            "type": "object",
            "properties": {
                "projectID": {"type": "string", "description": "Project identifier"},
                "revID": {"type": "string", "description": "Revision identifier"},
                "cases": {
                    "type": "array",
                    "items": case_schema,
                    "description": "Array of case data objects"
                }
            },
            "required": ["cases"]
        }
class CaseClass:
    #Case Data will be a dictionary containing all relevant information for the case to be handled.
    def __init__(self, batchUUID, caseNum, case_data, ActionClass=None, ResultsClasses=None):
        self.batchUUID = batchUUID
        self.caseNumber = caseNum
        self.caseStatus = "Not Started"
        self.case_data = case_data
        self.resultsFolder = generateResultsFolder(batchUUID,caseNum)
        # Store the configured classes (fall back to base classes if not provided)
        self.ActionClass = ActionClass if ActionClass is not None else ActionBase
        self.ResultsClasses = ResultsClasses if ResultsClasses is not None else [ResultsBase]


    def startCase(self):
        self.caseStatus = "Queued"
        # persist status change to job metadata if available
        try:
            if hasattr(self, 'job') and self.job is not None:
                self.job._write_metadata()
        except Exception:
            pass
    
    def runCase(self):
        import os, json

        # mark run time for this case
        try:
            if not isinstance(self.case_data, dict):
                self.case_data = {}
        except Exception:
            self.case_data = {}
        self.case_data['dateRun'] = datetime.datetime.utcnow().isoformat() + 'Z'
        self.caseStatus = "Running"
        # persist status change to job metadata if available
        try:
            if hasattr(self, 'job') and self.job is not None:
                self.job._write_metadata()
        except Exception:
            pass

        def _on_complete(result, error):
            if error:
                self.caseStatus = "Failed"
                out = {"error": str(error)}
            else:
                self.caseStatus = "Completed"
                # if result is None, produce a minimal success payload
                out = result if result is not None else {"status": "completed"}

            try:
                os.makedirs(self.resultsFolder, exist_ok=True)
                with open(os.path.join(self.resultsFolder, 'results.json'), 'w') as f:
                    json.dump(out, f, indent=2)
            except Exception:
                # ignore file-write errors but keep status updated
                pass
            # persist status change to job metadata if available
            try:
                if hasattr(self, 'job') and self.job is not None:
                    self.job._write_metadata()
            except Exception:
                pass

        action = self.ActionClass(self.case_data, on_complete=_on_complete, case=self)
        return action.perform_action_async()
        
    def completeCase(self):
        self.caseStatus = "Completed"
        try:
            if hasattr(self, 'job') and self.job is not None:
                self.job._write_metadata()
        except Exception:
            pass
    def isCompleted(self):
        return self.caseStatus == "Completed"
    def getResults(self):
        # Use the first configured ResultsClass (or ResultsBase as fallback)
        results = {}
        for ResultsClass in self.ResultsClasses:
            try:
                results[ResultsClass.__name__] = ResultsClass(self.resultsFolder).process_results()
            except Exception as e:
                results[ResultsClass.__name__] = {"error": str(e)}
        return results
    def get_status(self):
        return self.caseStatus


def UUIDExists(batchUUID):
    import os
    folder_path = f"results/{batchUUID}"
    return os.path.exists(folder_path)
def generateBatchUUID():
    import uuid
    batchUUID = str(uuid.uuid4())
    while UUIDExists(batchUUID):
        batchUUID = str(uuid.uuid4())
    return batchUUID
def generateBatchFolder(batchUUID):
    import os
    folder_path = f"results/{batchUUID}"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path
def generateResultsFolder(batchUUID, caseNum):
    import os
    folder_path = f"results/{batchUUID}/case_{caseNum}"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path
def getAllJobs(actionClass, ResultsClasses):
    import os
    base_path = "results"
    if not os.path.exists(base_path):
        return []
    jobs = []
    for entry in os.listdir(base_path):
        job_path = os.path.join(base_path, entry)
        if os.path.isdir(job_path):
            job_instance = jobClass(actionClass, ResultsClasses)
            job_instance.recreate(job_path)
            jobs.append(job_instance)
    return jobs
def getAllCases(batchUUID):
    import os, re
    folder_path = f"results/{batchUUID}"
    if not os.path.exists(folder_path):
        return []
    case_nums = []
    for name in os.listdir(folder_path):
        m = re.match(r'case_(\d+)$', name)
        if m and os.path.isdir(os.path.join(folder_path, name)):
            case_nums.append(int(m.group(1)))
    case_nums.sort()
    return case_nums


class DownloadableClass:
    """
    Base class for downloading case(s) in a format suitable for local execution.
    
    Handles automatic loading of job metadata and provides methods for single or multiple case downloads.
    Forkers should subclass this and implement generateDownloadable() and/or generateDownloadableMultiple().
    """
    def __init__(self, job_uuid, case_numbers=None, ActionClass=None, ResultsClasses=None):
        """
        Initialize the Downloadable instance.
        
        Args:
            job_uuid: The UUID of the job to download
            case_numbers: Optional list of case numbers to download. If None, all cases are available.
            ActionClass: The Action class for this API (optional, for job recreation)
            ResultsClasses: The Results classes for this API (optional, for job recreation)
        """
        self.job_uuid = job_uuid
        self.job_folder = generateBatchFolder(job_uuid)
        
        # Load job metadata
        self.job_metadata = self._load_job_metadata()
        
        # Recreate job instance for accessing case data
        self.job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
        self.job_instance.recreate(self.job_folder)
        
        # Filter cases if specific case numbers are requested
        if case_numbers is not None:
            self.cases = [case for case in self.job_instance.get_cases() 
                         if case.caseNumber in case_numbers]
        else:
            self.cases = self.job_instance.get_cases()
    
    def _load_job_metadata(self):
        """Load the job_metadata.json file for this job."""
        metadata_path = os.path.join(self.job_folder, "job_metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Job metadata not found at {metadata_path}")
        with open(metadata_path, 'r') as f:
            return json.load(f)
    
    def get_case_by_number(self, case_number):
        """Get a specific case by its number."""
        for case in self.cases:
            if case.caseNumber == case_number:
                return case
        raise ValueError(f"Case {case_number} not found in selected cases")
    
    def get_all_cases(self):
        """Get all selected cases."""
        return self.cases
    
    def generateDownloadable(self, case_number):
        """
        Generate a downloadable file/package for a single case.
        
        Args:
            case_number: The case number to generate downloadable for
            
        Returns:
            A dictionary with download information (e.g., {'filename': 'case.zip', 'data': bytes})
            or a file path, depending on implementation needs.
        """
        raise NotImplementedError("Subclasses should implement this method.")
    
    def generateDownloadableMultiple(self, case_numbers=None):
        """
        Generate a downloadable file/package for multiple cases.
        
        Args:
            case_numbers: Optional list of case numbers. If None, uses all selected cases.
            
        Returns:
            A dictionary with download information (e.g., {'filename': 'cases.zip', 'data': bytes})
            or a file path, depending on implementation needs.
        """
        raise NotImplementedError("Subclasses should implement this method.")

AllUnits = []
class Unit():
    def __init__(self, unitString):
        self.unitString = unitString
        self.alternateStrings = []
        self.ConvertibleUnits = []
        AllUnits.append(self)
    
    def addAlternateString(self, altString):
        # Override this method to add alternate string representations
        self.alternateStrings.append(altString)
    def defineConversion(self, targetUnit,function):
        # Override this method to define conversion functions
        self.ConvertibleUnits.append((targetUnit, function))
    def convertTo(self, targetUnit, value):
        # Override this method to define conversion logic
        for unit, func in self.ConvertibleUnits:
            if unit == targetUnit:
                return func(value)
        raise ValueError(f"Conversion to {targetUnit} not defined.")
    def convertibleTo(self,otherUnit):
        for unit, func in self.ConvertibleUnits:
            if unit == otherUnit:
                return True
        return False
    def __str__(self):
        return self.unitString

class meter(Unit):
    def __init__(self):
        super().__init__("meter")
        self.addAlternateString("m")
        self.defineConversion("centimeter", lambda x: x * 100)
        self.defineConversion("kilometer", lambda x: x / 1000)
        self.defineConversion("inch", lambda x: x * 39.3701)
        self.defineConversion("foot", lambda x: x * 3.28084)
class centimeter(Unit):
    def __init__(self):
        super().__init__("centimeter")
        self.addAlternateString("cm")
        self.defineConversion("meter", lambda x: x / 100)
        self.defineConversion("kilometer", lambda x: x / 100000)
        self.defineConversion("inch", lambda x: x * 0.393701)
        self.defineConversion("foot", lambda x: x * 0.0328084)
class kilometer(Unit):
    def __init__(self):
        super().__init__("kilometer")
        self.addAlternateString("km")
        self.defineConversion("meter", lambda x: x * 1000)
        self.defineConversion("centimeter", lambda x: x * 100000)
        self.defineConversion("inch", lambda x: x * 39370.1)
        self.defineConversion("foot", lambda x: x * 3280.84)
class inch(Unit):
    def __init__(self):
        super().__init__("inch")
        self.addAlternateString("in")
        self.defineConversion("meter", lambda x: x / 39.3701)
        self.defineConversion("centimeter", lambda x: x / 0.393701)
        self.defineConversion("kilometer", lambda x: x / 39370.1)
        self.defineConversion("foot", lambda x: x / 12)
class foot(Unit):
    def __init__(self):
        super().__init__("foot")
        self.addAlternateString("ft")
        self.defineConversion("meter", lambda x: x / 3.28084)
        self.defineConversion("centimeter", lambda x: x / 0.0328084)
        self.defineConversion("kilometer", lambda x: x / 3280.84)
        self.defineConversion("inch", lambda x: x * 12)