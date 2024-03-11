from random import randrange
import time
from flask import Flask, render_template, request, send_from_directory, jsonify
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

current_directory = os.getcwd()
# current_directory = current_directory.replace('\\', '/').replace(' ', '\\ ')
parent_directory = os.path.dirname(current_directory)

GEN_SYS_PATH = parent_directory + "/" # parent directory will be rlty2rlty folder
RICOH_IMG_PATH = GEN_SYS_PATH + "RICOH_img/"
RICOH_RAW_IMG_PATH = RICOH_IMG_PATH + "raw/"
RICOH_RESIZED_IMG_PATH = RICOH_IMG_PATH + "resized/"
END_IMG = GEN_SYS_PATH + "end_360_img/"
GEN_DIRS = GEN_SYS_PATH + "gen-dirs/"
END_ENV_IMG_PATH = GEN_SYS_PATH + "ENDENV_img/"
END_ENV_RAW_IMG_PATH = END_ENV_IMG_PATH + "raw/"
END_ENV_RESIZED_IMG_PATH = END_ENV_IMG_PATH + "resized/"

# This line needs to point to the location of your ComfyUI install.
# Current line can be left if ComfyUI is in the parent directory of rlty2rlty folder.
COMFYUI_DIR = os.path.dirname(parent_directory) + "/ComfyUI_windows_portable/"
print(COMFYUI_DIR)

# This line needs to point to the location of your ComfyUI install's output directory.
# It can be left alone if you the ComfyUI output folder is in its default location.
COMFYUI_OUTPUT_DIR = COMFYUI_DIR + "ComfyUI/output/"

# Start a ComfyUI instance on program startup.
# subprocess.run(f'start run_nvidia_gpu.bat', shell=True, cwd=COMFYUI_DIR)

# If you want to open generated video files on a networked computer,
# e.g., to display them in a Unity project running on a different computer,
# change this path to the network-shared folder location.
NETWORK_DRIVE_GEN_PATH = "//192.168.1.227/rlty2rlty/gen-dirs/"


# This function is called when page is loaded by browser.
# Initialize some variables in index.js
@app.route("/")
def hello():
    list_end_env_img = [f for f in listdir(END_ENV_RAW_IMG_PATH) if isfile(join(END_ENV_RAW_IMG_PATH, f))]
    data = { 
        'end_img_list' : list_end_env_img, 
        'end_img_path' : END_ENV_IMG_PATH
    }
    runtime = 0
    return render_template("index.html", data=data)

# Route to serve files back to js/html frontend
@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(END_ENV_RESIZED_IMG_PATH, filename)

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
    print(COMFYUI_OUTPUT_DIR + img_basename)
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

