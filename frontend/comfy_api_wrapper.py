import json
from urllib import request, parse
import random

inpaint_api_prompt = """
{
  "3": {
    "inputs": {
      "seed": 1043433909848955,
      "steps": 20,
      "cfg": 10,
      "sampler_name": "ddim",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "30",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "26",
        0
      ]
    },
    "class_type": "KSampler"
  },
  "6": {
    "inputs": {
      "text": "warped, 360 photo, seamless",
      "clip": [
        "29",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": {
      "text": "watermark, text",
      "clip": [
        "29",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "8": {
    "inputs": {
      "samples": [
        "3",
        0
      ],
      "vae": [
        "29",
        2
      ]
    },
    "class_type": "VAEDecode"
  },
  "20": {
    "inputs": {
      "image": "C:/Users/SREAL/Lab Users/mattg/genai/gen-sys/ComfyUI_windows_portable/ComfyUI/output/img2img_00016_cropmerge_filltrans_2.png",
      "upload": "image"
    },
    "class_type": "LoadImage"
  },
  "26": {
    "inputs": {
      "grow_mask_by": 24,
      "pixels": [
        "20",
        0
      ],
      "vae": [
        "29",
        2
      ],
      "mask": [
        "20",
        1
      ]
    },
    "class_type": "VAEEncodeForInpaint"
  },
  "29": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0_0.9vae.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "30": {
    "inputs": {
      "unet_name": "diffusion_pytorch_model.fp16.safetensors"
    },
    "class_type": "UNETLoader"
  },
  "38": {
    "inputs": {
      "upscale_model": [
        "39",
        0
      ],
      "image": [
        "8",
        0
      ]
    },
    "class_type": "ImageUpscaleWithModel"
  },
  "39": {
    "inputs": {
      "model_name": "4x-UltraSharp.pth"
    },
    "class_type": "UpscaleModelLoader"
  },
  "42": {
    "inputs": {
      "filename_prefix": "360_inpaint_upscale",
      "images": [
        "38",
        0
      ]
    },
    "class_type": "SaveImage"
  }
}
"""

img2img_prompt = """
{
  "4": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0_0.9vae.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "6": {
    "inputs": {
      "text": "360 photo of margaritaville",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": {
      "text": "text, watermark",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "10": {
    "inputs": {
      "add_noise": "enable",
      "noise_seed": 42,
      "steps": 25,
      "cfg": 10,
      "sampler_name": "ddim",
      "scheduler": "normal",
      "start_at_step": 0,
      "end_at_step": 20,
      "return_with_leftover_noise": "enable",
      "model": [
        "4",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "50",
        0
      ]
    },
    "class_type": "KSamplerAdvanced"
  },
  "11": {
    "inputs": {
      "add_noise": "disable",
      "noise_seed": 42,
      "steps": 25,
      "cfg": 10,
      "sampler_name": "euler",
      "scheduler": "normal",
      "start_at_step": 20,
      "end_at_step": 10000,
      "return_with_leftover_noise": "disable",
      "model": [
        "12",
        0
      ],
      "positive": [
        "15",
        0
      ],
      "negative": [
        "16",
        0
      ],
      "latent_image": [
        "10",
        0
      ]
    },
    "class_type": "KSamplerAdvanced"
  },
  "12": {
    "inputs": {
      "ckpt_name": "sd_xl_refiner_1.0_0.9vae.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "15": {
    "inputs": {
      "text": "360 photo of margaritaville",
      "clip": [
        "12",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "16": {
    "inputs": {
      "text": "text, watermark",
      "clip": [
        "12",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "17": {
    "inputs": {
      "samples": [
        "11",
        0
      ],
      "vae": [
        "12",
        2
      ]
    },
    "class_type": "VAEDecode"
  },
  "19": {
    "inputs": {
      "filename_prefix": "img2img_refined",
      "images": [
        "17",
        0
      ]
    },
    "class_type": "SaveImage"
  },
  "49": {
    "inputs": {
      "image": "R0010079_2_resized (2).JPG",
      "upload": "image"
    },
    "class_type": "LoadImage"
  },
  "50": {
    "inputs": {
      "pixels": [
        "49",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEEncode"
  }
}
"""

