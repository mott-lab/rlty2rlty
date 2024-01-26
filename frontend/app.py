from random import randrange
import time
from flask import Flask, render_template, request
from time import sleep
from os import listdir, mkdir
from os.path import isfile, isdir, join
import shutil
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import re
import os
import glob
import subprocess

import cam_mgr
import comfy_api_wrapper as comfy
import img_processing
import gen_util

app = Flask(__name__)

GEN_SYS_PATH = "C:/Users/SREAL/Lab Users/mattg/genai/gen-sys/"
RICOH_IMG_PATH = GEN_SYS_PATH + "RICOH_img/"
RICOH_RAW_IMG_PATH = RICOH_IMG_PATH + "raw/"
RICOH_RESIZED_IMG_PATH = RICOH_IMG_PATH + "resized/"
COMFYUI_OUTPUT_DIR = GEN_SYS_PATH + "ComfyUI_windows_portable/ComfyUI/output/"
END_IMG = GEN_SYS_PATH + "end_360_img/"
GEN_DIRS = GEN_SYS_PATH + "gen-dirs/"
END_ENV_IMG_PATH = GEN_SYS_PATH + "ENDENV_img/"
END_ENV_RAW_IMG_PATH = END_ENV_IMG_PATH + "raw/"
END_ENV_RESIZED_IMG_PATH = END_ENV_IMG_PATH + "resized/"

# set some global variables to be updated...
Last_gen_dir_full_path = ""
Last_gen_dir_name = ""
Last_gen_num = -1

Last_ricoh_img_name = ""
Last_ricoh_img_full_path = ""

Last_ricoh_resized_img_name = ""
Last_ricoh_resized_img_full_path = ""

End_env_img_file_full_path = ""

End_env_depth_mask = ""

Ricoh_img_depth_mask = ""

Last_img_dir_name = "R0010072"
Last_img_file_full_path = "C:/Users/SREAL/Lab Users/mattg/genai/gen-sys/RICOH_img_raw/resized/R0010072/R0010072_00001_.png"
Last_img_depth_mask = ""

@app.route("/")
def hello():
    runtime = 0
    return render_template("index.html", runtime=runtime)

@app.route("/", methods=["POST", "GET"])
def prompt_in():

    prompt = request.form.getlist('prompt')[0]
    cfg_scale = request.form.getlist('cfg_scale')[0]
    seed = request.form.getlist('seed')[0]
    print(f'{prompt}; scale: {cfg_scale}')
    if prompt == "":
        prompt = "alien lifeforms swirling through outer space, watercolor painting"
    
    # Blocking request...will not take a new prompt until the last one has finished.
    # id_str, runtime = sd_request(prompt, cfg_scale, seed)
    # print(runtime)
    
    # data = {
    #     "id": id_str,
    #     "runtime": str(runtime),
    # }
    # return data

    return render_template("index.html")

@app.route("/input_photo")
def input_photo():
    # take 360 photo
    print("--- taking 360 photo ")

    latest_photo_name, local_ricoh_photo_path = take_360_photo()
    
    img_new_name = resize_local_ricoh_photo(latest_photo_name, local_ricoh_photo_path)

    latest_ricoh_img_dir = prep_resized_photo_for_processing(img_new_name)

def create_depth_mask_for_img(img_basename, img_fullpath):

    img_basename = img_basename[:-4] # remove file extension

    print(f"=== Request depth mask for {img_basename}, full path: {img_fullpath}")
    # check if depth mask already created for last 360 image
    list_depth_masks_for_img = glob.glob(COMFYUI_OUTPUT_DIR + img_basename + "_DEPTH*.png")
    print(list_depth_masks_for_img)

    if len(list_depth_masks_for_img) == 0:
        print("=== Depth mask does not yet exist. Creating...")
        # create depth mask from last 360 image
        comfy.get_depth_from_img(
            img_fullpath,
            img_basename + "_DEPTH",
        )
        # comfyUI is async, wait for depth mask to generate (will be quick)
        list_depth_masks_for_img = glob.glob(COMFYUI_OUTPUT_DIR + img_basename + '_DEPTH*.png')
        while len(list_depth_masks_for_img) < 1:
            print("=== ... waiting for more depth masks based on input image")
            list_depth_masks_for_img = glob.glob(COMFYUI_OUTPUT_DIR + img_basename + '_DEPTH*.png')
            sleep(1)
        print(f"=== Finished creating depth mask: {list_depth_masks_for_img[-1]}")
    else:
        print(f"=== Depth mask already existed: {list_depth_masks_for_img[-1]}")
    return list_depth_masks_for_img[-1]

