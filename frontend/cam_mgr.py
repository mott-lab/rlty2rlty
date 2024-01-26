import shutil
from time import sleep
import requests
import re
from PIL import Image

def start_session():
    print("STARTING SESSION...")
    url = "http://192.168.1.1/osc/commands/execute"

    payload = "{\r\n    \"name\": \"camera.startSession\",\r\n    \"parameters\": {}\r\n}"
    headers = {
    'Content-Type': 'application/json;charset=utf-8'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    print("========================")
    SESSION_ID = response.json()["results"]["sessionId"]
    return SESSION_ID

def set_api_2(SESSION_ID):
    print("SETTING API VERSION...")
    url = "http://192.168.1.1/osc/commands/execute"

    payload = "{\"name\": \"camera.setOptions\",\
        \"parameters\": \
        {\"sessionId\": \"" + SESSION_ID + "\",\
            \"options\": {\
            \"clientVersion\": 2}}}"
    headers = {
    'Content-Type': 'application/json;charset=utf-8'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    print("========================")

def get_state():
    print("GETTING STATE...")
    url = "http://192.168.1.1/osc/state"

    payload = ""
    headers = {
    'Content-Type': 'application/json;charset=utf-8'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    # SESSION_ID = response.json()[""]
    responseJSON = response.json()
    if "_latestFileUrl" not in responseJSON["state"]:
        print("--- Not the proper API version, need to start session...")
        SESSION_ID = start_session()
        set_api_2(SESSION_ID)
        return ""
    
    latest_path = response.json()["state"]["_latestFileUrl"]
    print("--- Latest file: " + latest_path)
    print("========================")
    return latest_path

def take_pic():
    print("TAKING PHOTO...")
    url = "http://192.168.1.1/osc/commands/execute"

    payload = "{\"name\": \"camera.takePicture\"}"
    headers = {
    'Content-Type': 'application/json;charset=utf-8'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    print("========================")

def get_photo(photo_url):
    print("GETTING PHOTO...")
    # URL needs to be updated with last pic from state
    url = "http://192.168.1.1/files/744a605553442020104bdf5ff300fc01/100RICOH/R0010013.JPG"
    url = photo_url

    payload = ""
    headers = {
    'Content-Type': 'application/json;charset=utf-8'
    }

    # response = requests.request("GET", url, headers=headers, data=payload)
    response = requests.get(url, stream=True)

    print("========================")
    return response.raw


def main():
    while(1):
        latest_photo_url = get_state()
        old_photo_url = latest_photo_url
        take_pic()
        latest_photo_url = get_state()
        
        while latest_photo_url == old_photo_url or latest_photo_url == "":
            print("-- Waiting for new photo...")
            sleep(2)
            latest_photo_url = get_state()
        
        latest_photo_name = re.split("/", latest_photo_url)[-1]
        print("Latest photo: " + latest_photo_name)
        
        photo_raw = get_photo(latest_photo_url)

        save_path = "C:/Users/SREAL/Lab Users/mattg/genai/gen-sys/input_img/"
        # save_path += latest_photo_name
        with open(save_path + latest_photo_name, "wb") as f:
            photo_raw.decode_content = True
            shutil.copyfileobj(photo_raw, f)
            
        print("-- Finished saving: " + save_path + latest_photo_name)
        # Resize image
        print("-- Resizing image...")
        image = Image.open(save_path + latest_photo_name)
        print(f"Original size : {image.size}") # 5464x3640
        img_resized = image.resize((960, 480))
        img_new_name = latest_photo_name[:-4] + "_resized.jpg"
        save_path += "resized/"
        img_resized.save(save_path + img_new_name)
        print(f"-- Finished resizing image. Saved: {save_path + img_new_name}")
        sleep(40)
        


if __name__ == "__main__":
    main()
