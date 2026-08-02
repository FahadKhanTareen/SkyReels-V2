from typing import Optional

import torch
from PIL import Image

from .styles import Style


class PortraitStylizerPipeline:
    """Turns a selfie into a stylized AI portrait using an SDXL img2img pipeline.

    IP-Adapter is used to keep the generated portrait recognizable as the same
    person, since plain img2img at the strength needed for a strong style
    transfer tends to drift away from the source face.
    """

    def __init__(
        self,
        model_id: str = "stabilityai/stable-diffusion-xl-base-1.0",
        device: str = "cuda",
        weight_dtype: torch.dtype = torch.float16,
        use_ip_adapter: bool = True,
        ip_adapter_scale: float = 0.6,
        offload: bool = False,
    ):
        from diffusers import StableDiffusionXLImg2ImgPipeline

        self.device = device
        self.offload = offload
        self.use_ip_adapter = use_ip_adapter

        self.pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(model_id, torch_dtype=weight_dtype)
        if use_ip_adapter:
            self.pipe.load_ip_adapter(
                "h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin"
            )
            self.pipe.set_ip_adapter_scale(ip_adapter_scale)

        if offload:
            self.pipe.enable_model_cpu_offload()
        else:
            self.pipe.to(device)

    @torch.no_grad()
    def __call__(
        self,
        image: Image.Image,
        style: Style,
        seed: Optional[int] = None,
        strength: Optional[float] = None,
        guidance_scale: Optional[float] = None,
        num_inference_steps: int = 30,
        size: int = 1024,
    ) -> Image.Image:
        image = image.convert("RGB").resize((size, size))
        generator = torch.Generator(device=self.device).manual_seed(seed) if seed is not None else None

        kwargs = dict(
            prompt=style.prompt,
            negative_prompt=style.negative_prompt,
            image=image,
            strength=strength if strength is not None else style.strength,
            guidance_scale=guidance_scale if guidance_scale is not None else style.guidance_scale,
            num_inference_steps=num_inference_steps,
            generator=generator,
        )
        if self.use_ip_adapter:
            kwargs["ip_adapter_image"] = image

        result = self.pipe(**kwargs)
        return result.images[0]
