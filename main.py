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
        f_size = float(data.get('font_size', 20)) * 2.5
        x_pos = float(data.get('x_pos', 0)) * 2.5
        y_pos = float(data.get('y_pos', 0)) * 2.5
        bg_on = data.get('bg', True)
        
        unique_id = str(uuid.uuid4())[:8]
        input_file = f"in_{unique_id}.mp4"
        output_name = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

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

        with sr.AudioFile(audio_path) as source:
            duration = int(source.DURATION)
            for i in range(0, duration, 3):
                try:
                    audio_segment = recognizer.record(source, duration=3)
                    text = recognizer.recognize_google(audio_segment) 
                    
                    if text and len(text.strip()) > 1:
                        tr_text = translator.translate(text)
                        
                        # KRİTİK TAMİR: FFmpeg drawtext için özel karakter temizliği
                        # Tırnakları, iki noktaları ve ters bölüleri siliyoruz
                        clean_text = tr_text.replace("'", "").replace(":", "").replace('"', '').replace("\\", "")
                        
                        box_str = f":box=1:boxcolor=0x000000@0.7:boxborderw=10" if bg_on else ""
                        
                        # drawtext komutunu çift tırnak (") ile sarıyoruz, içindekileri tek tırnak (') yapıyoruz
                        part = f"drawtext=text='{clean_text}':fontcolor={t_color}:fontsize={f_size}{box_str}:x=(w-text_w)/2+({x_pos}):y=(h-text_h)/2+({y_pos}):enable='between(t,{i},{i+3})'"
                        filter_parts.append(part)
                except:
                    continue

        if not filter_parts:
            # Boş kalmasın diye güvenli bir yazı ekle
            filter_parts.append("drawtext=text='Esmaran AI':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=(h-text_h)/2")

        v_filter = ",".join(filter_parts)
        
        # 3. Final Render (Tırnak hatasını önlemek için filtreyi değişken olarak veriyoruz)
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-vf', v_filter,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25',
            '-c:a', 'aac', '-tight', 'experimental', output_path
        ]
        
        # subprocess.run'ı tek bir liste olarak çağırmak tırnak hatalarını çözer
        subprocess.run(cmd, check=True)
        
        for f in [input_file, audio_path]:
            if os.path.exists(f): os.remove(f)

        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})
    except Exception as e:
        # Hatayı daha net görmek için yazdırıyoruz
        print(f"HATA DETAYI: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
