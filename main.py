import os
import uuid
import yt_dlp
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import speech_recognition as sr

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/process', methods=['POST'])
def process_video():
    unique_id = str(uuid.uuid4())[:8]
    input_file = f"raw_{unique_id}.mp4"
    output_name = f"esmaran_{unique_id}.mp4"
    output_path = os.path.join(UPLOAD_FOLDER, output_name)
    audio_path = f"audio_{unique_id}.wav"
    filter_file = f"filter_{unique_id}.txt"

    try:
        data = request.json
        video_url = data.get('url')
        # Arayüzden gelen ayarlar
        t_color = data.get('color', '#ffffff').replace('#', '0x')
        f_size = int(float(data.get('font_size', 25)) * 2.8)
        x_pos = int(float(data.get('x_pos', 0)) * 2.5)
        y_pos = int(float(data.get('y_pos', 0)) * 2.5)
        bg_on = data.get('bg', True)

        # 1. YT-DLP İLE EVRENSEL İNDİRME (YT, TikTok, FB, IG hepsini kapsar)
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': input_file,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.google.com/',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 2. SESİ ANALİZ ET VE ALTYAZI OLUŞTUR
        subprocess.run(['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
        
        recognizer = sr.Recognizer()
        filter_parts = []
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Render standart fontu

        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            try:
                full_text = recognizer.recognize_google(audio_data, language="tr-TR")
                words = full_text.split()
                chunk_size = 4 # Her 4 kelimede bir yeni satır
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size])
                    start, end = (i//chunk_size)*3, ((i//chunk_size)+1)*3
                    box = ":box=1:boxcolor=0x000000@0.6:boxborderw=10" if bg_on else ""
                    part = f"drawtext=fontfile='{font_path}':text='{chunk}':fontcolor={t_color}:fontsize={f_size}{box}:x=(w-text_w)/2+({x_pos}):y=(h-text_h)/2+({y_pos}):enable='between(t,{start},{end})'"
                    filter_parts.append(part)
            except:
                filter_parts.append("drawtext=text=' ':x=0:y=0")

        # 3. FFMPEG İLE RENDER VE GALERİYE HAZIR HALE GETİRME
        v_filter = ",".join(filter_parts)
        with open(filter_file, "w", encoding="utf-8") as f:
            f.write(v_filter)

        render_cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-filter_complex_script:v', filter_file,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '24',
            '-c:a', 'aac', '-b:a', '128k', output_path
        ]
        subprocess.run(render_cmd, check=True)

        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        # Geçici dosyaları temizle
        for f in [input_file, audio_path, filter_file]:
            if os.path.exists(f): os.remove(f)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
                
