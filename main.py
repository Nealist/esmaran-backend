import os
import uuid
import yt_dlp
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import speech_recognition as sr # Ses dinleme için
from googletrans import Translator # Çeviri için
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def transcribe_and_translate(video_path):
    # Videonun sesini ayıkla
    audio_path = video_path.replace('.mp4', '.wav')
    subprocess.run(['ffmpeg', '-i', video_path, '-ar', '16000', '-ac', '1', audio_path, '-y'])
    
    recognizer = sr.Recognizer()
    translator = Translator()
    
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
        # Sesi metne çevir (İngilizce varsayıyoruz)
        text = recognizer.recognize_google(audio_data, language='en-US')
        # Türkçe'ye çevir
        translated = translator.translate(text, dest='tr').text
        return translated

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.json
        video_url = data.get('url')
        t_color = data.get('color', '#ffffff').replace('#', '0x')
        f_size = data.get('font_size', '24')
        y_val = data.get('y_pos', 0)
        
        unique_id = str(uuid.uuid4())[:8]
        input_file = f"in_{unique_id}.mp4"
        output_name = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

        # 1. İndir
        with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': input_file}) as ydl:
            ydl.download([video_url])

        # 2. Dinle ve Çevir
        try:
            altyazi = transcribe_and_translate(input_file)
        except:
            altyazi = "Ses anlasilamadi - ESMARAN AI"

        # 3. Altyazıyı Videoya Bas
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-vf', f"drawtext=text='{altyazi}':fontcolor={t_color}:fontsize={f_size}:box=1:boxcolor=0x000000@0.6:x=(w-text_w)/2:y=(h-text_h)/2+({y_val})",
            '-preset', 'ultrafast', '-c:a', 'copy', output_path
        ]
        
        subprocess.run(cmd, check=True)
        if os.path.exists(input_file): os.remove(input_file)
        if os.path.exists(input_file.replace('.mp4', '.wav')): os.remove(input_file.replace('.mp4', '.wav'))

        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
