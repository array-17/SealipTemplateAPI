from adapters import ActionBase as BaseAction, DownloadableClass, ResultsBase as BaseResults
from typing import Dict, Any, Optional
try:
    from .Templates import Template, define_template
except ImportError:
    from Templates import Template, define_template
import os
import json

class AddAction(BaseAction):
    """
    Action to add two numbers.
    """

    def __init__(self, action_data, on_complete=None, case=None):
        action_data = super().correctActionData(action_data)
        required = ["a", "b"]
        for key in required:
            if key not in action_data:
                raise ValueError(f"Missing required field '{key}' in action_data")
            if not isinstance(action_data[key], (int, float)):
                raise ValueError(f"Field '{key}' must be a number")
        self.a = action_data["a"]
        self.b = action_data["b"]
        super().__init__(action_data,on_complete,case)


    def perform_action(self) -> float:
        # Perform the addition
        #print result to results folder
        result_data = {"sum": self.a + self.b, "action_data": {"a": self.a, "b": self.b}}
        return result_data
    
    def mySchema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "title": "First number","units":"m"},
                "b": {"type": "number", "title": "Second number","units":"m"},
                "c": {"type": "number", "title": "Unused number","units":"m","x-KVPTable":True}
            },
            "required": ["a", "b"]
        }


class AddResults(BaseResults):
    """
    Results class to store the sum of two numbers.
    """

    def __init__(self, resultsFolder: str):
        super().__init__(resultsFolder)
        self.sum: Optional[float] = None

    def process_results(self) -> Dict[str, Any]:
        print("ResultsFolder =" + self.resultsFolder)
        data = self.getData()
        self.sum = data.get("sum")
        return {"sum": self.sum}
    
class GraphResults(BaseResults):
    """
    Results class to store a graphical representation of the addition.
    """

    def __init__(self, resultsFolder: str):
        super().__init__(resultsFolder)
        self.a: Optional[float] = None
        self.b: Optional[float] = None
        self.sum: Optional[float] = None

    def process_results(self) -> Dict[str, Any]:
        data = self.getData()
        self.a = data.get("action_data", {}).get("a")
        self.b = data.get("action_data", {}).get("b")
        self.sum = data.get("sum")
        graphJson={
            "type": "bar",
            "data": {
                "labels": ["a", "b", "sum"],
                "datasets": [{
                    "label": "Addition Result",
                    "data": [self.a, self.b, data.get("sum")],
                    "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56"]
                }]
            },
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True
                    }
                }
            }   
        }
        print("GraphJson =" + json.dumps(graphJson))
        
        return {"graph": graphJson}
    
