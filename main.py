import os
import uuid
import yt_dlp
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator # Hata veren kütüphane değiştirildi

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def transcribe_and_translate(video_path):
    # Videonun sesini ayıkla (.wav formatına çevir)
    audio_path = f"tmp_{uuid.uuid4().hex}.wav"
    subprocess.run(['ffmpeg', '-i', video_path, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
    
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            # Sesi metne çevir (İngilizce)
            english_text = recognizer.recognize_google(audio_data, language='en-US')
            # Türkçe'ye çevir (Deep Translator ile)
            translated = GoogleTranslator(source='en', target='tr').translate(english_text)
            return translated
    except Exception as e:
        print(f"Çeviri hatası: {e}")
        return "Altyazi Hazirlanamadi - ESMARAN AI"
    finally:
        if os.path.exists(audio_path): os.remove(audio_path)

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

        # 1. Videoyu İndir
        with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': input_file}) as ydl:
            ydl.download([video_url])

        # 2. Dinle ve Çevir (Burası biraz zaman alır)
        altyazi_metni = transcribe_and_translate(input_file)

        # 3. Altyazıyı Videoya Bas (FFmpeg)
        # Metin çok uzunsa videoda taşmasın diye basitçe kesiyoruz
        final_text = (altyazi_metni[:60] + '...') if len(altyazi_metni) > 60 else altyazi_metni
        
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-vf', f"drawtext=text='{final_text}':fontcolor={t_color}:fontsize={f_size}:box=1:boxcolor=0x000000@0.6:x=(w-text_w)/2:y=(h-text_h)/2+({y_val})",
            '-preset', 'ultrafast', '-c:a', 'copy', output_path
        ]
        
        subprocess.run(cmd, check=True)
        if os.path.exists(input_file): os.remove(input_file)

        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

@app.route('/')
def home(): return "ESMARAN AI AKTIF"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
