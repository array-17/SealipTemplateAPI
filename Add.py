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
        
class AddTemplate(Template):
    """
    Template class to define the structure of the Add API parameters.
    """

    def __init__(self):
        self.template = define_template( name="Cable Template",
    description="Template for defining cable parameters with groups",
    node_definitions=[
        {
            "type": "group",
            "name": "Cable_Add",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "Designation", "parameter_type": "string", "units": ""},

                # child group 1 with 2 parameters
                {
                    "type": "group",
                    "name": "Geometry",
                    "children": [
                        {"type": "parameter", "name": "outer_diameter", "parameter_type": "number", "units": "m"},
                        {"type": "parameter", "name": "wall_thickness", "parameter_type": "number", "units": "m"},
                    ],
                },

                # child group 2 with 2 parameters
                {
                    "type": "group",
                    "name": "Material",
                    "children": [
                        {"type": "parameter", "name": "youngs_modulus", "parameter_type": "number", "units": "Pa"},
                        {"type": "parameter", "name": "density", "parameter_type": "number", "units": "kg/m^3"},
                    ],
                },
            ],
        }
    ],)

    def to_frontend_parameters(self):
        return self.template.to_frontend_parameters()

    def toFrontend_parameters(self):
        return self.to_frontend_parameters()