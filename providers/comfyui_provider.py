"""
ComfyUI image generation provider for local Stable Diffusion workflows.

Requires a running ComfyUI server (default http://localhost:8188) and the
``requests`` package. No API key needed.
"""

import json
import time
import uuid
from typing import Optional

from .base import BaseImageProvider


# Minimal txt2img workflow -- users can replace via config or subclass.
_DEFAULT_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 0,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "", "clip": ["4", 1]},
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "bad quality, blurry", "clip": ["4", 1]},
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "sensia", "images": ["8", 0]},
    },
}


class ComfyUIProvider(BaseImageProvider):
    """Image generation via a local ComfyUI server.

    Sends a workflow JSON, polls for completion, and downloads the result.
    Only ``requests`` is needed.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        workflow: Optional[dict] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.workflow = workflow or _DEFAULT_WORKFLOW

    def _requests(self):
        try:
            import requests
        except ImportError:
            raise ImportError(
                "The 'requests' package is required for ComfyUIProvider. "
                "Install it with: pip install requests"
            )
        return requests

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: Optional[str] = None,
    ) -> bytes:
        requests = self._requests()
        width, height = (int(d) for d in size.split("x"))
        workflow = json.loads(json.dumps(self.workflow))

        # Inject prompt text and dimensions into the workflow.
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = prompt
        if "5" in workflow:
            workflow["5"]["inputs"]["width"] = width
            workflow["5"]["inputs"]["height"] = height

        client_id = uuid.uuid4().hex
        payload = {"prompt": workflow, "client_id": client_id}
        resp = requests.post(
            f"{self.base_url}/prompt", json=payload, timeout=10
        )
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]

        # Poll until the prompt finishes.
        for _ in range(120):
            time.sleep(2)
            history = requests.get(
                f"{self.base_url}/history/{prompt_id}", timeout=10
            ).json()
            if prompt_id in history:
                break
        else:
            raise TimeoutError("ComfyUI did not finish within 240 seconds.")

        outputs = history[prompt_id]["outputs"]
        # Find the first SaveImage node output.
        for node_output in outputs.values():
            images = node_output.get("images", [])
            if images:
                filename = images[0]["filename"]
                subfolder = images[0].get("subfolder", "")
                img_resp = requests.get(
                    f"{self.base_url}/view",
                    params={
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": "output",
                    },
                    timeout=30,
                )
                img_resp.raise_for_status()
                return img_resp.content

        raise RuntimeError("No image output found in ComfyUI history.")

    @classmethod
    def from_config(cls, config: dict) -> "ComfyUIProvider":
        return cls(
            base_url=config.get("base_url", "http://localhost:8188"),
            workflow=config.get("workflow"),
        )
