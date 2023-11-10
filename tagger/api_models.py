from typing import List, Dict

from modules.api import models as sd_models
from pydantic import BaseModel, Field


class TaggerInterrogateRequest(sd_models.InterrogateRequest):
    model: str = Field(
        title='Model',
        description='The interrogate model used.'
    )

    threshold: float = Field(
        default=0.35,
        title='Threshold',
        description='',
        ge=0,
        le=1
    )


class TaggerInterrogateResponse(BaseModel):
    caption: Dict[str, float] = Field(
        title='Caption',
        description='The generated caption for the image.'
    )


class InterrogatorsResponse(BaseModel):
    models: List[str] = Field(
        title='Models',
        description=''
    )


class InterrogateBatchFilesRequest(BaseModel):
    src_dir: str = Field(
        title='Source Directory',
        description='The directory containing the images to be interrogated.'
    )
    dst_dir: str = Field(
        title='Destination Directory',
        description='The directory to save the interrogated images.'
    )
    model: str = Field(
        title='Model',
        description='The interrogate model used.'
    )


class InterrogateBatchFilesResponse(BaseModel):
    success: bool = Field(
        title='Success',
        description='Whether the task is set successfully'
    )
    message: str = Field(
        title='Message',
        description='Message of the response'
    )

class ImageItem(BaseModel):
    data: str
    name: str

class InterrogateResult(BaseModel):
    caption: Dict[str, float]
    name: str

class BatchInterrogateRequest(BaseModel):
    images: List[ImageItem] = Field(
        title='Images',
        description='The images to be interrogated.'
    )
    model: str = Field(
        title='Model',
        description='The interrogate model used.'
    )
    threshold: float = Field(
        default=0.35,
        title='Threshold',
        description='',
        ge=0,
        le=1
    )

class BatchInterrogateResponse(BaseModel):
    code: int = Field(
        title='Code',
        description='The code of the response.'
    )
    message: str = Field(
        title='Message',
        description='The message of the response.'
    )
    captions: List[InterrogateResult] = Field(
        title='Captions',
        description='The results of the interrogation.'
    )
