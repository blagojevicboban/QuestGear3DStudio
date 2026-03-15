"""
Neural Enhancer Module for QuestGear3D
Integrates DiFix3D+ (Single-Step Diffusion) for NeRF/3DGS post-processing.
"""

import torch
import numpy as np
import os
from PIL import Image
from typing import Optional, Union, Tuple
import logging

# We will try to import diffusers. If not found, the module will be disabled.
HAS_DIFFUSERS = False
try:
    from diffusers import DiffusionPipeline
    from .difix.pipeline_difix import DifixPipeline
    from .difix.autoencoder_kl import AutoencoderKL
    HAS_DIFFUSERS = True
except ImportError:
    pass

class NeuralEnhancer:
    """Manages AI-based image enhancement using DiFix3D+."""
    
    def __init__(self, model_id: str = "nvidia/difix", device: str = "auto"):
        self.model_id = model_id
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.pipe = None
        self.is_loaded = False
        self.logger = logging.getLogger("QuestGear3D.NeuralEnhancer")

    def load_model(self):
        """Load the DiFix3D+ pipeline from Hugging Face."""
        if not HAS_DIFFUSERS:
            self.logger.error("Diffusers and local DiFix modules not found.")
            return False
            
        try:
            self.logger.info(f"Loading DiFix3D+ model: {self.model_id}...")
            
            # Load VAE and UNet separately since we are using custom classes
            vae = AutoencoderKL.from_pretrained(self.model_id, subfolder="vae")
            # The rest can be standard
            self.pipe = DifixPipeline.from_pretrained(
                self.model_id, 
                vae=vae,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                # we don't need trust_remote_code if we provide components
            )
            self.pipe.to(self.device)
            self.is_loaded = True
            self.logger.info("DiFix3D+ loaded successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load DiFix3D+: {e}")
            return False

    def enhance_image(
        self, 
        image: Union[Image.Image, np.ndarray], 
        prompt: str = "remove degradation",
        guidance_scale: float = 0.0,
        timestep: int = 199
    ) -> Optional[Image.Image]:
        """
        Enhance a single image using DiFix3D+ one-step diffusion.
        
        Args:
            image: Input image (PIL or numpy)
            prompt: Text prompt for enhancement guidance
            guidance_scale: Scale for classifier-free guidance (0.0 for DiFix)
            timestep: The specific noise timestep to use for the single-step fix
            
        Returns:
            Enhanced PIL Image or None if failed
        """
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
            
        try:
            # DiFix3D+ is designed for 1 step inference
            output = self.pipe(
                prompt=prompt,
                image=image,
                num_inference_steps=1,
                timesteps=[timestep],
                guidance_scale=guidance_scale
            ).images[0]
            
            return output
        except Exception as e:
            self.logger.error(f"Enhancement error: {e}")
            return None

    def enhance_batch(self, images: list, **kwargs):
        """Enhance a list of images."""
        results = []
        for img in images:
            res = self.enhance_image(img, **kwargs)
            if res:
                results.append(res)
        return results
