import os
import uuid
import yt_dlp
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_srt(video_path, unique_id):
    # Sesi ayıkla
    audio_path = f"tmp_{unique_id}.wav"
    subprocess.run(['ffmpeg', '-i', video_path, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
    
    recognizer = sr.Recognizer()
    translator = GoogleTranslator(source='en', target='tr')
    srt_content = ""
    
    with sr.AudioFile(audio_path) as source:
        duration = int(source.DURATION)
        # Videoyu 5'er saniyelik dilimlerle işle
        for i in range(0, duration, 5):
            try:
                offset = i
                audio_segment = recognizer.record(source, duration=5)
                text = recognizer.recognize_google(audio_segment, language='en-US')
                translated = translator.translate(text)
                
                # SRT Formatı oluştur (00:00:05 -> 00:00:10 gibi)
                start = f"00:00:{i:02d},000"
                end = f"00:00:{min(i+5, duration):02d},000"
                srt_content += f"{(i//5)+1}\n{start} --> {end}\n{translated}\n\n"
            except:
                continue
                
    srt_path = f"sub_{unique_id}.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    
    if os.path.exists(audio_path): os.remove(audio_path)
    return srt_path

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.json
        video_url = data.get('url')
        t_color = data.get('color', '#ffffff') # FFmpeg subtitles için Hex yeterli
        f_size = data.get('font_size', '20')
        
        unique_id = str(uuid.uuid4())[:8]
        input_file = f"in_{unique_id}.mp4"
        output_name = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

        # 1. Videoyu İndir
        with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': input_file}) as ydl:
            ydl.download([video_url])

        # 2. Dinamik SRT (Altyazı Dosyası) Oluştur
        srt_file = generate_srt(input_file, unique_id)

        # 3. SRT'yi Videoya Göm (Saniye saniye değişen mod)
        # Not: Force_style ile renk ve boyutu ayarlıyoruz
        style = f"FontSize={f_size},PrimaryColour={t_color.replace('#','&H00')}"
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-vf', f"subtitles={srt_file}:force_style='{style}'",
            '-preset', 'ultrafast', '-c:a', 'copy', output_path
        ]
        
        subprocess.run(cmd, check=True)
        
        # Temizlik
        for f in [input_file, srt_file]:
            if os.path.exists(f): os.remove(f)

        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

@app.route('/')
def home(): return "ESMARAN AI DINAMIK MOD AKTIF"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