img2img_singlectrl_prompt = """
{
  "4": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0_0.9vae.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint - BASE"
    }
  },
  "6": {
    "inputs": {
      "text": "a sci-fi room with a portal to another dimension (360:1.3)",
      "clip": [
        "58",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "(text:1.3), (watermark:1.2), (deformed:1.2)",
      "clip": [
        "58",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "17": {
    "inputs": {
      "samples": [
        "57",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "19": {
    "inputs": {
      "filename_prefix": "img2img_base_",
      "images": [
        "17",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  },
  "49": {
    "inputs": {
      "image": "R0010072_00001_ (3).png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "50": {
    "inputs": {
      "pixels": [
        "49",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEEncode",
    "_meta": {
      "title": "VAE Encode"
    }
  },
  "57": {
    "inputs": {
      "seed": 43,
      "tileX": 1,
      "tileY": 0,
      "steps": 25,
      "cfg": 10,
      "sampler_name": "dpmpp_3m_sde_gpu",
      "scheduler": "exponential",
      "denoise": 1,
      "model": [
        "58",
        0
      ],
      "positive": [
        "67",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "50",
        0
      ]
    },
    "class_type": "Asymmetric Tiled KSampler",
    "_meta": {
      "title": "Asymmetric Tiled KSampler"
    }
  },
  "58": {
    "inputs": {
      "lora_name": "View360.safetensors",
      "strength_model": 1,
      "strength_clip": 1,
      "model": [
        "4",
        0
      ],
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "LoraLoader",
    "_meta": {
      "title": "Load LoRA"
    }
  },
  "61": {
    "inputs": {
      "control_net_name": "t2i-adapter-depth-midas-sdxl-1.0.safetensors"
    },
    "class_type": "ControlNetLoader",
    "_meta": {
      "title": "Load ControlNet Model"
    }
  },
  "66": {
    "inputs": {
      "image": "MIDAS_DEPTH_00001_.png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "67": {
    "inputs": {
      "strength": 1.0,
      "conditioning": [
        "6",
        0
      ],
      "control_net": [
        "61",
        0
      ],
      "image": [
        "66",
        0
      ]
    },
    "class_type": "ControlNetApply",
    "_meta": {
      "title": "Apply ControlNet"
    }
  }
}
"""

img2img_doublectrl_prompt = """
{
  "4": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0_0.9vae.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint - BASE"
    }
  },
  "6": {
    "inputs": {
      "text": "a sci-fi room with a portal to another dimension (360:1.3)",
      "clip": [
        "58",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "text, watermark, (deformed:1.2)",
      "clip": [
        "58",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "17": {
    "inputs": {
      "samples": [
        "57",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "19": {
    "inputs": {
      "filename_prefix": "img2img_base_",
      "images": [
        "17",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  },
  "49": {
    "inputs": {
      "image": "R0010072_00001_ (3).png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "50": {
    "inputs": {
      "pixels": [
        "49",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEEncode",
    "_meta": {
      "title": "VAE Encode"
    }
  },
  "57": {
    "inputs": {
      "seed": 43,
      "tileX": 1,
      "tileY": 0,
      "steps": 25,
      "cfg": 10,
      "sampler_name": "dpmpp_3m_sde_gpu",
      "scheduler": "exponential",
      "denoise": 1,
      "model": [
        "58",
        0
      ],
      "positive": [
        "67",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "50",
        0
      ]
    },
    "class_type": "Asymmetric Tiled KSampler",
    "_meta": {
      "title": "Asymmetric Tiled KSampler"
    }
  },
  "58": {
    "inputs": {
      "lora_name": "View360.safetensors",
      "strength_model": 1,
      "strength_clip": 1,
      "model": [
        "4",
        0
      ],
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "LoraLoader",
    "_meta": {
      "title": "Load LoRA"
    }
  },
  "61": {
    "inputs": {
      "control_net_name": "t2i-adapter-depth-midas-sdxl-1.0.safetensors"
    },
    "class_type": "ControlNetLoader",
    "_meta": {
      "title": "Load ControlNet Model"
    }
  },
  "63": {
    "inputs": {
      "strength": 0.5,
      "conditioning": [
        "6",
        0
      ],
      "control_net": [
        "61",
        0
      ],
      "image": [
        "64",
        0
      ]
    },
    "class_type": "ControlNetApply",
    "_meta": {
      "title": "Apply ControlNet"
    }
  },
  "64": {
    "inputs": {
      "image": "MIDAS_DEPTH_00001_.png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "66": {
    "inputs": {
      "image": "MIDAS_DEPTH_00002_.png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "67": {
    "inputs": {
      "strength": 0.5,
      "conditioning": [
        "63",
        0
      ],
      "control_net": [
        "61",
        0
      ],
      "image": [
        "66",
        0
      ]
    },
    "class_type": "ControlNetApply",
    "_meta": {
      "title": "Apply ControlNet"
    }
  }
}
"""