class AddDownloadable(DownloadableClass):
    """
    Example implementation of DownloadableClass for the Add API.
    Generates downloadable files for cases in various formats.
    """
    
    def generateDownloadable(self, case_number, file_format='json'):
        """
        Generate a downloadable file for a single case.
        The job metadata is already loaded in self.job_metadata.
        
        Args:
            case_number: The case number to download
            file_format: Format of the file ('json', 'csv', etc.)
        """
        case = self.get_case_by_number(case_number)
        
        if file_format == 'json':
            import json
            downloadable_data = {**case.case_data}
            return {
                'filename': f'add_case_{case_number}.json',
                'data': json.dumps(downloadable_data, indent=2),
                'mimetype': 'application/json'
            }
        
        elif file_format == 'csv':
            import csv, io
            output = io.StringIO()
            
            # Extract keys and values from case_data
            rows = []
            for key, value_dict in case.case_data.items():
                value = value_dict.get('value', '')
                units = value_dict.get('units', '')
                rows.append({
                    'parameter': key,
                    'value': value,
                    'units': units
                })
            
            if rows:
                writer = csv.DictWriter(output, fieldnames=['parameter', 'value', 'units'])
                writer.writeheader()
                writer.writerows(rows)
            
            return {
                'filename': f'add_case_{case_number}.csv',
                'data': output.getvalue(),
                'mimetype': 'text/csv'
            }
        
        else:
            raise ValueError(f"Unsupported format: {file_format}")
    
    def generateDownloadableMultiple(self, case_numbers=None, file_format='json'):
        """
        Generate a downloadable file containing multiple cases.
        If case_numbers is None, downloads all selected cases.
        
        Args:
            case_numbers: List of case numbers to download (None for all)
            file_format: Format of the file ('json', 'csv', etc.)
        """
        cases_to_download = self.cases if case_numbers is None else [
            self.get_case_by_number(num) for num in case_numbers
        ]
        
        if file_format == 'json':
            import json
            downloadable_data = {'cases': []}
            for case in cases_to_download:
                downloadable_data['cases'].append({**case.case_data})
            
            return {
                'filename': f'add_job_{self.job_uuid}_cases.json',
                'data': json.dumps(downloadable_data, indent=2),
                'mimetype': 'application/json'
            }
        
        elif file_format == 'csv':
            import csv, io
            output = io.StringIO()
            
            # Collect all unique parameters across all cases
            all_params = set()
            for case in cases_to_download:
                all_params.update(case.case_data.keys())
            all_params = sorted(all_params)
            
            # Create CSV with case_number column + all parameters
            fieldnames = ['case_number'] + all_params
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for case in cases_to_download:
                row = {'case_number': case.caseNumber}
                for param in all_params:
                    if param in case.case_data:
                        value = case.case_data[param].get('value', '')
                        units = case.case_data[param].get('units', '')
                        # Combine value and units for CSV
                        row[param] = f"{value} {units}".strip()
                    else:
                        row[param] = ''
                writer.writerow(row)
            
            return {
                'filename': f'add_job_{self.job_uuid}_cases.csv',
                'data': output.getvalue(),
                'mimetype': 'text/csv'
            }
        
        else:
            raise ValueError(f"Unsupported format: {file_format}")
        


