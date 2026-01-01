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

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.json
        video_url = data.get('url')
        t_color = data.get('color', '#ffffff').replace('#', '0x')
        f_size = int(data.get('font_size', 20)) * 2.5
        x_pos = int(data.get('x_pos', 0)) * 2.5
        y_pos = int(data.get('y_pos', 0)) * 2.5
        bg_on = data.get('bg', True)
        
        unique_id = str(uuid.uuid4())[:8]
        input_file = f"in_{unique_id}.mp4"
        output_name = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

        # 1. Video İndir
        with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': input_file, 'quiet': True}) as ydl:
            ydl.download([video_url])

        # 2. Ses Analizi (Colab Tarzı Tek Seferde Dinleme)
        audio_path = f"tmp_{unique_id}.wav"
        subprocess.run(['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
        
        recognizer = sr.Recognizer()
        translator = GoogleTranslator(source='auto', target='tr')
        
        filter_parts = []
        with sr.AudioFile(audio_path) as source:
            duration = int(source.DURATION)
            # 5 saniyelik daha geniş parçalar sunucuyu rahatlatır
            for i in range(0, duration, 5):
                try:
                    # offset kullanarak her seferinde kaldığı yerden devam eder
                    audio_segment = recognizer.record(source, duration=5)
                    # language=None yaparak Google'ın dili kendi bulmasını sağlıyoruz (Hintçe çözümü)
                    text = recognizer.recognize_google(audio_segment, language=None) 
                    
                    if text:
                        tr_text = translator.translate(text)
                        # Tek satırda tut, özel karakterleri temizle
                        clean_text = tr_text.replace("'", "").replace(":", "").replace('"', '')
                        if len(clean_text) > 40: clean_text = clean_text[:37] + "..."

                        box_str = f":box=1:boxcolor=0x000000@0.7:boxborderw=10" if bg_on else ""
                        part = f"drawtext=text='{clean_text}':fontcolor={t_color}:fontsize={f_size}{box_str}:x=(w-text_w)/2+({x_pos}):y=(h-text_h)/2+({y_pos}):enable='between(t,{i},{i+5})'"
                        filter_parts.append(part)
                except:
                    continue 

        # Filtre yoksa videoyu bozma
        v_filter = ",".join(filter_parts) if filter_parts else "null"
        
        # 3. Final Render (Kopyalama değil, yeniden kodlama - libx264)
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-vf', v_filter,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', output_path
        ]
        
        subprocess.run(cmd, check=True)
        
        for f in [input_file, audio_path]:
            if os.path.exists(f): os.remove(f)

        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