txt2img_doublectrl_prompt = """
{
  "4": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0_0.9vae.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint - BASE"
    }
  },
  "6": {
    "inputs": {
      "text": "a sci-fi room with a portal to another dimension (360:1.3)",
      "clip": [
        "58",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "(text:1.3), (watermark:1.1), (deformed:1.2)",
      "clip": [
        "58",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "17": {
    "inputs": {
      "samples": [
        "57",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "19": {
    "inputs": {
      "filename_prefix": "img2img_base_",
      "images": [
        "17",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  },
  "57": {
    "inputs": {
      "seed": 43,
      "tileX": 1,
      "tileY": 0,
      "steps": 25,
      "cfg": 10,
      "sampler_name": "dpmpp_3m_sde_gpu",
      "scheduler": "exponential",
      "denoise": 1,
      "model": [
        "58",
        0
      ],
      "positive": [
        "67",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "68",
        0
      ]
    },
    "class_type": "Asymmetric Tiled KSampler",
    "_meta": {
      "title": "Asymmetric Tiled KSampler"
    }
  },
  "58": {
    "inputs": {
      "lora_name": "View360.safetensors",
      "strength_model": 1,
      "strength_clip": 1,
      "model": [
        "4",
        0
      ],
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "LoraLoader",
    "_meta": {
      "title": "Load LoRA"
    }
  },
  "61": {
    "inputs": {
      "control_net_name": "t2i-adapter-depth-midas-sdxl-1.0.safetensors"
    },
    "class_type": "ControlNetLoader",
    "_meta": {
      "title": "Load ControlNet Model"
    }
  },
  "63": {
    "inputs": {
      "strength": 1,
      "conditioning": [
        "6",
        0
      ],
      "control_net": [
        "61",
        0
      ],
      "image": [
        "64",
        0
      ]
    },
    "class_type": "ControlNetApply",
    "_meta": {
      "title": "Apply ControlNet"
    }
  },
  "64": {
    "inputs": {
      "image": "R0010072_resized_DEPTH_00001_.png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "66": {
    "inputs": {
      "image": "screenshot-spheres_resized_DEPTH_00001_.png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "67": {
    "inputs": {
      "strength": 0,
      "conditioning": [
        "63",
        0
      ],
      "control_net": [
        "61",
        0
      ],
      "image": [
        "66",
        0
      ]
    },
    "class_type": "ControlNetApply",
    "_meta": {
      "title": "Apply ControlNet"
    }
  },
  "68": {
    "inputs": {
      "width": 1440,
      "height": 720,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  }
}
"""

midas_depth_prompt = """
{
  "49": {
    "inputs": {
      "image": "R0010072_00001_ (3).png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "59": {
    "inputs": {
      "a": 6.283185307179586,
      "bg_threshold": 0.1,
      "resolution": 704,
      "image": [
        "49",
        0
      ]
    },
    "class_type": "MiDaS-DepthMapPreprocessor",
    "_meta": {
      "title": "MiDaS Depth Map"
    }
  },
  "65": {
    "inputs": {
      "filename_prefix": "MIDAS_DEPTH",
      "images": [
        "59",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}
"""