# This function is called on POST from index.html / index.js
@app.route("/sd_request", methods=["POST", "GET"])
def sd_request():

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

    # get transition prompt data from request
    prompt = request.form.getlist('prompt')[0]
    title = request.form.getlist('title')[0]
    start_img = request.form.getlist('start_img')[0]
    end_img = request.form.getlist('end_img')[0]
    cfg_scale = request.form.getlist('cfg_scale')[0] # not currently editable by user
    seed = request.form.getlist('seed')[0] # not currently editable by user
    
    seed = 10111
    steps = 20

    # TODO: pass this in from frontend
    liminal_method = 1

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
    # start_img_file_full_path = END_ENV_RAW_IMG_PATH + "interactive-game.png"
    start_img_file_full_path = END_ENV_RAW_IMG_PATH + start_img
    start_img_name = os.path.basename(start_img_file_full_path)
    # resize start environment image
    Start_env_resized_img_name = resize_end_env_img(start_img_name, start_img_file_full_path)
    Start_env_resized_img_full_path = END_ENV_RESIZED_IMG_PATH + Start_env_resized_img_name
    # copy resized end env image into new gen dir
    print(">> Copy resized end environment image into gen dir...")
    Start_env_resized_img_full_path = shutil.copy(Start_env_resized_img_full_path, Last_gen_dir_full_path)

    # get end environment image
    # end_img_file_full_path = END_ENV_RAW_IMG_PATH + "snaps-office-3.png"
    end_img_file_full_path = END_ENV_RAW_IMG_PATH + end_img
    end_img_name = os.path.basename(end_img_file_full_path)
    # resize end environment image
    end_env_img_name = resize_end_env_img(end_img_name, end_img_file_full_path)
    End_env_img_file_full_path = END_ENV_RESIZED_IMG_PATH + end_env_img_name
    # copy resized end env image into new gen dir
    print(">> Copy resized end environment image into gen dir...")
    End_env_img_file_full_path = shutil.copy(End_env_img_file_full_path, Last_gen_dir_full_path)

    print(">> Create depth mask for ricoh image...")
    Start_env_img_depth_mask = create_depth_mask_for_img(Start_env_resized_img_name, Start_env_resized_img_full_path)
    Start_env_img_depth_mask = shutil.copy(Start_env_img_depth_mask, Last_gen_dir_full_path)

    print(">> Create depth mask for end environment image...")
    End_env_depth_mask = create_depth_mask_for_img(end_env_img_name, End_env_img_file_full_path)
    End_env_depth_mask = shutil.copy(End_env_depth_mask, Last_gen_dir_full_path)

    

    # prompt = "a sci-fi room with a portal to another dimension"
    # prompt = "nature scene, forest with a waterfall and a river, calming, soothing, beautiful, serene"
    # prompt = "serene, tranquil, meditative scene at sunrise, peaceful Zen garden with smooth stones, a gentle stream, and blossoming cherry trees, soft morning light filters through the foliage, faint mist rising from grass, soft and pastel color palette, gentle pinks greens and warm gold"
    # prompt = "mesmerizing, tranquil, galactic scene, cosmos with swirling nebulas, twinkling stars, distant galaxies in a spectrum of vibrant colors, soft ethereal glow, deep blues, purples, glittering silver of distant stars"
    # prompt = "serene, tranquil, ethereal meditative scene in a sky of billowing undulating clouds, sunrise, warm palette of pastel pinks, oranges, light blues and purples"
    # prompt = "forest scene with a waterfall and a river, green pastures, beautiful, serene"
    # prompt = "a vibrant and tranquil landscape, lush green meadow, various trees in full bloom, white picket fence alongside a dirt path, clear blue sky with fluffy clouds, distant hills"
    
#     prompt = """
# In a liminal office space where two realities converge, the floor is a mosaic of sandy yellow paths and light grey office tiles, forming a checkerboard that bridges the desert with the corporate. The ceiling overhead is a spectacle of transformation: one half retains the open expanse of a clear blue sky, while the other half arches in segments of office-like light brown, dotted with both fluorescent lights and the whimsical floating rings of an aerial game.

# Desks and computers, with their orderly array of office paraphernalia, share this space with playful geometric shapes that belong to an outdoor game, including cones and cubes resting on work surfaces and floors. Traffic cones stand in place of some office chairs, and the obstacle course rings hang in the air, occasionally looping through the arms of desk lamps.

# A doorway frames a snippet of the outdoor game track, seemingly leading into the vastness of a playful landscape, while another opens to the structured confines of a corridor with yellow walls. The distant view blends low-poly trees and mountain silhouettes into the neutral tones of office partitions.

