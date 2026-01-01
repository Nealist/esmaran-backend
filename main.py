import os
import uuid
import yt_dlp
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator
import textwrap

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
        f_size = int(data.get('font_size', 25))
        x_pos = int(data.get('x_pos', 0))
        y_pos = int(data.get('y_pos', 0))
        box_on = data.get('bg', True)
        
        unique_id = str(uuid.uuid4())[:8]
        input_file = f"in_{unique_id}.mp4"
        output_name = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

        # 1. Video İndirme
        with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': input_file}) as ydl:
            ydl.download([video_url])

        # 2. Hassas Ses Analizi
        audio_path = f"tmp_{unique_id}.wav"
        subprocess.run(['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
        
        recognizer = sr.Recognizer()
        translator = GoogleTranslator(source='en', target='tr')
        
        filter_parts = []
        with sr.AudioFile(audio_path) as source:
            # 3'er saniyelik çok kısa dilimlerle kelime takibi
            duration = int(source.DURATION)
            for i in range(0, duration, 3):
                try:
                    audio_segment = recognizer.record(source, duration=3)
                    text = recognizer.recognize_google(audio_segment, language='en-US')
                    tr_text = translator.translate(text)
                    # Satır genişliğini sınırla (Telefona uygun)
                    wrapped = "\n".join(textwrap.wrap(tr_text, width=20))
                    
                    box_str = f":box=1:boxcolor=0x000000@0.7:boxborderw=10" if box_on else ""
                    part = f"drawtext=text='{wrapped}':fontcolor={t_color}:fontsize={f_size}{box_str}:x=(w-text_w)/2+({x_pos}):y=(h-text_h)/2+({y_pos}):enable='between(t,{i},{i+3})'"
                    filter_parts.append(part)
                except: continue

        v_filter = ",".join(filter_parts) if filter_parts else "drawtext=text=' '"
        
        # 3. İşleme
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-vf', v_filter, '-preset', 'ultrafast', '-c:a', 'copy', output_path
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
    
