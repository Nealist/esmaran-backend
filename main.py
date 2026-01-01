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
    unique_id = str(uuid.uuid4())[:8]
    input_file = f"in_{unique_id}.mp4"
    output_name = f"esmaran_{unique_id}.mp4"
    output_path = os.path.join(UPLOAD_FOLDER, output_name)
    filter_file = f"filter_{unique_id}.txt"

    try:
        data = request.json
        video_url = data.get('url')
        t_color = data.get('color', '#ffffff').replace('#', '0x')
        f_size = int(float(data.get('font_size', 25)) * 2.8) 
        x_pos = int(float(data.get('x_pos', 0)) * 2.5)
        y_pos = int(float(data.get('y_pos', 0)) * 2.5)
        bg_on = data.get('bg', True)
        
        # 1. Video İndir
        with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': input_file, 'quiet': True}) as ydl:
            ydl.download([video_url])

        # 2. Ses Analizi
        audio_path = f"tmp_{unique_id}.wav"
        subprocess.run(['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
        
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300 
        translator = GoogleTranslator(source='auto', target='tr')
        filter_parts = []

        # Render/Linux sunucularında genel font yolu
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        # Eğer bu font yoksa alternatif olarak şunu dene:
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

        with sr.AudioFile(audio_path) as source:
            duration = int(source.DURATION)
            for i in range(0, duration, 3):
                try:
                    audio_segment = recognizer.record(source, duration=3)
                    text = recognizer.recognize_google(audio_segment) 
                    if text and len(text.strip()) > 1:
                        tr_text = translator.translate(text)
                        # FFmpeg Drawtext için metni temizle (Virgülleri ve tırnakları uçur)
                        clean_text = tr_text.replace("'", "").replace(":", "").replace(",", "").replace('"', '').strip()
                        if len(clean_text) > 38: clean_text = clean_text[:35] + "..."
                        
                        box_str = f":box=1:boxcolor=0x000000@0.7:boxborderw=15" if bg_on else ""
                        
                        # Font dosyasını açıkça belirterek ekle
                        part = f"drawtext=fontfile='{font_path}':text='{clean_text}':fontcolor={t_color}:fontsize={f_size}{box_str}:x=(w-text_w)/2+({x_pos}):y=(h-text_h)/2+({y_pos}):enable='between(t,{i},{i+3})'"
                        filter_parts.append(part)
                except: continue

        if not filter_parts:
            filter_parts.append(f"drawtext=fontfile='{font_path}':text='Esmaran AI':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2")

        # Filtreyi tek satır ve UTF-8 olarak kaydet
        v_filter = ",".join(filter_parts)
        with open(filter_file, "w", encoding="utf-8") as f:
            f.write(v_filter)
        
        # 3. Final Render (Filtre scriptini tam yol ile ver)
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-filter_complex_script:v', filter_file,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
            '-c:a', 'aac', '-map', '0', output_path
        ]
        
        subprocess.run(cmd, check=True)
        
        # Temizlik
        for f in [input_file, audio_path, filter_file]:
            if os.path.exists(f): os.remove(f)

        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})
    except Exception as e:
        for f in [input_file, filter_file]:
            if os.path.exists(f): os.remove(f)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

