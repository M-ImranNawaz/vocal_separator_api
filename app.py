"""_summary_
"""
import shutil
import os
import json
import logging
import audiofile

from fastapi import FastAPI,  Depends, File, UploadFile, HTTPException, Security
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security.api_key import APIKeyHeader

from starlette.status import HTTP_403_FORBIDDEN
from src.utils.get_models import download_all_models
from src import models

logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.DEBUG)

app = FastAPI()


# Define the API key name and value
API_KEY_NAME = "access_token"
API_KEY = "xSx+4YQ5PkrWjcMu+KQEO8chSzD/vt6eYMaJCz8SyRA="

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Dependency for API key validation
async def get_api_key(api_key: str = Security(api_key_header)):
    """_summary_

    Args:
        api_key (str, optional): _description_. Defaults to Security(api_key_header).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    # logger.debug(f"{api_key}  ==  {API_KEY}       result = {api_key == API_KEY}")
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )


# Load model configuration
models_json = json.load(open("src/models_dir/models.json", "r", encoding= "utf-8"))
logger.debug('model loaded')

# Download all models (if not already downloaded)
download_all_models(models_json)
logger.debug('downloaded')

# Initialize the model
DEVICE = "cpu"
META = {"segment": 2, "split": True}
DEMUCS = models.Demucs(name="hdemucs_mmi", other_metadata=META, device=DEVICE, logger=None)
logger.debug('initialized ')

# separate a song into 4 stems
@app.post("/separate")
async def separate(file: UploadFile = File(...), stems: int = 2,
                    user_id = None, api_key: str = Depends(get_api_key)):
    """_summary_

    Args:
        file (UploadFile, optional): _description_. Defaults to File(...).
        stems (int, optional): _description_. Defaults to 2.
        api_key (str): description. Defaults to Depends(get_api_key).
        user_id (_type_, optional): _description_. Defaults to None.
    """
    # Save the uploaded file
    # headers = request.headers
    # logger.debug(headers)
    # logger.debug(api_key)
    try:
        if stems not in [2, 4]:
            msg = "Invalid stems parameter. Only 2 or 4 are allowed."
            raise HTTPException(status_code=400, detail=msg)
        if user_id is None:
            raise HTTPException(status_code=400, detail="user_id field is required")
        audio_path = f"temp/{file.filename}"
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the file
        res = DEMUCS(audio_path)
        print(res)
        # Access the separated audio directly
        vocals = res["vocals"].cpu().numpy()
        if stems == 4:
            bass = res["bass"].cpu().numpy()
            drums = res["drums"].cpu().numpy()
            other = res["other"].cpu().numpy()
        if stems == 2:
            music = (res["bass"] + res["drums"] + res["other"]).cpu().numpy()
        output_path = f"temp/output/{user_id}/"
        os.makedirs(output_path, exist_ok=True)

        # # Save the separated tracks
        vocals_path = os.path.join(output_path, 'vocals.mp3')
        if stems == 4:
            bass_path = os.path.join(output_path, 'bass.mp3')
            drums_path = os.path.join(output_path, 'drums.mp3')
            other_path = os.path.join(output_path, 'other.mp3')
        if stems == 2:
            music_path = os.path.join(output_path, 'music.mp3')

        # Save the separated tracks
        audiofile.write(vocals_path, vocals, 44100)
        if stems == 4:
            audiofile.write(bass_path, bass, 44100)
            audiofile.write(drums_path, drums, 44100)
            audiofile.write(other_path, other, 44100)
        if stems == 2:
            audiofile.write(music_path, music, 44100)
        # Create a JSON response with the paths to the separated files
        response = {
            "vocals.mp3": output_path,
            "bass.mp3": output_path,
            "drums.mp3": output_path,
            "other.mp3": output_path
        } if stems == 4 else {
            "vocals.mp3": output_path,
            "music.mp3": output_path
        }
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # Return the JSON response
        return JSONResponse(content=response)
    except Exception as e:
        detail = f"An error occurred during audio separation: {str(e)}"
        raise HTTPException(status_code=500, detail=detail) from e

# download files
@app.get("/download")
async def download(file_path: str, api_key: str = Depends(get_api_key)):
    """_summary_
    donwnload files
    """
    logger.debug(file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_name = os.path.basename(file_path)
    return FileResponse(path=file_path, filename=file_name, media_type='audio/mp3')

# delete a folder
@app.delete("/delete/{folder_name}")
async def delete_folder(folder_name: str, api_key: str = Depends(get_api_key)):
    """_summary_
    delete the cache songs of th current use here folder_name is the id of user
    """
    # Construct the folder path (assumes folders are in the current working directory)
    folder_name = f'temp/output/{folder_name}'
    folder_path = os.path.join(os.getcwd(), folder_name)
    logger.debug(folder_name)

    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="The specified path is not a folder")

    try:
        shutil.rmtree(folder_path)
        return {"message": f"Folder '{folder_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from e


# home
@app.get("/")
def home():
    """_summary_
    demo home
    """
    return 'Welcome to my api world'