vfi_prompt = """
{
  "7": {
    "inputs": {
      "frame_rate": 10,
      "loop_count": 0,
      "filename_prefix": "AnimateDiff",
      "format": "video/h264-mp4",
      "pix_fmt": "yuv420p",
      "crf": 19,
      "save_metadata": true,
      "pingpong": false,
      "save_output": true,
      "images": [
        "11",
        0
      ]
    },
    "class_type": "VHS_VideoCombine",
    "_meta": {
      "title": "Video Combine 🎥🅥🅗🅢"
    }
  },
  "8": {
    "inputs": {
      "directory": "",
      "image_load_cap": 0,
      "skip_first_images": 0,
      "select_every_nth": 1
    },
    "class_type": "VHS_LoadImagesPath",
    "_meta": {
      "title": "Load Images (Path) 🎥🅥🅗🅢"
    }
  },
  "11": {
    "inputs": {
      "ckpt_name": "rife49.pth",
      "clear_cache_after_n_frames": 10,
      "multiplier": 20,
      "fast_mode": false,
      "ensemble": true,
      "scale_factor": 2,
      "cache_in_fp16": true,
      "frames": [
        "8",
        0
      ]
    },
    "class_type": "RIFE VFI",
    "_meta": {
      "title": "RIFE VFI (recommend rife47 and rife49)"
    }
  }
}
"""

def queue_prompt(prompt):
  p = {"prompt": prompt}
  data = json.dumps(p).encode('utf-8')
  req =  request.Request("http://127.0.0.1:8188/prompt", data=data)
  request.urlopen(req)

def gen_from_360_singlectrl(input_360_file_path, depth_img_path, output_filename, text_prompt, seed, denoising_strength, steps):
  prompt = json.loads(img2img_singlectrl_prompt)
  load_img_node = prompt["49"]["inputs"]
  load_depth_img_node = prompt["66"]["inputs"]
  save_img_node = prompt["19"]["inputs"]
  text_prompt_node = prompt["6"]["inputs"]
  ksampler_node = prompt["57"]["inputs"]
  # update input img
  load_img_node["image"] = input_360_file_path
  # update depth img for controlnet
  load_depth_img_node["image"] = depth_img_path
  # update output file name
  save_img_node["filename_prefix"] = output_filename
  # update text prompt
  text_prompt_node["text"] = text_prompt
  # update denoising strength of base SDXL model
  ksampler_node["denoise"] = denoising_strength
  # update seeds
  ksampler_node["seed"] = seed

  # DEBUG SET STEPS LOW
  ksampler_node["steps"] = steps

  queue_prompt(prompt)

def gen_from_txt2img_doublectrl(depth_img_1_path, depth_img_2_path, controlnet_1_strength, controlnet_2_strength, output_filename, text_prompt, seed, steps):
  prompt = json.loads(img2img_doublectrl_prompt)
  load_img_node = prompt["49"]["inputs"]
  load_depth_img_1_node = prompt["64"]["inputs"]
  load_depth_img_2_node = prompt["66"]["inputs"]
  controlnet_1_node = prompt["63"]["inputs"]
  controlnet_2_node = prompt["67"]["inputs"]
  save_img_node = prompt["19"]["inputs"]
  text_prompt_node = prompt["6"]["inputs"]
  ksampler_node = prompt["57"]["inputs"]

  # update depth img for controlnet
  load_depth_img_1_node["image"] = depth_img_1_path
  load_depth_img_2_node["image"] = depth_img_2_path
  #update controlnet strengths
  controlnet_1_node["strength"] = controlnet_1_strength
  controlnet_2_node["strength"] = controlnet_2_strength
  # update output file name
  save_img_node["filename_prefix"] = output_filename
  # update text prompt
  text_prompt_node["text"] = text_prompt
  # update seeds
  ksampler_node["seed"] = seed

  # DEBUG SET STEPS LOW
  ksampler_node["steps"] = steps

  queue_prompt(prompt)

