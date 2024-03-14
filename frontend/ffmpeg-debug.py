

import subprocess

NETWORK_DRIVE_GEN_PATH = "//192.168.1.227/rlty2rlty/gen-dirs/"

# Last_gen_dir_full_path = "C:\\Users\\SREAL\\Lab Users\\mattg\\genai\\rlty2rlty\\gen-dirs\\gen0004"
Last_gen_dir_full_path = "D:\\mattg\\gen-sys\\rlty2rlty\\gen-dirs\\gen0005"
Last_gen_dir_name = "gen0005"

title = "Matt G_gen0005"

print(">> Combining upscaled frames back into a video...")
frame_still_duration = 0.05
xfade_duration = 0.05

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
                            f"-c:v mjpeg -qscale:v 1 -pix_fmt yuv444p -fps_mode vfr -color_range 2 "
                            # f"-b:v 3500K -maxrate 3500K -bufsize 2000K "
                            f"\"{vid_path}\"")

ffmpeg_combine_proc = subprocess.Popen(ffmpeg_combine_frames_cmd)
ffmpeg_combine_proc.wait()
print(">> Finished combining upscaled frames into video.")