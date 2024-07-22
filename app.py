# import json
# import audiofile
# import os
# import numpy as np
# import torch as torch
# from src.utils.get_models import download_all_models
# from src import models

# # Load model configuration
# models_json = json.load(open("src/models_dir/models.json", "r"))

# # Download all models (if not already downloaded)
# download_all_models(models_json)

# # Path to your audio file
# AUDIO_FILE_PATH = '/Users/imrannawaz/Documents/Rolling in the Deep.mp3'
# output_path = "/Users/imrannawaz/Documents/output/"
# # device = "cuda"  # Use "cuda" if you have a compatible GPU
# device = "cuda" if torch.cuda.is_available() else "cpu"

# # Ensure output directory exists
# if not os.path.exists(output_path):
#     os.makedirs(output_path)

# # Initialize the model
# demucs = models.Demucs(name="hdemucs_mmi", other_metadata={"segment": 2, "split": True}, device=device, logger=None)

# # Separating an audio file
# res = demucs(AUDIO_FILE_PATH)

# print(res)
# # Access the separated audio directly
# vocals = res["vocals"].cpu().numpy()
# bass = res["bass"].cpu().numpy()
# drums = res["drums"].cpu().numpy()
# other = res["other"].cpu().numpy()

# # Save the separated tracks
# audiofile.write(os.path.join(output_path, 'vocals.mp3'), vocals, 44100)
# audiofile.write(os.path.join(output_path, 'bass.mp3'), bass, 44100)
# audiofile.write(os.path.join(output_path, 'drums.mp3'), drums, 44100)
# audiofile.write(os.path.join(output_path, 'other.mp3'), other, 44100)

# print("Audio separation complete. Separated files saved as 'vocals.wav', 'bass.wav', 'drums.wav', and 'other.wav'.")



# from fastapi import FastAPI, File, UploadFile
# from fastapi.responses import FileResponse
# import shutil
# import os
# import json
# import audiofile
# import torch
# from src.utils.get_models import download_all_models
# from src import models

# app = FastAPI()

# # Load model configuration
# models_json = json.load(open("src/models_dir/models.json", "r"))

# # Download all models (if not already downloaded)
# download_all_models(models_json)

# # Initialize the model
# device = "cuda" if torch.cuda.is_available() else "cpu"
# demucs = models.Demucs(name="hdemucs_mmi", other_metadata={"segment": 2, "split": True}, device=device, logger=None)

# @app.post("/separate")
# async def separate(file: UploadFile = File(...)):
#     # Save the uploaded file
#     audio_path = f"temp/{file.filename}"
#     with open(audio_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     # Process the file
#     res = demucs(audio_path)

#     # Access the separated audio directly
#     vocals = res["vocals"].cpu().numpy()
#     music = (res["bass"] + res["drums"] + res["other"]).cpu().numpy()

#     output_path = "temp/output/"
#     os.makedirs(output_path, exist_ok=True)

#     # Save the separated tracks
#     vocals_path = os.path.join(output_path, 'vocals.wav')
#     music_path = os.path.join(output_path, 'music.wav')
#     audiofile.write(vocals_path, vocals, 44100)
#     audiofile.write(music_path, music, 44100)

#     # Return the paths to the separated files
#     return {"vocals": vocals_path, "music": music_path}






from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import json
import audiofile
import torch
from src.utils.get_models import download_all_models
from src import models
import logging

logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.DEBUG)

app = FastAPI()

# Load model configuration
models_json = json.load(open("src/models_dir/models.json", "r"))
logger.debug('model loaded')

# Download all models (if not already downloaded)
download_all_models(models_json)
logger.debug('downloaded')

# Initialize the model
device = "cpu"
demucs = models.Demucs(name="hdemucs_mmi", other_metadata={"segment": 2, "split": True}, device=device, logger=None)
logger.debug('initialized ')

@app.post("/separate")
async def separate(file: UploadFile = File(...), stems: int = 2):
    # Save the uploaded file
    try:
        if stems not in [2, 4]:
            raise HTTPException(status_code=400, detail="Invalid stems parameter. Only 2 or 4 are allowed.")
        
        audio_path = f"temp/{file.filename}"
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the file
        res = demucs(audio_path)
        print(res)
        # Access the separated audio directly
        vocals = res["vocals"].cpu().numpy()
        if stems == 4:
            bass = res["bass"].cpu().numpy()
            drums = res["drums"].cpu().numpy()
            other = res["other"].cpu().numpy()
        if stems == 2:
            music = (res["bass"] + res["drums"] + res["other"]).cpu().numpy()


        output_path = "temp/output/"
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


        # Return the JSON response
        return JSONResponse(content=response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during audio separation: {str(e)}")

#download files
@app.get("/download")
async def download(file_path: str):
    return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type='audio/wav')

# home
@app.get("/")
def home():
    return 'Welcome to my api world'












# from fastapi import FastAPI, File, UploadFile
# from fastapi.responses import StreamingResponse, FileResponse
# import shutil
# import os
# import json
# import audiofile
# import io
# import torch
# from src.utils.get_models import download_all_models
# from src import models

# app = FastAPI()

# # Load model configuration
# models_json = json.load(open("src/models_dir/models.json", "r"))

# # Download all models (if not already downloaded)
# download_all_models(models_json)

# # Initialize the model
# device = "cuda" if torch.cuda.is_available() else "cpu"
# demucs = models.Demucs(name="hdemucs_mmi", other_metadata={"segment": 2, "split": True}, device=device, logger=None)

# @app.post("/separate")
# async def separate(file: UploadFile = File(...)):
#     # Save the uploaded file
#     audio_path = f"temp/{file.filename}"
#     with open(audio_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     # Process the file
#     res = demucs(audio_path)

#     # Access the separated audio directly
#     vocals = res["vocals"].cpu().numpy()
#     bass = res["bass"].cpu().numpy()
#     drums = res["drums"].cpu().numpy()
#     other = res["other"].cpu().numpy()

#     # Prepare in-memory bytes for each separated track
#     vocal_bytes = io.BytesIO(initial_bytes= vocals)
#     bass_bytes = io.BytesIO(initial_bytes=bass)
#     drums_bytes = io.BytesIO(initial_bytes=drums)
#     other_bytes = io.BytesIO(initial_bytes=other)

#     # audiofile.write(vocal_bytes, vocals, 44100)
#     # audiofile.write(bass_bytes, bass, 44100)
#     # audiofile.write(drums_bytes, drums, 44100)
#     # audiofile.write(other_bytes, other, 44100)

#     # vocal_bytes.seek(0)
#     # bass_bytes.seek(0)
#     # drums_bytes.seek(0)
#     # other_bytes.seek(0)

#     # Return the separated files as bytes
#     return {
#         "vocals": StreamingResponse(vocals, media_type="audio/wav"),
#         # "bass": StreamingResponse(bass_bytes, media_type="audio/wav"),
#         # "drums": StreamingResponse(drums_bytes, media_type="audio/wav"),
#         # "other": StreamingResponse(other_bytes, media_type="audio/wav")
#     }

# @app.get("/download")
# async def download(file_path: str):
#     return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type='audio/wav')