# Notice boards, half-covered in blue, peek from walls that are merging the horizon of the game world with the pragmatic surfaces of an office. Lighting is a dance of sunlight and the artificial glow of an indoor work environment, casting an array of shadows that belong to neither world completely. This space is a canvas of transition, a visual narrative of two disparate environments slowly merging into a single, surreal tableau.
# """
    prompt += ", panoramic, (360 view:1.3)" #, (360-degree:1.3), wide-angle lens"

    gen_steps = 25 # not needed, probably. default in comfy api call.
    denoising_strength_arr = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    if liminal_method == 0:
        '''
        # +++ Gen for start image
        '''
        comfy_output_basename = Last_gen_dir_name + "_00"

        # generate 10 images with gradually increasing denoising strength, based on most ricoh image
        for i in range(0, len(denoising_strength_arr)):
            print(f"+++ [RICOH] queueing prompt with denoise set to {denoising_strength_arr[i]}")
            comfy.gen_from_360_singlectrl(
                Start_env_resized_img_full_path, 
                Start_env_img_depth_mask,
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
                Start_env_img_depth_mask, 
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
        ricoh_copy = shutil.copy(Start_env_resized_img_full_path, Last_gen_dir_full_path + "/gen_img/")
        end_copy = shutil.copy(End_env_img_file_full_path, Last_gen_dir_full_path + "/gen_img/")
        os.rename(ricoh_copy, Last_gen_dir_full_path + "/gen_img/" + Last_gen_dir_name + "_00_00000_.png")
        os.rename(end_copy, Last_gen_dir_full_path + "/gen_img/" + Last_gen_dir_name + "_03_00012_.png")

    # LIMINAL_METHOD 1: always double controlnets
    elif liminal_method == 1:

        ### OLD: no SD, just motion interpolation (melting effect)
        # start_img = shutil.move(Last_ricoh_resized_img_full_path, Last_gen_dir_full_path + "/input_img/img_1.png")
        # end_img = shutil.move(End_env_img_file_full_path, Last_gen_dir_full_path + "/input_img/img_2.png")
        
        # comfy.gen_video_from_imgs(
        #     Last_gen_dir_full_path + "/input_img/",
        #     300,
        #     10,
        #     Last_gen_dir_name
        # )
        ####

        # TODO: Fix for this liminal_method

        # denoising_strength_arr = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        denoising_strength_arr = [0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

        '''
        # +++ Gen for liminal gen between ricoh gen image and end environment gen image
        '''
        comfy_output_basename = Last_gen_dir_name + "_02"

        # generate 10 images with gradually increasing denoising strength
        # start with start ctrl weight at 1, decrease to 0.5
        # start with end ctrl weight at 0, increase to 0.5
        ctrl_weight_1 = 1.0
        ctrl_weight_2 = 0.0
        num_liminal_gen = 0
        for i in range(0, len(denoising_strength_arr)):
            print(f"+++ [LIMINAL 1.1] queueing double ctrl with ctrl 1: {ctrl_weight_1}, ctrl 2: {ctrl_weight_2}, denoise {denoising_strength_arr[i]}")
            comfy.gen_from_360_doublectrl(
                input_360_file_path=Start_env_resized_img_full_path,
                depth_img_1_path=Start_env_img_depth_mask, 
                depth_img_2_path=End_env_depth_mask,
                controlnet_1_strength=ctrl_weight_1,
                controlnet_2_strength=ctrl_weight_2,
                output_filename=comfy_output_basename, 
                text_prompt=prompt, 
                seed=seed,
                denoising_strength=denoising_strength_arr[i],
                steps=steps
            )
            ctrl_weight_1 -= 0.05
            ctrl_weight_2 += 0.05
            num_liminal_gen += 1

        # do one generation in the middle at controls 0.5 and 0.5 based on start image.
        print(f"+++ [LIMINAL 1.1] queueing double ctrl with ctrl 1: {ctrl_weight_1}, ctrl 2: {ctrl_weight_2}, denoise {denoising_strength_arr[i]}")
        comfy.gen_from_360_doublectrl(
            input_360_file_path=Start_env_resized_img_full_path,
            depth_img_1_path=Start_env_img_depth_mask, 
            depth_img_2_path=End_env_depth_mask,
            controlnet_1_strength=0.5,
            controlnet_2_strength=0.5,
            output_filename=comfy_output_basename, 
            text_prompt=prompt, 
            seed=seed,
            denoising_strength=denoising_strength_arr[i],
            steps=steps
        )

        num_liminal_gen += 1

        # do one generation in the middle at controls 0.5 and 0.5 based on end image.
        print(f"+++ [LIMINAL 1.2] queueing double ctrl with ctrl 1: {ctrl_weight_1}, ctrl 2: {ctrl_weight_2}, denoise {denoising_strength_arr[i]}")
        comfy.gen_from_360_doublectrl(
            input_360_file_path=End_env_img_file_full_path,
            depth_img_1_path=Start_env_img_depth_mask, 
            depth_img_2_path=End_env_depth_mask,
            controlnet_1_strength=0.5,
            controlnet_2_strength=0.5,
            output_filename=comfy_output_basename, 
            text_prompt=prompt, 
            seed=seed,
            denoising_strength=denoising_strength_arr[i],
            steps=steps
        )

        num_liminal_gen += 1

        # generate 10 images with gradually decreasing denoising strength, based on end env image
        # start with start ctrl weight at 1, decrease to 0.5
        # start with end ctrl weight at 0, increase to 0.5
        ctrl_weight_1 = 0.45
        ctrl_weight_2 = 0.55
        for i in range(len(denoising_strength_arr) - 1, -1, -1):
            print(f"+++ [LIMINAL 1.2] queueing double ctrl with ctrl 1: {ctrl_weight_1}, ctrl 2: {ctrl_weight_2}, denoise {denoising_strength_arr[i]}")
            comfy.gen_from_360_doublectrl(
                input_360_file_path=End_env_img_file_full_path,
                depth_img_1_path=Start_env_img_depth_mask, 
                depth_img_2_path=End_env_depth_mask,
                controlnet_1_strength=ctrl_weight_1,
                controlnet_2_strength=ctrl_weight_2,
                output_filename=comfy_output_basename, 
                text_prompt=prompt, 
                seed=seed,
                denoising_strength=denoising_strength_arr[i],
                steps=steps
            )
            ctrl_weight_1 -= 0.05
            ctrl_weight_2 += 0.05
            num_liminal_gen += 1

        
        # comfyUI is async, need to wait for all images to finish generating...
        # (this is a really dumb way to wait for images, but not sure if comfyUI has callbacks)
        comfy_output = COMFYUI_OUTPUT_DIR + comfy_output_basename
        list_liminal_gen = glob.glob(comfy_output + '*.png')
        len_list_last_checked = 0
        while len(list_liminal_gen) < num_liminal_gen: 
            list_liminal_gen = glob.glob(comfy_output + '*.png')
            len_list_current = len(list_liminal_gen)
            if len_list_current != len_list_last_checked:
                print(f"+++ [LIMINAL] ... generated {len_list_current}/{num_liminal_gen} based on start and end env depth masks")
            len_list_last_checked = len_list_current
            sleep(1)

        print(f"+++ [LIMINAL] {len(list_liminal_gen)}/{num_liminal_gen} Completed generation.")

        print(f">> Moving generated images to {Last_gen_dir_name}")
        # move endenv images from comfyUI path to project path
        for f in list_liminal_gen:
            img_name = os.path.basename(f)
            print(f">> [LIMINAL] moving {img_name} to {Last_gen_dir_name}")
            os.rename(f, Last_gen_dir_full_path + "/gen_img/" + img_name)

        # TODO: Fix for this liminal_method
        print(f">> Copy starter images to /gen_img/ and rename")
        ricoh_copy = shutil.copy(Start_env_resized_img_full_path, Last_gen_dir_full_path + "/gen_img/")
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

    print("+++ [VIDEO] Waiting for video frame interpolation to complete...")
    sleep(45)
    
    comfy_output = COMFYUI_OUTPUT_DIR + Last_gen_dir_name
    list_video_gen = glob.glob(comfy_output + '*.mp4')
    while len(list_video_gen) < 1:
        # print(f"+++ [VIDEO] ... waiting for video to finish")
        list_video_gen = glob.glob(comfy_output + '*.mp4')
        sleep(1)
    
    print(f"+++ [VIDEO] ... preparing to move video file")
    sleep(15)
    
    vid_file = list_video_gen[0]
    print(f"+++ Finished generating video. Moving {vid_file} to: {Last_gen_dir_full_path}")
    gen_video_file = shutil.move(vid_file, Last_gen_dir_full_path) 
    # vid_name = os.path.basename(vid_file)
    # os.rename(vid_file, Last_gen_dir_full_path + vid_name)
    # vid_file = Last_gen_dir_full_path + vid_name

    ### DEBUG
    # gen_video_file = "C:\\Users\\SREAL\\Lab Users\\mattg\\genai\\rlty2rlty\\gen-dirs\\gen0015\\gen0015_00001.mp4"
    # Last_gen_dir_full_path = "C:\\Users\\SREAL\\Lab Users\\mattg\\genai\\rlty2rlty\\gen-dirs\\gen0015"
    # Last_gen_dir_name = "gen0015"
    # os.mkdir(Last_gen_dir_full_path + "/gen_vid_frames/")
    # os.mkdir(Last_gen_dir_full_path + "/gen_vid_frames/base/")
    # os.mkdir(Last_gen_dir_full_path + "/gen_vid_frames/upscaled/")
    ##### END DEBUG

    print(f">> Extracting frames from video {gen_video_file}...")
    ffmpeg_extract_frames_cmd = f"ffmpeg -i \"{gen_video_file}\" -qscale:v 1 -qmin 1 -qmax 1 \"{Last_gen_dir_full_path}/gen_vid_frames/base/frame%08d.png\""
    ffmpeg_proc = subprocess.Popen(ffmpeg_extract_frames_cmd)
    ffmpeg_proc.wait()
    print(">> Finished extracting frames with ffmpeg.")

    print(">> Upscaling video frames with ESRGAN. This will take a while.")
    realesrgan_path = "C:/Users/SREAL/Lab Users/mattg/wares/Real-ESRGAN/realesrgan-ncnn-vulkan-20220424-windows"
    realesrgan_cmd = f"\"{realesrgan_path}/realesrgan-ncnn-vulkan.exe\" -i \"{Last_gen_dir_full_path}/gen_vid_frames/base/\" -o \"{Last_gen_dir_full_path}/gen_vid_frames/upscaled/\" -n realesr-animevideov3 -s 2 -f jpg"
    realesrgan_proc = subprocess.Popen(realesrgan_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    realesrgan_proc.wait()
    print(">> Finished upscaling frames with ESRGAN.")

    print(">> Combining upscaled frames back into a video...")
    frame_still_duration = 0.05
    xfade_duration = 0.05
    # w = 5760
    # h = 2880
    w = 2880
    h = 1440
    # vid_path = f"{Last_gen_dir_full_path}/{Last_gen_dir_name}_trans_vid.mov"
    vid_name = f"{title}_{Last_gen_dir_name}.mov"
    vid_path = f"{Last_gen_dir_full_path}/{vid_name}"
    vid_path_netdrive = f"{NETWORK_DRIVE_GEN_PATH}/{Last_gen_dir_name}/{vid_name}"
    # w = 4320
    # h = 2160
    ffmpeg_combine_frames_cmd = (f"ffmpeg "
                                f"-framerate 10 "
                                f"-i \"{Last_gen_dir_full_path}/gen_vid_frames/upscaled/frame%08d.jpg\" "
                                f"-vf "
                                f"zoompan=d={(frame_still_duration + xfade_duration) / xfade_duration}:s={w}x{h}:fps={1.0 / xfade_duration},"
                                f"framerate=30:interp_start=0:interp_end=255:scene=100 "
                                # f"-c:v prores_ks -profile:v 2 -qscale:v 15 -pix_fmt yuv422p10le -fps_mode vfr "
                                # f"-c:v libx264 -profile:v main -g 1 -crf 7 -bf 0 -pix_fmt yuv420p -fps_mode vfr " # pxfmt was yuv422p. profile was main
                                # f"-c:v dnxhd -profile:v dnxhr_sq -pix_fmt yuv422p " #problem
                                # f"-c:v cfhd -pix_fmt yuv422p " #problem
                                # f"-c:v mjpeg -qscale:v 1 -pix_fmt yuvj422p -fps_mode vfr "
                                # f"-c:v hevc_nvenc -pix_fmt yuv420p -fps_mode vfr "
                                # f"-c:v hevc_nvenc -profile:v main -preset slow -pix_fmt yuv420p -fps_mode vfr "
                                f"-c:v mjpeg -qscale:v 1 -pix_fmt yuv444p -fps_mode vfr "
                                # f"-b:v 3500K -maxrate 3500K -bufsize 2000K "
                                f"\"{vid_path}\"")

    ffmpeg_combine_proc = subprocess.Popen(ffmpeg_combine_frames_cmd)
    ffmpeg_combine_proc.wait()
    print(">> Finished combining upscaled frames into video.")

    print(">> Removing gen_vid_frames folder.")
    shutil.rmtree(f"{Last_gen_dir_full_path}/gen_vid_frames/")

    # Spatial media metadata only required for viewing the video through a standard video player\
    # e.g., YouTube or VLC. Applied to a skybox in Unity, it is not needed.
    # print(">> Injecting spatial media metadata into video.")
    # spatial_metadata_injector_path = "C:\\Users\\SREAL\\Lab Users\\mattg\\genai\\gen-sys\\frontend\\spatial-media-injector\\spatial-media\\spatialmedia"
    # injected_vid_path = f"{Last_gen_dir_full_path}/{Last_gen_dir_name}_trans_vid_spatial.mov"
    # inject_cmd = f"python \"{spatial_metadata_injector_path}\" -i --stereo=none \"{vid_path}\" \"{injected_vid_path}\""
    # inject_proc = subprocess.Popen(inject_cmd)
    # inject_proc.wait()

    # TODO:
    # copy video to unity path with transition videos
    # rename it there? 
    # copy prompt data to unity path as well


    print(">> Writing generation data to file.")

    transition_prompt_data = f"{start_img}\n{end_img}\n{title}\n{prompt}\n{seed}\n{vid_path}\n{vid_path_netdrive}"
    print(transition_prompt_data)

    # write transition prompt data to file
    with open(Last_gen_dir_full_path + f'/{Last_gen_dir_name}.txt', 'w') as file:
        file.write(transition_prompt_data)

    print(">>>>                               <<<<")
    print(">> All done. Responding to frontend. <<")
    print(">>>>                               <<<<")
    
    runtime = 0
    response = jsonify({ 'video_path': vid_path })
    response.headers.add('Access-Control-Allow-Origin', '*')
    # return render_template("sd_request.html", runtime=runtime)
    return response

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