# click a button, make a genxxxx directory. store dir name. 
# copy last Ricoh image to gen dir. rename
# copy selected environment image to gen dir
# make or take last ghosts, copy to gen dir
# make gen images, move to gen dir
# make gen video

@app.route("/sd_request")
def sd_request():

    with app.app_context():
        return render_template("sd_request.html", runtime=0)
    
    # get most recent gen dir name, number
    gen_dirs = [d for d in listdir(GEN_DIRS) if isdir(join(GEN_DIRS, d))] # get list of gen dirs
    Last_gen_dir_name = gen_dirs[-1] # get last string in list
    Last_gen_num = int(Last_gen_dir_name[-4:]) # cast last four characters to int
    Last_gen_dir_full_path = GEN_DIRS + Last_gen_dir_name
    print(f">> Found last gen dir #{Last_gen_num}: {Last_gen_dir_name}, full path: {Last_gen_dir_full_path}")

    # create new gen(x+1) directory
    Last_gen_num += 1
    Last_gen_dir_name = f"gen{Last_gen_num:04d}"
    Last_gen_dir_full_path = f"{GEN_DIRS + Last_gen_dir_name}"
    print(f">> Create new gen dir: {Last_gen_dir_full_path}")
    os.mkdir(Last_gen_dir_full_path)
    os.mkdir(Last_gen_dir_full_path + "/gen_img/")
    os.mkdir(Last_gen_dir_full_path + "/gen_vid_frames/")
    os.mkdir(Last_gen_dir_full_path + "/gen_vid_frames/base/")
    os.mkdir(Last_gen_dir_full_path + "/gen_vid_frames/upscaled/")
    os.mkdir(Last_gen_dir_full_path + "/input_img/")

    liminal = True

    # get last ricoh photo
    # print(">> Getting last Ricoh image...")
    # list_ricoh_img = [f for f in listdir(RICOH_RAW_IMG_PATH) if isfile(join(RICOH_RAW_IMG_PATH, f))]
    # Last_ricoh_img_name = list_ricoh_img[-1] # get last string in list
    # Last_ricoh_img_full_path = RICOH_RAW_IMG_PATH + Last_ricoh_img_name
    # print(f">> Found last ricoh image: {Last_ricoh_img_name}, full path: {Last_ricoh_img_full_path}")
    
    # # TODO: check if last ricoh has already been resized

    # # Update references to last resized ricoh image
    # Last_ricoh_resized_img_name = resize_local_ricoh_photo(Last_ricoh_img_name, Last_ricoh_img_full_path)
    # Last_ricoh_resized_img_full_path = RICOH_RESIZED_IMG_PATH + Last_ricoh_resized_img_name

    # # copy last resized ricoh image into new gen dir
    # print(">> Copy resized ricoh photo into gen dir...")
    # Last_ricoh_resized_img_full_path = shutil.copy(Last_ricoh_resized_img_full_path, Last_gen_dir_full_path)

    # first image
    start_img_file_full_path = END_ENV_RAW_IMG_PATH + "home-office.png"
    start_img_name = os.path.basename(start_img_file_full_path)
    # resize start environment image
    Last_ricoh_resized_img_name = resize_end_env_img(start_img_name, start_img_file_full_path)
    Last_ricoh_resized_img_full_path = END_ENV_RESIZED_IMG_PATH + Last_ricoh_resized_img_name
    # copy resized end env image into new gen dir
    print(">> Copy resized end environment image into gen dir...")
    Last_ricoh_resized_img_full_path = shutil.copy(Last_ricoh_resized_img_full_path, Last_gen_dir_full_path)

    # get end environment image
    end_img_file_full_path = END_ENV_RAW_IMG_PATH + "nature-path-1.png"
    end_img_name = os.path.basename(end_img_file_full_path)
    # resize end environment image
    end_env_img_name = resize_end_env_img(end_img_name, end_img_file_full_path)
    End_env_img_file_full_path = END_ENV_RESIZED_IMG_PATH + end_env_img_name
    # copy resized end env image into new gen dir
    print(">> Copy resized end environment image into gen dir...")
    End_env_img_file_full_path = shutil.copy(End_env_img_file_full_path, Last_gen_dir_full_path)

    print(">> Create depth mask for ricoh image...")
    Ricoh_img_depth_mask = create_depth_mask_for_img(Last_ricoh_resized_img_name, Last_ricoh_resized_img_full_path)
    Ricoh_img_depth_mask = shutil.copy(Ricoh_img_depth_mask, Last_gen_dir_full_path)

    print(">> Create depth mask for end environment image...")
    End_env_depth_mask = create_depth_mask_for_img(end_env_img_name, End_env_img_file_full_path)
    End_env_depth_mask = shutil.copy(End_env_depth_mask, Last_gen_dir_full_path)

    seed = 1011
    steps = 22

    # prompt = "a sci-fi room with a portal to another dimension"
    # prompt = "nature scene, forest with a waterfall and a river, calming, soothing, beautiful, serene"
    # prompt = "serene, tranquil, meditative scene at sunrise, peaceful Zen garden with smooth stones, a gentle stream, and blossoming cherry trees, soft morning light filters through the foliage, faint mist rising from grass, soft and pastel color palette, gentle pinks greens and warm gold"
    # prompt = "mesmerizing, tranquil, galactic scene, cosmos with swirling nebulas, twinkling stars, distant galaxies in a spectrum of vibrant colors, soft ethereal glow, deep blues, purples, glittering silver of distant stars"
    # prompt = "serene, tranquil, ethereal meditative scene in a sky of billowing undulating clouds, sunrise, warm palette of pastel pinks, oranges, light blues and purples"
    # prompt = "forest scene with a waterfall and a river, green pastures, beautiful, serene"
    prompt = "a vibrant and tranquil landscape, lush green meadow, various trees in full bloom, white picket fence alongside a dirt path, clear blue sky with fluffy clouds, distant hills"
    prompt += ", panoramic, (360 view:1.3)" #, (360-degree:1.3), wide-angle lens"

    gen_steps = 25 # not needed, probably. default in comfy api call.
    denoising_strength_arr = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    if liminal:
        '''
        # +++ Gen for start image
        '''
        comfy_output_basename = Last_gen_dir_name + "_00"

        # generate 10 images with gradually increasing denoising strength, based on most ricoh image
        for i in range(0, len(denoising_strength_arr)):
            print(f"+++ [RICOH] queueing prompt with denoise set to {denoising_strength_arr[i]}")
            comfy.gen_from_360_singlectrl(
                Last_ricoh_resized_img_full_path, 
                Ricoh_img_depth_mask,
                comfy_output_basename, 
                prompt, 
                seed, 
                denoising_strength_arr[i],
                steps
            )

        # comfyUI is async, need to wait for all images to finish generating
        comfy_output = COMFYUI_OUTPUT_DIR + comfy_output_basename
        list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
        len_list_last_checked = 0
        while len(list_gen_from_ricoh_img) < len(denoising_strength_arr):
            list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
            len_list_current = len(list_gen_from_ricoh_img)
            if len_list_current != len_list_last_checked:
                print(f"+++ [RICOH] ... generated {len_list_current}/{len(denoising_strength_arr)} based on ricoh image")
            len_list_last_checked = len_list_current
            sleep(1)

        print(f"+++ [RICOH] {len(list_gen_from_ricoh_img)}/{len(denoising_strength_arr)} Completed generation. ")
        print(f">> Moving generated images to {Last_gen_dir_name}")
        # move ricoh images from comfyUI path to project path
        for f in list_gen_from_ricoh_img:
            img_name = os.path.basename(f)
            print(f">> [RICOH] moving {img_name} to {Last_gen_dir_name}")
            os.rename(f, Last_gen_dir_full_path + "/gen_img/" + img_name)

        '''
        # +++ Gen for end environment image
        '''
        comfy_output_basename = Last_gen_dir_name + "_03"

        # generate 10 images with gradually decreasing denoising strength, based on end env image
        for i in range(len(denoising_strength_arr) - 1, -1, -1):
            print(f"+++ [ENDENV] queueing prompt with denoise set to {denoising_strength_arr[i]}")
            comfy.gen_from_360_singlectrl(
                End_env_img_file_full_path, 
                End_env_depth_mask,
                comfy_output_basename, 
                prompt, 
                seed, 
                denoising_strength_arr[i],
                steps
            )

        # comfyUI is async, need to wait for all images to finish generating
        comfy_output = COMFYUI_OUTPUT_DIR + comfy_output_basename
        list_gen_from_end_env_img = glob.glob(comfy_output + '*.png')
        len_list_last_checked = 0
        while len(list_gen_from_end_env_img) < (len(denoising_strength_arr)):
            list_gen_from_end_env_img = glob.glob(comfy_output + '*.png')
            len_list_current = len(list_gen_from_end_env_img)
            if len_list_current != len_list_last_checked:
                print(f"+++ [ENDENV] ... generated {len_list_current}/{len(denoising_strength_arr)} based on end environment image")
            len_list_last_checked = len_list_current
            sleep(1)

        print(f"+++ [ENDENV] {len(list_gen_from_end_env_img)}/{len(denoising_strength_arr)} Completed generation.")
        print(f">> Moving generated images to {Last_gen_dir_name}")
        # move endenv images from comfyUI path to project path
        for f in list_gen_from_end_env_img:
            img_name = os.path.basename(f)
            print(f">> [ENDENV] moving {img_name} to {Last_gen_dir_name}")
            os.rename(f, Last_gen_dir_full_path + "/gen_img/" + img_name)

        '''
        # +++ Gen for liminal gen between ricoh gen image and end environment gen image
        '''
        comfy_output_basename = Last_gen_dir_name + "_02"

        # generate images gradually shifting controlnet weight from ricoh image to end env image
        ctrl_weight_1 = 1.0
        ctrl_weight_2 = 0.0
        num_liminal_gen = 0
        while ctrl_weight_1 >= 0.0:
            print(f"+++ [LIMINAL] queueing double ctrl with ctrl 1: {ctrl_weight_1}, ctrl 2: {ctrl_weight_2}")
            comfy.gen_from_txt2img_doublectrl(
                Ricoh_img_depth_mask, 
                End_env_depth_mask,
                ctrl_weight_1,
                ctrl_weight_2,
                comfy_output_basename, 
                prompt, 
                seed,
                steps
            )
            ctrl_weight_1 -= 0.05
            ctrl_weight_2 += 0.05
            num_liminal_gen += 1

        # comfyUI is async, need to wait for all images to finish generating
        comfy_output = COMFYUI_OUTPUT_DIR + comfy_output_basename
        list_liminal_gen = glob.glob(comfy_output + '*.png')
        len_list_last_checked = 0
        while len(list_liminal_gen) < num_liminal_gen:
            list_liminal_gen = glob.glob(comfy_output + '*.png')
            len_list_current = len(list_liminal_gen)
            if len_list_current != len_list_last_checked:
                print(f"+++ [LIMINAL] ... generated {len_list_current}/{num_liminal_gen} based on ricoh and end env depth masks")
            len_list_last_checked = len_list_current
            sleep(1)

        print(f"+++ [LIMINAL] {len(list_liminal_gen)}/{num_liminal_gen} Completed generation.")

        print(f">> Moving generated images to {Last_gen_dir_name}")
        # move endenv images from comfyUI path to project path
        for f in list_liminal_gen:
            img_name = os.path.basename(f)
            print(f">> [LIMINAL] moving {img_name} to {Last_gen_dir_name}")
            os.rename(f, Last_gen_dir_full_path + "/gen_img/" + img_name)

        print(f">> Copy starter images to /gen_img/ and rename")
        ricoh_copy = shutil.copy(Last_ricoh_resized_img_full_path, Last_gen_dir_full_path + "/gen_img/")
        end_copy = shutil.copy(End_env_img_file_full_path, Last_gen_dir_full_path + "/gen_img/")
        os.rename(ricoh_copy, Last_gen_dir_full_path + "/gen_img/" + Last_gen_dir_name + "_00_00000_.png")
        os.rename(end_copy, Last_gen_dir_full_path + "/gen_img/" + Last_gen_dir_name + "_03_00012_.png")

        print(f"+++ [VIDEO] Generate video from files in /gen_img/{Last_gen_dir_name}")

        comfy.gen_video_from_imgs(
            Last_gen_dir_full_path + "/gen_img/",
            20,
            10,
            Last_gen_dir_name
        )

    
    else:
        start_img = shutil.move(Last_ricoh_resized_img_full_path, Last_gen_dir_full_path + "/input_img/img_1.png")
        end_img = shutil.move(End_env_img_file_full_path, Last_gen_dir_full_path + "/input_img/img_2.png")
        
        comfy.gen_video_from_imgs(
            Last_gen_dir_full_path + "/input_img/",
            300,
            10,
            Last_gen_dir_name
        )

    print("+++ [VIDEO] Waiting for video frame interpolation to complete...")
    sleep(45)
    
    comfy_output = COMFYUI_OUTPUT_DIR + Last_gen_dir_name
    list_video_gen = glob.glob(comfy_output + '*.mp4')
    while len(list_video_gen) < 1:
        # print(f"+++ [VIDEO] ... waiting for video to finish")
        list_video_gen = glob.glob(comfy_output + '*.mp4')
        sleep(1)
    
    print(f"+++ [VIDEO] ... preparing to move video file")
    sleep(10)
    
    vid_file = list_video_gen[0]
    print(f"+++ Finished generating video. Moving {vid_file} to: {Last_gen_dir_full_path}")
    gen_video_file = shutil.move(vid_file, Last_gen_dir_full_path) # TODO: Use shutil.move() for all file moves instead of os.rename()
    # vid_name = os.path.basename(vid_file)
    # os.rename(vid_file, Last_gen_dir_full_path + vid_name)
    # vid_file = Last_gen_dir_full_path + vid_name

    print(f">> Extracting frames from video {gen_video_file}...")
    ffmpeg_extract_frames_cmd = f"ffmpeg -i \"{gen_video_file}\" -qscale:v 1 -qmin 1 -qmax 1 \"{Last_gen_dir_full_path}/gen_vid_frames/base/frame%08d.png\""
    ffmpeg_proc = subprocess.Popen(ffmpeg_extract_frames_cmd)
    ffmpeg_proc.wait()
    print(">> Finished extracting frames with ffmpeg.")

    print(">> Upscaling video frames with ESRGAN. This will take a while.")
    realesrgan_path = "C:/Users/SREAL/Lab Users/mattg/wares/Real-ESRGAN/realesrgan-ncnn-vulkan-20220424-windows"
    realesrgan_cmd = f"\"{realesrgan_path}/realesrgan-ncnn-vulkan.exe\" -i \"{Last_gen_dir_full_path}/gen_vid_frames/base/\" -o \"{Last_gen_dir_full_path}/gen_vid_frames/upscaled/\" -n realesr-animevideov3 -s 4 -f png"
    realesrgan_proc = subprocess.Popen(realesrgan_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    realesrgan_proc.wait()
    print(">> Finished upscaling frames with ESRGAN.")

    print(">> Combining upscaled frames back into a video...")
    frame_still_duration = 0.05
    xfade_duration = 0.05
    w = 5760
    h = 2880
    ffmpeg_combine_frames_cmd = (f"ffmpeg "
                                f"-framerate 10 "
                                f"-i \"{Last_gen_dir_full_path}/gen_vid_frames/upscaled/frame%08d.png\" "
                                f"-vf "
                                f"zoompan=d={(frame_still_duration + xfade_duration) / xfade_duration}:s={w}x{h}:fps={1.0 / xfade_duration},"
                                f"framerate=60:interp_start=0:interp_end=255:scene=100 "
                                f"-c:v hevc_nvenc -r 60 -pix_fmt yuv420p "
                                f"\"{Last_gen_dir_full_path}/{Last_gen_dir_name}_trans_vid.mp4\"")

    ffmpeg_combine_proc = subprocess.Popen(ffmpeg_combine_frames_cmd)
    ffmpeg_combine_proc.wait()
    print(">> Finished combining upscaled frames into video.")

    print(">> Removing gen_vid_frames folder.")
    shutil.rmtree(f"{Last_gen_dir_full_path}/gen_vid_frames/")

    print(">> Injecting spatial media metadata into video.")
    spatial_metadata_injector_path = "C:\\Users\\SREAL\\Lab Users\\mattg\\genai\\gen-sys\\frontend\\spatial-media-injector\\spatial-media\\spatialmedia"
    vid_path = f"{Last_gen_dir_full_path}/{Last_gen_dir_name}_trans_vid.mp4"
    injected_vid_path = f"{Last_gen_dir_full_path}/{Last_gen_dir_name}_trans_vid_spatial.mp4"
    inject_cmd = f"python \"{spatial_metadata_injector_path}\" -i --stereo=none \"{vid_path}\" \"{injected_vid_path}\""
    inject_proc = subprocess.Popen(inject_cmd)
    inject_proc.wait()

    print(">> Done.")

    
   

    return render_template("sd_request.html")

def take_360_photo():
    latest_photo_url = cam_mgr.get_state()
    old_photo_url = latest_photo_url
    # take 360 photo
    cam_mgr.take_pic()
    latest_photo_url = cam_mgr.get_state()
    
    # wait for ricoh camera to process the new photo
    while latest_photo_url == old_photo_url or latest_photo_url == "":
        print("-- Waiting for new photo...")
        sleep(2)
        latest_photo_url = cam_mgr.get_state()
    
    latest_photo_name = re.split("/", latest_photo_url)[-1]
    print("Latest photo: " + latest_photo_name)
    
    # retrieve photo from ricoh camera
    photo_raw = cam_mgr.get_photo(latest_photo_url)

    local_ricoh_photo_path = RICOH_IMG_PATH + latest_photo_name

    # save_path += latest_photo_name
    with open(local_ricoh_photo_path, "wb") as f:
        photo_raw.decode_content = True
        shutil.copyfileobj(photo_raw, f)
        
    print("-- Finished saving: " + local_ricoh_photo_path)

    return latest_photo_name, local_ricoh_photo_path

def resize_img(img_path, save_path):
    print("-- Resizing image...")
    img = Image.open(img_path)
    print(f"-- Original size : {img.size}") # 5464x3640
    img_resized = img.resize((1440, 720)) # scale image down for SD img2img
    img_new_path = img_path[:-4] + "_resized" + img_path[-4:]
    img_new_path = save_path + "/" + os.path.basename(img_new_path)
    img_resized.save(img_new_path)
    return img_new_path

def resize_local_ricoh_photo(latest_photo_name, local_ricoh_photo_path):
    # Resize image
    print("-- Resizing image...")
    image = Image.open(local_ricoh_photo_path)
    print(f"-- Original size : {image.size}") # 5464x3640
    img_resized = image.resize((1440, 720)) # scale image down for SD img2img
    print(f"-- New size : {img_resized.size}")
    img_new_name = latest_photo_name[:-4] + "_resized.jpg"
    img_resized.save(RICOH_RESIZED_IMG_PATH + img_new_name)
    print(f"-- Finished resizing image. Saved: {RICOH_RESIZED_IMG_PATH + img_new_name}")
    image.close()
    return img_new_name

def resize_end_env_img(img_name, img_full_path):
    # Resize image
    print("-- Resizing image...")
    image = Image.open(img_full_path)
    print(f"-- Original size : {image.size}") # 5464x3640
    img_resized = image.resize((1440, 720)) # scale image down for SD img2img
    print(f"-- New size : {img_resized.size}")
    img_new_name = img_name[:-4] + "_resized" + img_full_path[-4:]
    img_resized.save(END_ENV_RESIZED_IMG_PATH + img_new_name)
    print(f"-- Finished resizing image. Saved: {END_ENV_RESIZED_IMG_PATH + img_new_name}")
    image.close()
    return img_new_name

def prep_resized_photo_for_processing(img_new_name):
    ricoh_img_name = img_new_name[:-4]
    latest_ricoh_img_dir = RICOH_RESIZED_IMG_PATH + ricoh_img_name

    mkdir(latest_ricoh_img_dir)
    shutil.copy(RICOH_RESIZED_IMG_PATH + ricoh_img_name, latest_ricoh_img_dir)
    os.rename(latest_ricoh_img_dir + ricoh_img_name + '.jpg', latest_ricoh_img_dir + ricoh_img_name + '_0.jpg')
    return latest_ricoh_img_dir

#############################
# TEST
#############################
# sd_request()

def sd_request_webui(prompt, cfg_scale, seed):

    start_time = time.time()
    print(f"- T={start_time}: Received SD gen request with following data:")
    print(f"-- prompt: {prompt}")
    print(f"-- cfg_scale: {cfg_scale}")
    print(f"-- seed: {seed}")

    # Look for most recent captured photo
    input_img_path = "C:\\Users\\SREAL\\Lab Users\\mattg\\genai\\gen-sys\\input_img\\resized\\"
    input_img_files = [f for f in listdir(input_img_path) if isfile(join(input_img_path, f))]
    # Wait for a file to be input
    while len(input_img_files) == 0:
        print("-- No input image files found. Waiting...")
        sleep(1)
    last_img_file_name = input_img_files.pop() # O(1)
    print(f"-- Found last input image file: {last_img_file_name}")
    last_img_full_path = input_img_path + last_img_file_name

    # Look at most recent directory generated/output
    output_img_path = "C:/Users/SREAL/Lab Users/mattg/genai/gen-sys/output_img/"
    output_img_prod_path = output_img_path + "prod/"
    output_img_dirs = [f for f in listdir(output_img_prod_path) if isdir(join(output_img_prod_path, f))]
    # If first output img, output_img_path is simple assignment
    if len(output_img_dirs) == 0:
        print("-- Creating first image output directory...")
        output_img_path = output_img_path + last_img_file_name[:-4]
    # If not...
    else:
        last_img_dir_name = output_img_dirs.pop() # O(1)
        print(f"-- Last output image directory: {last_img_dir_name}")
        # Check if last output dir is input dir name
        if last_img_file_name[:-4] == last_img_dir_name:
            print("--- [CAM LAG] A directory for this image already exists. This means the camera has not captured another photo by the time we are attempting to generate a new set of images.")
            print("--- [CAM LAG] Creating a new directory...")
            output_img_path = output_img_path + last_img_file_name[:-4] + "1"
        # Else, check if last output dir contains input dir name
        elif last_img_file_name[:-4] in last_img_dir_name:
            print("--- [CAM LAG] A directory for this image already exists. This means the camera has not captured another photo by the time we are attempting to generate a new set of images.")
            print("--- [CAM LAG] Creating a new directory...")
            # If so, increment output dir name
            last_char = last_img_dir_name[-1]
            new_suffix = int(last_char) + 1
            output_img_path = output_img_path + last_img_file_name[:-4] + str(new_suffix)
        else:
            output_img_path = output_img_path + last_img_file_name[:-4]

    if not isdir(output_img_path):
        print("-- Creating directory for generated images...")
        mkdir(output_img_path)

    with open("log.tsv", "a") as logfile:
        log_str = "\n" + output_img_prod_path + last_img_file_name[:-4] + "\t" + \
            prompt + "\t" + cfg_scale + "\t" + seed
        logfile.write(log_str)
            
    # # check if outdir already exists
    # if isdir(output_img_path):
        
    #     last_char = output_img_path[-1]
    #     if last_char.isnumeric():
    #         new_suffix = int(last_char) + 1
    #     else:
    #         new_suffix = 1
    #     output_img_path = output_img_path + str(new_suffix)
    #     mkdir(output_img_path)

    url = "http://127.0.0.1:7860"

    gen_request = {
        "init_images": [
            last_img_full_path
        ],
    #   "resize_mode": 0,
        "denoising_strength": 0.3,
    #   "image_cfg_scale": 0,
    #   "mask": "string",
    #   "mask_blur": 4,
    #   "inpainting_fill": 0,
    #   "inpaint_full_res": True,
    #   "inpaint_full_res_padding": 0,
    #   "inpainting_mask_invert": 0,
    #   "initial_noise_multiplier": 0,
        "prompt": "cyberpunk office interior in the year 3000, aliens in space suits, oil painting",
    #   "styles": [
    #     "string"
    #   ],
        "seed": 42,
    #   "subseed": -1,
    #   "subseed_strength": 0,
    #   "seed_resize_from_h": -1,
    #   "seed_resize_from_w": -1,
    #   "sampler_name": "Euler",
    #   "batch_size": 1,
    #   "n_iter": 1,
        "steps": 20,
        "cfg_scale": 7,
        "width": 960,
        "height": 480,
    #   "restore_faces": False,
    #   "tiling": False,
    #   "do_not_save_samples": False,
    #   "do_not_save_grid": False,
        "negative_prompt": "low quality",
    #   "eta": 0,
    #   "s_churn": 0,
    #   "s_tmax": 0,
    #   "s_tmin": 0,
    #   "s_noise": 1,
    #   "override_settings": {},
    #   "override_settings_restore_afterwards": True,
    #   "script_args": [],
    #   "sampler_index": "Euler",
    #   "include_init_images": False,
    #   "script_name": "string",
    #   "send_images": True,
    #   "save_images": False,
    #   "alwayson_scripts": {}
    }

    # Open photo
    # encoded = base64.b64encode(open("C:\\Users\\SREAL\\Lab Users\\mattg\\genai\\gen-sys\\input_img\\R0010039_resized.jpg", "rb").read())
    encoded = base64.b64encode(open(last_img_full_path, "rb").read())
    encoded_str = str(encoded, encoding="utf-8")
    encoded_data = "data:image/png;base64," + encoded_str

    num_imgs = 12

    for i in range(0, num_imgs):

        denoise = i / num_imgs

        gen_request = {
            "init_images": [
                encoded_data
            ],
            "denoising_strength": denoise,
            "prompt": prompt,
            "seed": seed,
            "steps": 50,
            "cfg_scale": cfg_scale,
            "width": 960,
            "height": 480,
            "negative_prompt": "low quality",
        }

        print(f"-- Posting request {i + 1} of {num_imgs} to Stable Diffusion WEBUI API...")
        response = requests.post(url=f'{url}/sdapi/v1/img2img', json=gen_request)

        r = response.json()

        print("-- Parsing response from SD WEBUI API...")
        for img in r['images']:
            image = Image.open(io.BytesIO(base64.b64decode(img.split(",",1)[0])))

            png_payload = {
                "image": "data:image/png;base64," + img
            }
            print("--- Retrieving image from SD WEBUI...")
            response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("parameters", response2.json().get("info"))
            output_img_fullpath = output_img_path + "/" + f"{i:05d}.png"
            print(f"--- Saving gen img {i:05d}.png in {output_img_path}")
            image.save(output_img_fullpath, pnginfo=pnginfo)

        # encoded = base64.b64encode(open(output_img_fullpath, "rb").read())
        # encoded_str = str(encoded, encoding="utf-8")
        # encoded_data = "data:image/png;base64," + encoded_str

        # upscale_request = {
        #     "init_images": [
        #         encoded_data
        #     ],
        #     "script_name": "SD upscale",
        #     "script_args" : 
        #     # [
        #     # "",512,0,8,32,64,0.275,32,3,False,0,True,8,3,2,1080,1440,1.875
        #     # ],
        #     [
        #         "", 20, "ESRGAN_4x", 2
        #     ]
        # }

        # response = requests.post(url=f'{url}/sdapi/v1/img2img', json=upscale_request)

        # r = response.json()

        # print("-- Parsing response from SD WEBUI API...")
        # for img in r['images']:
        #     image = Image.open(io.BytesIO(base64.b64decode(img.split(",",1)[0])))

        #     png_payload = {
        #         "image": "data:image/png;base64," + img
        #     }
        #     print("--- Retrieving image from SD WEBUI...")
        #     response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

        #     pnginfo = PngImagePlugin.PngInfo()
        #     pnginfo.add_text("parameters", response2.json().get("info"))
        #     output_img_fullpath = output_img_path + "/" + f"up{i:05d}.png"
        #     print(f"--- Saving gen img {i:05d}.png in {output_img_path}")
        #     image.save(output_img_fullpath, pnginfo=pnginfo)

        stars = 42 if (i + 1) < num_imgs else 43
        print("\n" + "*" * stars)
        print(f"*** COMPLETED GENERATING IMAGE {i+1} of {num_imgs} ***")
        print("*" * stars + "\n")

    end_time = time.time()
    total_time = end_time - start_time

    print(f"-- T={end_time}: Completed image generation. Moving them into prod folder for display.")
    shutil.move(output_img_path, output_img_prod_path)
    return output_img_path, total_time