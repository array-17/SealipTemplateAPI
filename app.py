from flask import Flask, jsonify, request
from jsonschema import validate, ValidationError
import threading
from adapters import UUIDExists, jobClass
from JobRunner import JobRunner
from fork_config import (
    API_META,
    ACTION_CLASS,
    RESULTS_CLASSES,
    TEMPLATE_CLASSES,
    DOWNLOADABLE_CLASS,
    validate_fork_config,
)

app = Flask(__name__)

#startup code here

##

validate_fork_config()

ActionClass = ACTION_CLASS
ResultsClasses = RESULTS_CLASSES
TemplateClasses = TEMPLATE_CLASSES



#Start the Job Runner
job_runner = JobRunner(ActionClass, ResultsClasses)
job_runner_thread = threading.Thread(target=job_runner.run_loop, daemon=True)
job_runner_thread.start()

@app.route('/', methods=['GET'])
def index():
    #return static/tester.html
    return app.send_static_file('tester.html')

@app.route('/NautAPI', methods=['GET'])
def get_api_meta():
    #Returns the API metadata, this tells the program that the API exists on the given endpoint
    return jsonify(API_META)

@app.route('/Jobs/schema', methods=['GET'])
def get_job_schema():
    #Returns the JSON schema for job creation
    job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
    class_schema = job_instance.get_job_schema()

    return jsonify(class_schema)

@app.route('/Jobs/create', methods=['POST'])
def create_job():
    job_parameters = request.get_json()
    # Validate job_parameters against a predefined schema
    project_id = job_parameters.get('projectID', '1')
    rev_id = job_parameters.get('revID', '1')
    cases = job_parameters.get('cases', [])
    job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
    job_instance.create(project_id, rev_id, cases)
    return jsonify({"batchUUID": job_instance.batchUUID})

@app.route('/Jobs/<batchUUID>/cases', methods=['GET'])
def get_job_cases(batchUUID):
    if not UUIDExists(batchUUID):
        return jsonify({"error": "Batch UUID does not exist"}), 404
    job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
    job_instance.recreate(f"results/{batchUUID}")
    case_list = []
    for case in job_instance.get_cases():
        case_list.append({
            "caseNumber": case.caseNumber,
            "status": case.get_status()
        })
    return jsonify({"cases": case_list})

@app.route('/Jobs/<batchUUID>', methods=['GET'])
def getAllJobs():
    import os
    jobs_folder = "results"
    all_jobs = []
    for entry in os.listdir(jobs_folder):
        job_path = os.path.join(jobs_folder, entry)
        if os.path.isdir(job_path):
            job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
            job_instance.recreate(job_path)
            all_jobs.append(job_instance)
    return all_jobs

#GetJobsByProjectID
@app.route('/Jobs/project/<ProjectID>', methods=['GET'])
def getAllJobsByProjectID(ProjectID):
    import os
    jobs_folder = "results"
    all_jobs = []
    for entry in os.listdir(jobs_folder):
        job_path = os.path.join(jobs_folder, entry)
        if os.path.isdir(job_path):
            job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
            job_instance.recreate(job_path)
            if job_instance.projectID == ProjectID:
                all_jobs.append(job_instance.asJson())
    return all_jobs
#getjobsbyrevid
@app.route('/Jobs/rev/<rev_id>', methods=['GET'])
def getAllJobsByRevID(rev_id):
    import os
    jobs_folder = "results"
    all_jobs = []
    for entry in os.listdir(jobs_folder):
        job_path = os.path.join(jobs_folder, entry)
        if os.path.isdir(job_path):
            job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
            job_instance.recreate(job_path)
            if job_instance.revID == rev_id:
                all_jobs.append(job_instance.asJson())
    return all_jobs


@app.route('/Jobs/<batchUUID>/start', methods=['POST'])
def start_job(batchUUID):
    if not UUIDExists(batchUUID):
        return jsonify({"error": "Batch UUID does not exist"}), 404
    job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
    job_instance.recreate(f"results/{batchUUID}")
    for case in job_instance.get_cases():
        case.startCase()
    return jsonify({"status": "Job started"})

@app.route('/Jobs/<batchUUID>/status', methods=['GET'])
def job_status(batchUUID):
    if not UUIDExists(batchUUID):
        return jsonify({"error": "Batch UUID does not exist"}), 404
    job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
    job_instance.recreate(f"results/{batchUUID}")
    status_list = []
    for case in job_instance.get_cases():
        status_list.append({
            "caseNumber": case.caseNumber,
            "status": case.get_status()
        })
    return jsonify({"cases": status_list})

