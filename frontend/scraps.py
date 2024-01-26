    denoising_strength_arr = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        ctrl_weight_1_arr =      [1.0, 1.0, 1.0, 1.0, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
        
        comfy_output_basename = Last_gen_dir_name + "_00"

        '''
        # Generate for start
        '''
        # generate images for start image
        num_gen = 0
        ctrl_weight_1 = ctrl_weight_1_arr[0]
        while num_gen < len(denoising_strength_arr):
            ctrl_weight_1 = ctrl_weight_1_arr[num_gen]
            ctrl_weight_2 = 1 - ctrl_weight_1
            print(f"+++ [START_IMG] queueing double ctrl with ctrl 1: {ctrl_weight_1}, ctrl 2: {ctrl_weight_2}")
            comfy.gen_from_360_doublectrl(
                Last_ricoh_resized_img_full_path,
                Ricoh_img_depth_mask, 
                End_env_depth_mask,
                ctrl_weight_1,
                ctrl_weight_2,
                comfy_output_basename, 
                prompt, 
                seed,
                denoising_strength_arr[num_gen],
                steps
            )
            num_gen += 1

        # comfyUI is async, need to wait for all images to finish generating
        comfy_output = COMFYUI_OUTPUT_DIR + comfy_output_basename
        list_gen_start = glob.glob(comfy_output + '*.png')
        while len(list_gen_start) < num_gen:
            print(f"+++ [START_IMG] ... generated {len(list_gen_start)}/{num_gen} based on ricoh and end env depth masks")
            list_gen_start = glob.glob(comfy_output + '*.png')
            sleep(1)

        print(f"+++ [START_IMG] {len(list_gen_start)}/{num_gen} Completed generation.")

        print(f">> Moving generated images to {Last_gen_dir_name}")
        # move start images from comfyUI path to project path
        for f in list_gen_start:
            img_name = os.path.basename(f)
            print(f">> [START_IMG] moving {img_name} to {Last_gen_dir_name}")
            os.rename(f, Last_gen_dir_full_path + "/gen_img/" + img_name)

        comfy_output_basename = Last_gen_dir_name + "_02"

        '''
        # Generate for end
        '''
        # generate images for end image
        i = (len(denoising_strength_arr) - 1)
        ctrl_weight_1 = ctrl_weight_1_arr[0]

        while i >= 0:
            print(i)
            ctrl_weight_1 = ctrl_weight_1_arr[i]
            ctrl_weight_2 = 1 - ctrl_weight_1
            print(f"+++ [END_IMG] queueing double ctrl with ctrl 1: {ctrl_weight_1}, ctrl 2: {ctrl_weight_2}")
            comfy.gen_from_360_doublectrl(
                End_env_img_file_full_path,
                End_env_depth_mask,
                Ricoh_img_depth_mask, 
                ctrl_weight_1,
                ctrl_weight_2,
                comfy_output_basename, 
                prompt, 
                seed,
                denoising_strength_arr[i],
                steps
            )
            i -= 1

        num_gen = len(denoising_strength_arr)
        # comfyUI is async, need to wait for all images to finish generating
        comfy_output = COMFYUI_OUTPUT_DIR + comfy_output_basename
        list_gen_end = glob.glob(comfy_output + '*.png')
        while len(list_gen_end) < num_gen:
            print(f"+++ [END_IMG] ... generated {len(list_gen_end)}/{num_gen} based on ricoh and end env depth masks")
            list_gen_end = glob.glob(comfy_output + '*.png')
            sleep(1)

        print(f"+++ [END_IMG] {len(list_gen_end)}/{num_gen} Completed generation.")

        print(f">> Moving generated images to {Last_gen_dir_name}")
        # move endenv images from comfyUI path to project path
        for f in list_gen_end:
            img_name = os.path.basename(f)
            print(f">> [END_IMG] moving {img_name} to {Last_gen_dir_name}")
            os.rename(f, Last_gen_dir_full_path + "/gen_img/" + img_name)

    Last_img_depth_mask = create_depth_mask_for_img(Last_img_dir_name, Last_img_file_full_path)
    
    # set seed
    seed = 42

    '''
    +++ Gen for start image
    '''

    print(f"+++ Generating 10 images based on {Last_img_file_full_path} +++")
    prompt = "a sci-fi room with a portal to another dimension"
    prompt += ", panoramic, (360 view:1.3)" #, (360-degree:1.3), wide-angle lens"

    gen_steps = 25 # not needed, probably. default in comfy api call.
    denoising_strength_arr = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    # generate 10 images with gradually increasing denoising strength, based on most recent photo in the photo path
    for i in range(0, len(denoising_strength_arr)):
        comfy.gen_from_360_singlectrl(
            Last_img_file_full_path, 
            Last_img_depth_mask,
            Last_img_dir_name, 
            prompt, 
            seed, 
            denoising_strength_arr[i]
        )

    # comfyUI is async, need to wait for all images to finish generating
    comfy_output = COMFYUI_OUTPUT_DIR + Last_img_dir_name
    list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
    while len(list_gen_from_ricoh_img) < len(denoising_strength_arr):
        print("+++ ... waiting for more gen images based on image")
        list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
        sleep(1)

    '''
    +++ Gen for end environment image
    '''
    # generate 10 images with gradually increasing denoising strength, based on most recent photo in the photo path
    for i in range(0, len(denoising_strength_arr)):
        comfy.gen_from_360_singlectrl(
            Last_img_file_full_path, 
            Last_img_depth_mask,
            Last_img_dir_name, 
            prompt, 
            seed, 
            denoising_strength_arr[i]
        )

    # comfyUI is async, need to wait for all images to finish generating
    comfy_output = COMFYUI_OUTPUT_DIR + Last_img_dir_name
    list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
    while len(list_gen_from_ricoh_img) < len(denoising_strength_arr):
        print("+++ ... waiting for more gen images based on image")
        list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
        sleep(1)

    return
    '''
    gen_steps = 20
    gen_steps_arr = [1, 3, 5, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20]
    
    # generate 10 images with gradually increasing denoising strength, based on most recent photo in the photo path
    for i in range(0, len(gen_steps_arr)):
        comfy.gen_from_360(
            last_img_file_full_path, 
            last_img_dir_name, 
            prompt, 
            seed, 
            gen_steps - gen_steps_arr[i]
        )
    '''

    # comfyUI is async, need to wait for all images to finish generating
    comfy_output = COMFYUI_OUTPUT_DIR + Last_img_dir_name
    list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
    while len(list_gen_from_ricoh_img) < len(gen_steps_arr):
        print("... waiting for more gen images based on ricoh photo")
        list_gen_from_ricoh_img = glob.glob(comfy_output + '*.png')
        sleep(1)
    
    for img in list_gen_from_ricoh_img:
        print(img)

    # move ricoh images from comfyUI path to project path
    for f in list_gen_from_ricoh_img:
        img_name = os.path.basename(f)
        os.rename(f, RICOH_RESIZED_IMG_PATH + Last_img_dir_name + "/" + img_name)

    list_gen_from_end_img = []

    # get end image to generate from
    end_img_file_full_path = END_IMG + "screenshot-spheres.png"
    end_img_name = os.path.basename(end_img_file_full_path)[:-4]

    # if the image sequence has not already been generated, generate the last half of the transition
    # otherwise, just get the list of images previously generated
    if not os.path.isdir(END_IMG + end_img_name):
        mkdir(END_IMG + end_img_name)
        end_img_file_full_path = resize_img(end_img_file_full_path, END_IMG + end_img_name)

        # generate the reverse images to transition from AI world to VR world
        for i in range(0, len(gen_steps_arr)):
            comfy.gen_from_360(end_img_file_full_path, end_img_name + "_resized", prompt, seed, gen_steps - gen_steps_arr[i])

        while len(list_gen_from_end_img) < len(gen_steps_arr):
            print("... waiting for more gen images based on end screenshot")
            list_gen_from_end_img = glob.glob(COMFYUI_OUTPUT_DIR + end_img_name + '*.png')
            sleep(1)
        
        # move files from comfyUI path to project path
        for f in list_gen_from_end_img:
            img_name = os.path.basename(f)
            os.rename(f, END_IMG + end_img_name + "/" + img_name)
    else:
        list_gen_from_end_img = glob.glob(END_IMG + end_img_name + "/" + '*.png') 
        # [os.path.join(END_IMG + end_img_name, f) for f in os.listdir(END_IMG + end_img_name) if os.path.isfile(join(END_IMG + end_img_name, f))]

    # get list of the AI->VR generated images
    for img in list_gen_from_end_img:
        print(img)

    imgs_to_mask = list_gen_from_ricoh_img[1:] + list_gen_from_end_img[1:]

    # bisect images, merge them, and insert transparent mask
    # for img in imgs_to_mask:
    #     img_processing.bisect_image_and_mask(img)

    # fill the seam of generated images and upscale them

    # create video out of seamless 360 photos

    # upload video to server for view on headset