class SNTemplate(Template):
    """
    Template class to define the structure of the Master input S-N curve parameters.
    """

    def __init__(self):
        self.template = define_template( name="S-N Data",
    description="Template for defining S-N Data",
    node_definitions=[
        {
            "type": "group",
            "name": "Material",  # top-level group
            "children": [
                {
                    "type": "group",
                    "name": "Material Template",
                    "children": [
                        {"type": "parameter", "name": "m1", "parameter_type": "number", "units": "-"},
                        {"type": "parameter", "name": "Loga1", "parameter_type": "number", "units": "-"},
                        {"type": "parameter", "name": "InflectionPoint", "parameter_type": "number", "units": "MPa"},
                        {"type": "parameter", "name": "m2", "parameter_type": "number", "units": "-"},
                        {"type": "parameter", "name": "Loga2", "parameter_type": "number", "units": "-"}
                    ]
                }
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()

class CableTemplate(Template):
    """
    Template class to define the structure of the Master input cableparameters.
    """

    def __init__(self):
        self.template = define_template( name="Cable Template",
    description="Template for defining cable parameters with groups",
    node_definitions=[
        {
            "type": "group",
            "name": "Cable",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Cable Outer Diameter", "parameter_type": "number", "units": "mm"},
            
                {"type": "parameter", "name": "Weight in Air", "parameter_type": "number", "units": "kg/m"},
                {"type": "parameter", "name": "Weight in Water", "parameter_type": "number", "units": "kg/m"},
                {"type": "parameter", "name": "Axial Stiffness", "parameter_type": "number", "units": "MN"},
                {"type": "parameter", "name": "Bending Stiffness", "parameter_type": "number", "units": "kNm2"},
                {"type": "parameter", "name": "Torsional Stiffness", "parameter_type": "number", "units": "kNm2"},
                {"type": "parameter", "name": "Max Allowable Tension", "parameter_type": "number", "units": "kN"},
                {"type": "parameter", "name": "Max Bend Radius", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Max Sidewall Pressure", "parameter_type": "number", "units": "kN/m"},
               {"type": "parameter", "name": "Sheath S-N Curve", "parameter_type": "string", "units": ""},
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()
    
class CPSTemplate(Template):
    """
    Template class to define the structure of the Master input cableparameters.
    """

    def __init__(self):
        self.template = define_template( name="CPS Template",
    description="Template for defining cable protection system parameters with groups",
    node_definitions=[
        {
            "type": "group",
            "name": "Cable Protection System",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {            "type": "group",
            "name": "Internal Stiffener",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Arc Length", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Inner Diameter", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Outer Diameter", "parameter_type": "number", "units": "m"},

            ]
            },
            {            "type": "group",
            "name": "Connector",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Arc Length", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Inner Diameter", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Outer Diameter", "parameter_type": "number", "units": "m"},

            ]
            },
            {            "type": "group",
            "name": "External Stiffener",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Arc Length", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Inner Diameter", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Outer Diameter", "parameter_type": "number", "units": "m"},

            ]
            },
            {            "type": "group",
            "name": "Clamp",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Arc Length", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Inner Diameter", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Outer Diameter", "parameter_type": "number", "units": "m"},

            ]
            },
            {            "type": "group",
            "name": "Stiffener Sleeve",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Arc Length", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Inner Diameter", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Outer Diameter", "parameter_type": "number", "units": "m"},

            ]
            },
            {
            "type": "group",
            "name": "ABR",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Arc Length", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Inner Diameter", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Outer Diameter", "parameter_type": "number", "units": "m"},

            ]
            },
            
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()
    

    




class StructuralTemplate(Template):
    """
    Template class to define the structure of the Master input cableparameters.
    """

    def __init__(self):
        self.template = define_template( name="Structural Template",
    description="Template for defining structural parameters with groups",
    node_definitions=[
        {
            "type": "group",
            "name": "Structural",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {            "type": "group",
            "name": "WTG",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "HHang-Off Height", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Exit Elevation Min", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Exit Elevation Max", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Exit Angle", "parameter_type": "number", "units": "deg"},
                {"type": "parameter", "name": "Monopile Radius", "parameter_type": "number", "units": "m"},

            ]
            },
            {            "type": "group",
            "name": "OSS",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "HHang-Off Height", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Exit Elevation Min", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Exit Elevation Max", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "Exit Angle", "parameter_type": "number", "units": "deg"},
                {"type": "parameter", "name": "J-tube Straight Length", "parameter_type": "number", "units": "m"},
                {"type": "parameter", "name": "J-tube Elbow Radius", "parameter_type": "number", "units": "m"}

            ]
            }
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()


class EnvironmentTemplate(Template):
    """
    Template class to define the structure of Environment input parameters.
    """

    def __init__(self):
        self.template = define_template(name="Environment Template",
    description="Template for defining environment parameters with groups",
    node_definitions=[
        {
            "type": "group",
            "name": "Environment",
            "children": [
                # Pulled from table: Wave Parameters
                {
                    "type": "group",
                    "name": "Wave Parameters",
                    "children": [
                        {"type": "parameter", "name": "Hmax (50yr)", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "THmax (50yr)", "parameter_type": "number", "units": "s"},
                        {"type": "parameter", "name": "Hmax (10yr)", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "THmax (10yr)", "parameter_type": "number", "units": "s"},
                        {"type": "parameter", "name": "Hmax (1yr)", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "THmax (1yr)", "parameter_type": "number", "units": "s"},
                    ]
                },
                # Pulled from table: Current Parameters
                {
                    "type": "group",
                    "name": "Current Parameters",
                    "children": [
                        {"type": "parameter", "name": "Surface Current (50yr)", "parameter_type": "number", "units": "m/s"},
                        {"type": "parameter", "name": "Surface Current (10yr)", "parameter_type": "number", "units": "m/s"},
                        {"type": "parameter", "name": "Surface Current (1yr) FLS", "parameter_type": "number", "units": "m/s"},
                    ]
                },
                # Pulled from table: Water Depth
                {
                    "type": "group",
                    "name": "Water Depth",
                    "children": [
                        {"type": "parameter", "name": "Shallowest", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Deepest", "parameter_type": "number", "units": "m"},
                    ]
                },
                # Pulled from table: Marine Growth
                {
                    "type": "group",
                    "name": "Marine Growth",
                    "children": [
                        {"type": "parameter", "name": "Marine Growth Thickness", "parameter_type": "number", "units": "mm"},
                        {"type": "parameter", "name": "Marine Growth Density", "parameter_type": "number", "units": "kg/m^3"},
                    ]
                },
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()


class ScourBurialTemplate(Template):
    """
    Template class to define the structure of Scour + Burial input parameters.
    """

    def __init__(self):
        self.template = define_template(name="Scour + Burial Template",
    description="Template for defining scour and burial parameters with groups",
    node_definitions=[
        {
            "type": "group",
            "name": "Scour + Burial",
            "children": [
                # Pulled from table: Scour Protection
                {
                    "type": "group",
                    "name": "Scour Protection",
                    "children": [
                        {"type": "parameter", "name": "Scour Protection Extent Top (Max)", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Scour Protection Extent Bottom (Max)", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Scour Protection Gradient", "parameter_type": "string", "units": "1:X"},
                        {"type": "parameter", "name": "Burial Start Extent", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Burial Gradient", "parameter_type": "string", "units": "1:X"},
                        {"type": "parameter", "name": "Burial Depth (Top of Cable)", "parameter_type": "number", "units": "m"},
                    ]
                },
                # Pulled from table: Scour Pit
                {
                    "type": "group",
                    "name": "Scour Pit",
                    "children": [
                        {"type": "parameter", "name": "Scour Pit Extent (Max)", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Scour Pit Gradient", "parameter_type": "string", "units": "1:X"},
                        {"type": "parameter", "name": "Burial Start Extent", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Burial Gradient", "parameter_type": "string", "units": "1:X"},
                        {"type": "parameter", "name": "Burial Depth (Top of Cable)", "parameter_type": "number", "units": "m"},
                    ]
                },
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()


class StabalizationTemplate(Template):
    """
    Template class to define the structure of Stabalization input parameters.
    """

    def __init__(self):
        self.template = define_template(name="Stabalization Template",
    description="Template for defining stabalization parameters with groups",
    node_definitions=[
        {
            "type": "group",
            "name": "Stabalization",
            "children": [
                # Pulled from table: Rock Berm Overview
                {
                    "type": "group",
                    "name": "Rock Berm Overview",
                    "children": [
                        {"type": "parameter", "name": "Berm Distance from Structural Exit to Full Depth of Cover", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Berm Width", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Berm Height Above Product", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Berm Slope", "parameter_type": "string", "units": "1:X"},
                        {"type": "parameter", "name": "Berm Extent", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Berm Rock Density", "parameter_type": "number", "units": "kg/m3"},
                    ]
                },
                # Pulled from table: Rock Bag Overview
                {
                    "type": "group",
                    "name": "Rock Bag Overview",
                    "children": [
                        {"type": "parameter", "name": "Bag Diameter", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Bag Height", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Bag Quantity", "parameter_type": "number", "units": "-"},
                        {"type": "parameter", "name": "Bag Weight", "parameter_type": "number", "units": "kg"},
                        {"type": "parameter", "name": "Bag Rock Density", "parameter_type": "number", "units": "kg/m3"},
                    ]
                },
                # Pulled from table: Mattress Overview
                {
                    "type": "group",
                    "name": "Mattress Overview",
                    "children": [
                        {"type": "parameter", "name": "Mattress Length", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Mattres Height", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "Mattress Quantity", "parameter_type": "number", "units": "-"},
                        {"type": "parameter", "name": "Mattress Weight", "parameter_type": "number", "units": "kg"},
                        {"type": "parameter", "name": "Mattress Density", "parameter_type": "number", "units": "kg/m3"},
                    ]
                },
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()
    

    