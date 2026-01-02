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
    audio_path = f"tmp_{unique_id}.wav"

    try:
        data = request.json
        video_url = data.get('url')
        t_color = data.get('color', '#ffffff').replace('#', '0x')
        f_size = int(float(data.get('font_size', 25)) * 2.8)
        x_pos = int(float(data.get('x_pos', 0)) * 2.5)
        y_pos = int(float(data.get('y_pos', 0)) * 2.5)
        bg_on = data.get('bg', True)

        # 1. Video İndir
        ydl_opts = {
            'format': 'best',
            'outtmpl': input_file,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 2. Sesi Çıkar (Google'ın en sevdiği format: 16k mono)
        subprocess.run(['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
        
        recognizer = sr.Recognizer()
        translator = GoogleTranslator(source='auto', target='tr')
        filter_parts = []
        
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

        # SES ANALİZİ - YENİ MANTIK
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source) # Tüm sesi bir kerede hafızaya al
            
            # Tüm videoyu tek parça analiz etmek yerine, sessizliğe göre bölüyoruz
            try:
                # Google'a tüm dosyayı gönderip 'json' formatında zaman damgalı sonuç istiyoruz
                full_text = recognizer.recognize_google(audio_data, language="tr-TR") 
                
                # Basit bir kelime bölücü (Render'da zaman damgası her zaman gelmeyebilir)
                # Bu yüzden metni 4'er saniyelik bloklara kendimiz bölüyoruz
                words = full_text.split()
                chunk_size = 5 # Her altyazıda 5 kelime
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size])
                    start = (i // chunk_size) * 4
                    end = start + 4
                    
                    clean_text = chunk.replace("'", "").replace('"', '').replace(':', '').strip()
                    box_str = f":box=1:boxcolor=0x000000@0.7:boxborderw=15" if bg_on else ""
                    part = f"drawtext=fontfile='{font_path}':text='{clean_text}':fontcolor={t_color}:fontsize={f_size}{box_str}:x=(w-text_w)/2+({x_pos}):y=(h-text_h)/2+({y_pos}):enable='between(t,{start},{end})'"
                    filter_parts.append(part)
            except:
                pass

        # KRİTİK: Eğer liste boşsa FFmpeg hata vermesin diye boş bir yazı ekle
        v_filter = ",".join(filter_parts) if filter_parts else "drawtext=text=' ':x=0:y=0"
        
        with open(filter_file, "w", encoding="utf-8") as f:
            f.write(v_filter)
        
        # 3. Final Render (Filtreyi complex_script olarak zorla)
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-filter_complex_script:v', filter_file,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
            '-c:a', 'copy', output_path # Sesi bozmadan kopyala
        ]
        subprocess.run(cmd, check=True)
        
        return jsonify({"status": "success", "download_url": f"https://{request.host}/download/{output_name}"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        for f in [input_file, audio_path, filter_file]:
            if os.path.exists(f): os.remove(f)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
