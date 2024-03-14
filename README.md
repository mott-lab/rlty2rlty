***this repo is currently under construction**

# rlty2rlty

This project creates 360-degree videos that transition between two 360-degree images.
The transition optionally passes through a liminal space generated by AI.
The extended abstract describing this system will be published in the proceedings of the IEEE VR 2024 conference.
You can access a pre-print of the paper at the following link: https://TODO.
The project demo video is available at the following link: https://www.youtube.com/watch?v=u4CyvdE3Y3g.

Examples of transitions generated with this repo that you can view on a VR headset:
- https://www.youtube.com/watch?v=cjMZkDDk20o
- https://www.youtube.com/watch?v=dRojiAOyM7k
- https://www.youtube.com/watch?v=kEyZLqNOilc
- https://www.youtube.com/watch?v=ZkDDoRO-DnE


This repo provides a browser-based interface for generating transitions between two arbitrary environments captured in 360-degree images.
It currently uses Stable Diffusion XL 1.0.
I plan to configure it to use Stable Diffusion 3 / Stable Cascade soon.


If you want to use/edit the ComfyUI workflows in your own instance of ComfyUI, the `comfyui_workflows` folder contains the workflow.json files that created the API versions called in the Python files.

## Dependencies

TODO: insert links

- ComfyUI (I use the standalone installation version)
- Python (I am using 3.11, but should work with any Python 3)
- Flask
- FFmpeg. Needs to be added to your path environment variable.

## Installation and Configuration

TODO: look into any instructions for the spatial-media-injector git submodule.

1. Clone this repo.
From the command line: `git clone https://github.com/mott-lab/rlty2rlty`
Or, download the repo as a .zip (by clicking the green button above) and extract it.

2. Install ComfyUI.

3. Configure global variables in the `app.py` Python script.
    - `COMFYUI_OUTPUT_DIR` should be set to the location that ComfyUI saves images. For me this is `ComfyUI_windows_portable/ComfyUI/output/` which I have in the same directory as the `rlty2rlty` repo. You can leave this variable unchanged if you have the same setup.s

3. Add any 360 images you want to experiment with in the `ENDENV_img/raw/` directory.
There are some example images in there already.
They should have a 2:1 aspect ratio, but they can be any resolution.
The program will automatically resize them to the proper size for processing and copy them into the `ENDENV_img/resized/` directory.

## Running

TODO: consider what should happen if user does not enter anything as a liminal prompt. LLM-generated? I guess not since that would require a GPT key... Skip liminal space?

1. Run the front-end web interface. 
Open a command line interface in the `frontend` directory and enter the command `flask run`.

2. Run the ComfyUI instance. For me, this is double-clicking the `run-nvidia-gpu.bat` program in the folder I installed it.

3. Open a web broswer and navigate to http://127.0.0.1:5000. 

4. Select the starting environment where you would like the transition video to start, and the ending environment where you would like the transition video to end up.

5. Enter a prompt for the liminal space you would like the transition video to pass through.

6. Click the `generate transition` button. 
You can observe the progress of the generation process in the command line interfaces for the rlty2rlty program and the ComfyUI program.

7. The transition video will be output in latest directory created in the `gen-dirs` directory.

## rlty2rlty Process

This section describes how the rlty2rlty transition process works.

### Image Generation Approach

The rlty2rlty system creates transition videos through multiples series of images generated based on the input 360° images of the starting environment and ending environment, as well as the user text prompt describing a liminal space.
It primarily uses the following techniques to achieve this:
- Stable Diffusion image-to-image mode
- LORA trained on 360° images
- MiDaS depth estimator
- Depth T2I-Adapter

#### Stable Diffusion img2img
The denoising strength parameters affords generating unique images based on an input image while controlling how much influence the input image has on the output.

#### LoRA

#### MiDaS Depth Estimator

#### Depth T2I-Adapter

### Transition Construction


### Limtations and Future Work