@app.route('/Jobs/<batchUUID>/results', methods=['GET'])
def job_results(batchUUID):
    if not UUIDExists(batchUUID):
        return jsonify({"error": "Batch UUID does not exist"}), 404
    job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
    job_instance.recreate(f"results/{batchUUID}")
    results_list = []
    for case in job_instance.get_cases():
        try:
            case_results = case.getResults()
        except Exception as e:
            case_results = {"error": str(e)}
        results_list.append({
            "caseNumber": case.caseNumber,
            "results": case_results
        })
    return jsonify({"cases": results_list})


@app.route('/results/types', methods=['GET'])
def get_result_types():
    return jsonify([result_class.__name__ for result_class in ResultsClasses])

@app.route('/Jobs/<batchUUID>/cases/<int:caseNumber>/results/<resultType>', methods=['GET'])
def case_result(batchUUID, caseNumber, resultType):
    if not UUIDExists(batchUUID):
        return jsonify({"error": "Batch UUID does not exist"}), 404
    job_instance = jobClass(ActionClass=ActionClass, ResultsClasses=ResultsClasses)
    job_instance.recreate(f"results/{batchUUID}")
    case_instance = None
    for case in job_instance.get_cases():
        if case.caseNumber == caseNumber:
            case_instance = case
            break
    if case_instance is None:
        return jsonify({"error": "Case number does not exist"}), 404
    result_instance = None
    for result_class in ResultsClasses:
        if result_class.__name__ == resultType:
            result_instance = result_class(case_instance.resultsFolder)
            break
    if result_instance is None:
        return jsonify({"error": "Result type does not exist"}), 404
    try:
        processed_results = result_instance.process_results()
        return processed_results
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/Templates', methods=['GET'])
def get_templates():
    # Return the templates for the frontend to render input forms, this is based on the Template classes defined in Templates.py
    templates = []
    for template_class in TemplateClasses:
        template_instance = template_class()
        if hasattr(template_instance, 'toFrontend_parameters') and callable(getattr(template_instance, 'toFrontend_parameters')):
            templates.append(template_instance.toFrontend_parameters())
        elif hasattr(template_instance, 'to_frontend_parameters') and callable(getattr(template_instance, 'to_frontend_parameters')):
            templates.append(template_instance.to_frontend_parameters())
        elif hasattr(template_instance, 'template') and hasattr(template_instance.template, 'to_frontend_parameters') and callable(getattr(template_instance.template, 'to_frontend_parameters')):
            templates.append(template_instance.template.to_frontend_parameters())
        else:
            raise Exception(f"Template class {template_class.__name__} does not expose a frontend serialization method")
    return jsonify({"templates": templates})

@app.route('/Jobs/<string:jobUUID>/download', methods=['GET'])
def download_job(jobUUID):
    """
    Download one or more cases from a job in various formats.
    Query params:
        - cases: comma-separated list of case numbers (optional, defaults to all cases)
        - format: file format (optional, defaults to 'json'). Options: 'json', 'csv', etc.
    """
    from flask import send_file, Response
    import io
    import mimetypes
    
    # Check if job exists
    if not UUIDExists(jobUUID):
        return jsonify({"error": "Job UUID does not exist"}), 404
    
    # Get requested case numbers
    cases_param = request.args.get('cases', None)
    case_numbers = None
    if cases_param:
        try:
            case_numbers = [int(c.strip()) for c in cases_param.split(',')]
        except ValueError:
            return jsonify({"error": "Invalid case numbers format"}), 400
    
    # Get requested format
    file_format = request.args.get('format', 'json').lower()
    
    try:
        # Create downloadable instance (job metadata is automatically loaded)
        downloadable = DOWNLOADABLE_CLASS(jobUUID, case_numbers=case_numbers, 
                          ActionClass=ActionClass, 
                          ResultsClasses=ResultsClasses)
        
        # Generate download based on number of cases and format
        if case_numbers and len(case_numbers) == 1:
            # Single case download
            result = downloadable.generateDownloadable(case_numbers[0], file_format=file_format)
        else:
            # Multiple cases download
            result = downloadable.generateDownloadableMultiple(case_numbers, file_format=file_format)
        
        # Extract file data, filename, and mimetype
        file_data = result['data']
        filename = result['filename']
        mimetype = result.get('mimetype', None)
        
        # Auto-detect mimetype from filename if not provided
        if mimetype is None:
            mimetype, _ = mimetypes.guess_type(filename)
            if mimetype is None:
                mimetype = 'application/octet-stream'
        
        # Handle binary data (bytes) vs text data (str)
        if isinstance(file_data, bytes):
            response_data = file_data
        else:
            response_data = str(file_data).encode('utf-8')
        
        return Response(
            response_data,
            mimetype=mimetype,
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

if __name__ == '__main__':
    import os
    import threading
    import base64, mimetypes
    port = int(os.environ.get('PORT', 5006))
    app.run(host='0.0.0.0', port=port)
