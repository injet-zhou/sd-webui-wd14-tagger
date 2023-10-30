import os.path
from typing import Callable
from threading import Lock
from secrets import compare_digest

import tqdm
from PIL import Image

from modules import shared
from modules.api.api import decode_base64_to_image
from modules.call_queue import queue_lock
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tagger import utils
from tagger import api_models as models


class Api:
    def __init__(self, app: FastAPI, queue_lock: Lock, prefix: str = None) -> None:
        if shared.cmd_opts.api_auth:
            self.credentials = dict()
            for auth in shared.cmd_opts.api_auth.split(","):
                user, password = auth.split(":")
                self.credentials[user] = password

        self.app = app
        self.queue_lock = queue_lock
        self.prefix = prefix

        self.add_api_route(
            'interrogate',
            self.endpoint_interrogate,
            methods=['POST'],
            response_model=models.TaggerInterrogateResponse
        )

        self.add_api_route(
            'interrogators',
            self.endpoint_interrogators,
            methods=['GET'],
            response_model=models.InterrogatorsResponse
        )

        self.add_api_route(
            'batch_files_interrogate',
            self.endpoint_batch_files_interrogate,
            methods=['POST'],
            response_model=models.InterrogateBatchFilesResponse
        )

    def auth(self, creds: HTTPBasicCredentials = Depends(HTTPBasic())):
        if creds.username in self.credentials:
            if compare_digest(creds.password, self.credentials[creds.username]):
                return True

        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Basic"
            })

    def add_api_route(self, path: str, endpoint: Callable, **kwargs):
        if self.prefix:
            path = f'{self.prefix}/{path}'

        if shared.cmd_opts.api_auth:
            return self.app.add_api_route(path, endpoint, dependencies=[Depends(self.auth)], **kwargs)
        return self.app.add_api_route(path, endpoint, **kwargs)

    def endpoint_interrogate(self, req: models.TaggerInterrogateRequest):
        if req.image is None:
            raise HTTPException(404, 'Image not found')

        if req.model not in utils.interrogators.keys():
            raise HTTPException(404, 'Model not found')

        image = decode_base64_to_image(req.image)
        interrogator = utils.interrogators[req.model]

        with self.queue_lock:
            ratings, tags = interrogator.interrogate(image)

        return models.TaggerInterrogateResponse(
            caption={
                **ratings,
                **interrogator.postprocess_tags(
                    tags,
                    req.threshold
                )
            })

    def endpoint_batch_files_interrogate(self, req: models.InterrogateBatchFilesRequest):
        src = req.src_dir
        dst = req.dst_dir
        model = req.model
        if src is None or src == "":
            raise HTTPException(400, 'Source directory is required')
        if not os.path.exists(src):
            raise HTTPException(404, 'Source directory not exists')
        if dst is None or dst == "":
            dst = src
        if not os.path.exists(dst):
            os.makedirs(dst)
        if model is None or model == "":
            raise HTTPException(400, 'Model is required')
        if model not in utils.interrogators.keys():
            raise HTTPException(404, 'Model not found')

        images = os.listdir(src)
        if images is None or len(images) == 0:
            return models.InterrogateBatchFilesResponse(
                success=True,
                message="No images to interrogate"
            )
        include_ext = ["jpg", "jpeg", "png"]
        images = [image for image in images if image.split(".")[-1].lower() in include_ext]
        if images is None or len(images) == 0:
            return models.InterrogateBatchFilesResponse(
                success=True,
                message="No images to interrogate"
            )

        with self.queue_lock:
            interrogator = utils.interrogators[model]
            pbar = tqdm.tqdm(images)
            for index, image in enumerate(pbar):
                desc = f"Interrogating {index + 1}/{len(images)}"
                pbar.set_description(desc)
                image_path = os.path.join(src, image)
                img = Image.open(image_path)
                ratings, tags = interrogator.interrogate(img)
                tags = interrogator.postprocess_tags(tags, 0.35)
                save_filename = image.split('.')[0] + ".txt"
                save_path = os.path.join(dst, save_filename)
                tag_str = ""
                for tag in tags.keys():
                    tag_str += f"{tag},"
                tag_str = tag_str[:-1]
                with open(save_path, "w") as f:
                    f.write(tag_str)

        return models.InterrogateBatchFilesResponse(
            success=True,
            message="Interrogation completed"
        )

    def endpoint_interrogators(self):
        return models.InterrogatorsResponse(
            models=list(utils.interrogators.keys())
        )


def on_app_started(_, app: FastAPI):
    if len(utils.interrogators) == 0:
        utils.refresh_interrogators()
    Api(app, queue_lock, '/tagger/v1')
