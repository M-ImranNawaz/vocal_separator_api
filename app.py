import shutil
import os
import json
import logging
from typing import Optional
import audiofile
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Security
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store the model
DEMUCS_MODEL = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load the model
    global DEMUCS_MODEL
    logger.info("Loading Demucs model...")
    
    try:
        from src.utils.get_models import download_all_models
        from src import models
        
        # Load model configuration
        models_json = json.load(open("src/models_dir/models.json", "r", encoding="utf-8"))
        logger.info('Model config loaded')
        
        # Download all models (if not already downloaded)
        download_all_models(models_json)
        logger.info('Models downloaded')
        
        # Initialize the model
        DEVICE = "cpu"
        META = {"segment": 2, "split": True}
        DEMUCS_MODEL = models.Demucs(name="hdemucs_mmi", other_metadata=META, device=DEVICE, logger=None)
        logger.info('Model initialized successfully')
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
    
    yield
    
    # Shutdown: Cleanup if needed
    logger.info("Shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# API Key configuration
API_KEY_NAME = "access_token"
API_KEY = "xSx+4YQ5PkrWjcMu+KQEO8chSzD/vt6eYMaJCz8SyRA="
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, 
            detail="Could not validate credentials"
        )

@app.post("/separate")
async def separate(
    file: UploadFile = File(...), 
    stems: int = 2,
    user_id: Optional [str] = None, 
    api_key: str = Depends(get_api_key)
):
    if DEMUCS_MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        if stems not in [2, 4]:
            raise HTTPException(status_code=400, detail="Invalid stems parameter. Only 2 or 4 are allowed.")
        
        if user_id is None:
            raise HTTPException(status_code=400, detail="user_id field is required")
        
        # Create temp directory
        os.makedirs("temp", exist_ok=True)
        
        # Save uploaded file
        audio_path = f"temp/{file.filename}"
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process with model
        logger.info(f"Processing audio file: {file.filename}")
        res = DEMUCS_MODEL(audio_path)
        
        # Extract audio data
        vocals = res["vocals"].cpu().numpy()
        if stems == 4:
            bass = res["bass"].cpu().numpy()
            drums = res["drums"].cpu().numpy()
            other = res["other"].cpu().numpy()
        elif stems == 2:
            music = (res["bass"] + res["drums"] + res["other"]).cpu().numpy()
        
        # Create output directory
        output_path = f"temp/output/{user_id}/"
        os.makedirs(output_path, exist_ok=True)
        
        # Save separated tracks
        vocals_path = os.path.join(output_path, 'vocals.mp3')
        audiofile.write(vocals_path, vocals, 44100)
        
        response_data = {"vocals.mp3": vocals_path}
        
        if stems == 4:
            bass_path = os.path.join(output_path, 'bass.mp3')
            drums_path = os.path.join(output_path, 'drums.mp3')
            other_path = os.path.join(output_path, 'other.mp3')
            
            audiofile.write(bass_path, bass, 44100)
            audiofile.write(drums_path, drums, 44100)
            audiofile.write(other_path, other, 44100)
            
            response_data.update({
                "bass.mp3": bass_path,
                "drums.mp3": drums_path,
                "other.mp3": other_path
            })
        elif stems == 2:
            music_path = os.path.join(output_path, 'music.mp3')
            audiofile.write(music_path, music, 44100)
            response_data["music.mp3"] = music_path
        
        # Cleanup input file
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        logger.info(f"Successfully processed {file.filename}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        # Cleanup on error
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
        raise HTTPException(status_code=500, detail=f"Audio separation failed: {str(e)}")

@app.get("/download")
async def download(file_path: str, api_key: str = Depends(get_api_key)):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    file_name = os.path.basename(file_path)
    return FileResponse(path=file_path, filename=file_name, media_type='audio/mp3')

@app.delete("/delete/{folder_name}")
async def delete_folder(folder_name: str, api_key: str = Depends(get_api_key)):
    folder_path = f'temp/output/{folder_name}'
    full_path = os.path.join(os.getcwd(), folder_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    
    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="Path is not a folder")
    
    try:
        shutil.rmtree(full_path)
        return {"message": f"Folder '{folder_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@app.get("/")
def home():
    return {"message": "Demucs API is running", "status": "healthy"}

@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": DEMUCS_MODEL is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)