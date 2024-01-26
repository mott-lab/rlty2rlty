from PIL import Image, ImageDraw

comfy_out = 'C:/Users/SREAL/Lab Users/mattg/genai/gen-sys/ComfyUI_windows_portable/ComfyUI/output/'

def bisect_image_and_mask(img_file_full_path):
    # img_file = 'img2img_00016_'
    img = Image.open(img_file_full_path)

    print(f"Original size : {img.size}") # 5464x3640

    # img_crop_l = img.crop((0, 0, 540, 720))
    # img_crop_r = img.crop((900, 0, 1440, 720))
    img_crop_l = img.crop((0, 0, 720, 720))
    img_crop_r = img.crop((720, 0, 1440, 720))

    crop_merge = Image.new('RGB', (2*img_crop_r.size[0], img_crop_l.size[1]), (250, 250, 250))
    crop_merge.paste(img_crop_r, (0,0))
    crop_merge.paste(img_crop_l, (img_crop_r.size[0], 0))

    print(f"crop_merge size : {crop_merge.size}")

    midpoint_w = crop_merge.size[0] / 2
    fill_trans_w = 300

    mask = Image.new('L', crop_merge.size, color=255)
    draw = ImageDraw.Draw(mask)

    draw.rectangle(xy=[midpoint_w - (fill_trans_w / 2), 0, midpoint_w + (fill_trans_w / 2), 720], fill=0)
    crop_merge.putalpha(mask)

    del draw

    crop_merge.save(img_file_full_path[:-4] + 'cropmergemask.png')

    # img_resized = img.resize((1440, 720))
    # img_crop_l.save(comfy_out + img_2_process + 'R.png')

    img.close()

    return img_file_full_path[:-4] + 'cropmergemask.png'