rlty2rlty is a proof-of-concept prototype designed to demonstrate using AI to generate visual transitions between two arbitrary environments without any prior knowledge of either environment.
Perhaps the most apparent limitation of this work is that it creates 360° videos, and it does not transition the meshes and textures of the 3D objects in the scene themselves.
With the rapidly developing research on neural rendering and 3D model generation, it is possible that this rlty2rlty system could be used without much alteration to generate 3D scene transitions in the near future.
In the shorter term, one solution could use a compute shader to generate approximate scene meshes based on depth images generated for each transition image, and then use a fragment shader to color the mesh based on the transition image.
I am currently working on this approach and would welcome a collaborator if you are interested in this project.


The AI system also uses a
% In image-to-image mode, in addition to the AI system takes a text prompt and an image as inputs, as well as a 
\emph{denoising strength} parameter to control the influence of the text versus the image: 
% when generating the image.
% Lower denoising strength values mean that the generator mostly bases its output on the input image; 
% Higher denoising strength 
higher values produce images visually closer to the text prompt than the base image.
Our system uses two techniques to ensure that the generated images conform to the visual structure of equirectangular 360\textdegree{} images and display properly on MR HWDs.
First, the system uses a low-rank adaptation (LoRA) layer trained on equirectangular 360\textdegree{} images to provide the general visual structure~\cite{hu2021lora}.
% \footnote{\url{https://huggingface.co/artificialguybr/360Redmond}}.
The system also creates a depth mask for the input images using the MiDaS monocular depth estimator~\cite{ranftl2020towards}, which is then used by a T2I-Adapter~\cite{mou2023t2i} to provide additional spatial conditioning to the generated image.


\paragraph{Transition Construction}

The system generates the transition in three phases.
In the \emph{start phase}, it generates a series of images based on the \se{} image that gradually increase the denoising strength while fixing the weight of the T2I-Adapter control for the \se{} image's depth mask to its maximum and setting the weight of the \ee{} image's depth mask adapter to zero.
In the \emph{liminal phase}, it generates a series of images using Stable Diffusion's text-to-image mode (i.e., without basing the images on either the \se{} or \ee{} image) that begins with the \se{} image's depth mask adapter maxed out and the \ee{} image's adapter at zero. 
The generations in this series increase the \se{} image's depth mask adapter and decrease the \ee{} image's adapter by the same amount each step.
In the \emph{end phase}, it inverts the \emph{start phase} using the \ee{} input image as its base, with maximizing the \ee{} image's depth mask adapter while zeroing out the \se{} input image's adapter.
Once all images are generated, the system smooths the transition by inserting additional frames using real-time intermediate flow estimation (RIFE),
% , a video frame interpolation model, 
a model designed to interpolate motion between consecutive images~\cite{huang2022real}.
All frames are then assembled in order and displayed on an MR HWD.

The visual effect in the \emph{start phase} is that images gradually become more like the AI's most intense application of the text prompt while maintaining the depth and visual structure of the \se{}. 
In the \emph{liminal phase}, the images are all intense applications of the text prompt while gradually switching the structure of the environment from the \se{} to match the \ee{} image.
The \emph{end phase} is an inverse of the \emph{start phase}, where the environment morphs from the liminal space to the \ee{} with visual structure guidance from the \ee{}.

\paragraph{Future Work}

First, we intend to evaluate how these transition techniques affect users' presence, attention, and task performance at different points in a transition between two environments.
% the transition video plays linearly and does not allow the user to edit it apart from the initial liminal text prompt.
% However, when transitioning, a user may want to spend additional time exploring a liminal space.
% Future work could 
From a system perspective, future work could explore ways to allow more user interaction, e.g., to support pausing the transition while the system generates additional scenes in the event the user wants to spend more time exploring an interesting liminal space.
Additionally, users may want to control factors of the transition, e.g., how fast different phases occur, through the text prompt.
Last, future work could use AI to classify objects in each image to generate transitions based on scene semantics, or transition scene meshes and textures.