def gen_from_360_doublectrl(input_360_file_path, depth_img_1_path, depth_img_2_path, controlnet_1_strength, controlnet_2_strength, output_filename, text_prompt, seed, denoising_strength, steps):
  prompt = json.loads(img2img_doublectrl_prompt)
  load_img_node = prompt["49"]["inputs"]
  load_depth_img_1_node = prompt["64"]["inputs"]
  load_depth_img_2_node = prompt["66"]["inputs"]
  controlnet_1_node = prompt["63"]["inputs"]
  controlnet_2_node = prompt["67"]["inputs"]
  save_img_node = prompt["19"]["inputs"]
  text_prompt_node = prompt["6"]["inputs"]
  ksampler_node = prompt["57"]["inputs"]
  # update input img
  load_img_node["image"] = input_360_file_path
  # update depth img for controlnet
  load_depth_img_1_node["image"] = depth_img_1_path
  load_depth_img_2_node["image"] = depth_img_2_path
  #update controlnet strengths
  controlnet_1_node["strength"] = controlnet_1_strength
  controlnet_2_node["strength"] = controlnet_2_strength
  # update output file name
  save_img_node["filename_prefix"] = output_filename
  # update text prompt
  text_prompt_node["text"] = text_prompt
  # update denoising strength of base SDXL model
  ksampler_node["denoise"] = denoising_strength
  # update seeds
  ksampler_node["seed"] = seed

  # DEBUG SET STEPS LOW
  ksampler_node["steps"] = steps

  queue_prompt(prompt)

def get_depth_from_img(input_360_file_path, output_filename):
  prompt = json.loads(midas_depth_prompt)
  load_img_node = prompt["49"]["inputs"]
  save_img_node = prompt["65"]["inputs"]
  # update input img
  load_img_node["image"] = input_360_file_path
  # update output file name
  save_img_node["filename_prefix"] = output_filename

  queue_prompt(prompt)

def gen_video_from_imgs(img_dir, multiplier, framerate, output_filename):
  prompt = json.loads(vfi_prompt)
  load_imgs_node = prompt["8"]["inputs"]
  vfi_node = prompt["11"]["inputs"]
  video_combine_node = prompt["7"]["inputs"]
  load_imgs_node["directory"] = img_dir
  vfi_node["multiplier"] = multiplier
  video_combine_node["filename_prefix"] = output_filename
  video_combine_node["frame_rate"] = framerate
  queue_prompt(prompt)

# gen with SDXL base+refiner
def gen_from_360(input_360_file_path, output_filename, text_prompt, seed, start_step):
  prompt = json.loads(img2img_prompt)
  # update input img
  prompt["49"]["inputs"]["image"] = input_360_file_path
  # update output file name
  prompt["19"]["inputs"]["filename_prefix"] = output_filename
  # update text prompt
  prompt["15"]["inputs"]["text"] = text_prompt
  prompt["6"]["inputs"]["text"] = text_prompt
  # update starting step number of base SDXL model
  prompt["10"]["inputs"]["start_at_step"] = start_step
  # update seeds
  prompt["10"]["inputs"]["noise_seed"] = seed
  prompt["11"]["inputs"]["noise_seed"] = seed

  queue_prompt(prompt)

def inpaint(filename):

  prompt = json.loads(inpaint_api_prompt)
  #set the text prompt for our positive CLIPTextEncode
  # prompt["6"]["inputs"]["text"] = "masterpiece best quality man"

  #set the seed for our KSampler node
  prompt["3"]["inputs"]["seed"] = 5

  # set file
  base_in_dir = 'C:/Users/SREAL/Lab Users/mattg/genai/gen-sys/ComfyUI_windows_portable/ComfyUI/output/'
  base_in_file = 'img2img_00016_cropmerge_filltrans_2.png'
  prompt["20"]["inputs"]["image"] = base_in_dir + filename

  queue_prompt(prompt)