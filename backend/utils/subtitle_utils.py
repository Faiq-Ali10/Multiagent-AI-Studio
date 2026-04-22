import os
import tempfile
import base64
import subprocess
import whisper
import ffmpeg

# Load the AI model only once
model_instance = None

def get_whisper_model():
    global model_instance
    if model_instance is None:
        model_instance = whisper.load_model("base")
    return model_instance

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def create_srt_content(transcription_result):
    srt_text = ""
    
    # We construct the SRT arrow using character codes to avoid syntax issues
    arrow = chr(45) + chr(45) + ">"
    
    for i, segment in enumerate(transcription_result["segments"]):
        start = format_time(segment["start"])
        end = format_time(segment["end"])
        text = segment["text"].strip()
        
        srt_text += f"{i + 1}\n{start} {arrow} {end}\n{text}\n\n"
        
    return srt_text

def get_video_theme_color(video_path):
    """
    Extracts a frame from the video, shrinks it to 1 pixel to get the average color,
    and returns it as an ASS formatted hex string (BBGGRR).
    """
    try:
        # Extract a frame at 1 second, resize to 1x1, format as raw RGB
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:01", "-i", video_path,
            "-vframes", "1", "-vf", "scale=1:1",
            "-f", "image2pipe", "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if len(result.stdout) >= 3:
            r, g, b = result.stdout[:3]
            
            # Boost the color brightness so it pops on screen
            max_val = max(r, g, b)
            if max_val > 0:
                mult = 255 / max_val
                r = min(255, int(r * mult))
                g = min(255, int(g * mult))
                b = min(255, int(b * mult))
            else:
                r, g, b = 255, 255, 255 # White fallback if completely black
                
            # ASS color format is Blue, Green, Red (BBGGRR)
            return f"{b:02X}{g:02X}{r:02X}"
    except Exception:
        pass
    
    return "00FFFF" # Default Yellow fallback

def process_and_burn_subtitles(video_bytes: bytes, original_filename: str, position: str = "bottom"):
    model = get_whisper_model()
    
    # Extract the original extension
    _, ext = os.path.splitext(original_filename)
    if not ext:
        ext = ".mp4"

    # Corrected SubStation Alpha mapping
    alignment_map = {
        "bottom": 2,
        "top": 6,
        "center": 10
    }
    
    align_code = alignment_map.get(position.lower(), 2)
        
    # Using a TemporaryDirectory isolates the files
    with tempfile.TemporaryDirectory() as temp_dir:
        input_filename = "input_vid" + ext
        srt_filename = "subtitles.srt"
        output_filename = "output_vid" + ext
        
        input_path = os.path.join(temp_dir, input_filename)
        srt_path = os.path.join(temp_dir, srt_filename)
        output_path = os.path.join(temp_dir, output_filename)
        
        # Write the video file
        with open(input_path, "wb") as f:
            f.write(video_bytes)
            
        try:
            # Step A: Transcribe audio to text
            result = model.transcribe(input_path)
            srt_content = create_srt_content(result)
            
            # Stop processing if no speech is detected
            if not srt_content.strip():
                raise Exception("No speech or voice detected in the video.")
            
            with open(srt_path, "w", encoding="utf8") as srt_file:
                srt_file.write(srt_content)
                
            # Step B: Get Dynamic Theme Color
            theme_hex = get_video_theme_color(input_path)
                
            # Step C: Burn subtitles onto the video frames
            video_stream = ffmpeg.input(input_filename)
            audio_stream = video_stream.audio
            
            # Use the dynamic color and add a black outline for readability
            style_string = f"Fontname=Arial,FontSize=24,PrimaryColour=&H{theme_hex},OutlineColour=&H000000,BorderStyle=1,Outline=2,Alignment={align_code}"
            
            video_stream = video_stream.filter(
                "subtitles", 
                srt_filename, 
                force_style=style_string
            )
            
            output_stream = ffmpeg.output(video_stream, audio_stream, output_filename)
            
            # Step D: Compile to native arguments and use subprocess
            ffmpeg_args = ffmpeg.compile(output_stream, overwrite_output=True)
            
            try:
                subprocess.run(
                    ffmpeg_args,
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                error_log = e.stderr.decode("utf8", errors="ignore")
                print("\n========== FFMPEG CRASH LOG ==========")
                print(error_log)
                print("======================================\n")
                raise Exception("FFmpeg crashed. Please check your terminal logs.")
                
            # Step E: Read the final video and encode to Base64
            with open(output_path, "rb") as final_file:
                encoded_string = base64.b64encode(final_file.read()).decode("utf8")
                
            return encoded_string
            
        except Exception as e:
            print("Error during processing: " + str(e))
            raise e
        
def process_outline_subtitles(video_bytes: bytes, original_filename: str):
    model = get_whisper_model()
    
    _, ext = os.path.splitext(original_filename)
    if not ext:
        ext = ".mp4"
        
    with tempfile.TemporaryDirectory() as temp_dir:
        input_filename = "input_vid" + ext
        srt_filename = "subtitles.srt"
        
        output_filename = "output_vid.mkv"
        
        input_path = os.path.join(temp_dir, input_filename)
        srt_path = os.path.join(temp_dir, srt_filename)
        output_path = os.path.join(temp_dir, output_filename)
        
        with open(input_path, "wb") as f:
            f.write(video_bytes)
            
        try:
            result = model.transcribe(
                input_path, 
                fp16=False, 
                condition_on_previous_text=False
            )
            srt_content = create_srt_content(result)
            
            if not srt_content.strip():
                raise Exception("No speech or voice detected in the video.")
            
            with open(srt_path, "w", encoding="utf8") as srt_file:
                srt_file.write(srt_content)
                
            d = chr(45)
            ffmpeg_args = [
                "ffmpeg", d + "y",
                d + "i", input_filename,
                d + "f", "srt",
                d + "i", srt_filename,
                d + "map", "0:v:0",
                d + "map", "0:a:0?",
                d + "map", "1:0",
                d + "c:v", "libx264",
                d + "preset", "fast",
                d + "vsync", "1",
                d + "async", "1",
                d + "c:a", "aac",
                d + "b:a", "192k",
                d + "c:s", "subrip",
                d + "metadata:s:s:0", "language=eng",
                d + "metadata:s:s:0", "title=English",
                output_filename
            ]
            
            try:
                subprocess.run(
                    ffmpeg_args,
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                error_log = e.stderr.decode("utf8", errors="ignore")
                print("\n========== FFMPEG CRASH LOG ==========")
                print(error_log)
                print("======================================\n")
                raise Exception("FFmpeg crashed. Please check your terminal logs.")
                
            with open(output_path, "rb") as final_file:
                encoded_string = base64.b64encode(final_file.read()).decode("utf8")
                
            return encoded_string
            
        except Exception as e:
            print("Error during processing: " + str(e))
            raise e