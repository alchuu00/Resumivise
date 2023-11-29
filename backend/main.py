import os
import json
from utils.docReader import read_docx, write_docx
from utils.pdfReader import read_pdf
from api.gptApi import GptApi
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Allow all origins in development. Adjust as needed for production.
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singeltont Pattern
class GptClientWrapper:
    def __init__(self):
        self.gpt_client = GptApi()

    def get_instance(self):
        return self.gpt_client

gpt_client_wrapper = GptClientWrapper()

def get_gpt_client():
    return gpt_client_wrapper.get_instance()

def reading_data(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.pdf':
        data = json.loads(read_pdf(file_path))
    elif file_extension == '.docx':
        data = json.loads(read_docx(file_path))
    else:
        raise HTTPException(status_code=400, detail='File type not supported')
    return data

def name_generator(filename,client_id):
    return f"{filename}_{client_id}"


def process_upload_resume(filename, file_content, client_id):
    print("UPLOAD")
    print(filename)
    file_extension = filename.split('.')[1].lower()
    if file_extension in ['docx', 'pdf']:
        filen_name = name_generator('uploaded_resume',client_id)
        with open(f"./static/resume/{filen_name}.{file_extension}", 'wb') as f:
            f.write(file_content.read())
        data = reading_data(f"./static/resume/{filen_name}.{file_extension}")
        gptClient = get_gpt_client()
        extracted_resume_data = gptClient.extract_info_from_resume(data['text'])

        print("EXTRACTING is finished")
        
        try:
            extracted_resume_data = json.loads(extracted_resume_data)

            # Write JSON data to a text file
            extracted_resume_filename = name_generator('extracted_resume',client_id)
            with open(f"./static/resume/{extracted_resume_filename}.json", 'w') as file:
                json.dump(extracted_resume_data, file)

            print('JSON data has been successfully written to extracted_resume.json.')

        except json.JSONDecodeError as e:
            return f'Error decoding JSON: {e}'
        except Exception as e:
            return f'Error: {e}'
        
        os.remove(f"./static/resume/{filen_name}.{file_extension}")
        return 'successfully uploaded'
    else:
        return 'Failed to upload'
    
def process_upload_job_description(job_description_data, client_id):
    try:
        job_description_filename = name_generator('job_description',client_id)
        with open(f"./static/resume/{job_description_filename}.txt", 'w') as file:
                file.write(job_description_data)
        return "Job description received successfully"
    except Exception as e:
        return f'Error: {e}'


def process_compare(client_id):
    print("COMPARE")
    gptClient = get_gpt_client()
    extracted_resume_filename = name_generator('extracted_resume',client_id)
    job_description_filename = name_generator('job_description',client_id)
    with open(f"./static/resume/{extracted_resume_filename}.json") as file:
        extracted_resume_data = file.read()

    try: 
        with open(f"./static/resume/{job_description_filename}.txt") as file:
                job_description_data = file.read()
    except FileNotFoundError:
        job_description_data = ''

    return gptClient.compare_resume_with_job_description(
        extracted_resume_data, 
        job_description_data
        )

def process_revise(client_id):
    print("REVISE")
    gptClient = get_gpt_client()
    extracted_resume_filename = name_generator('extracted_resume',client_id)
    job_description_filename = name_generator('job_description',client_id)
    with open(f"./static/resume/{extracted_resume_filename}.json") as file:
        extracted_resume_data = file.read()

    try: 
        with open(f"./static/resume/{job_description_filename}.txt") as file:
                job_description_data = file.read()
    except FileNotFoundError:
        job_description_data = ''

    return gptClient.align_resume_info_with_job_description(
        extracted_resume_data, 
        job_description_data
        )

@app.post("/upload_resume")
def upload_resume(resume: UploadFile = File(...), client_id: str = Form(...)):
    try:
        result = process_upload_resume(resume.filename, resume.file, client_id)
        return json.dumps({'text': result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@app.post("/upload_job_description")
def upload_job_description(data: dict):
    client_id=data.get('client_id', '')
    job_description = data['text']
    result = process_upload_job_description(job_description, client_id)
    return {"message": result}

@app.get("/compare_resume")
def compare_resume(client_id: str = Query(...)):
    print(client_id)
    compared_data_stream = process_compare(client_id)

    # return StreamingResponse(compared_data_stream,
    #                            media_type='text/event-stream') # This for Streaming
    return json.dumps(compared_data_stream)


@app.get("/revise_resume")
def revise_resume(client_id: str = Query(...)):
    print(client_id)
    tailored_resume_data_stream = process_revise(client_id)
    
    # return StreamingResponse(tailored_resume_data_stream,
    #                            media_type='text/event-stream') # This for Streaming
    return json.dumps(tailored_resume_data_stream)


if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8000, workers=4)