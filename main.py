import os
import uuid
import yt_dlp
import subprocess
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def download_fallback(url, output_path):
    """
    Eğer yt-dlp engellenirse, üçüncü taraf API'leri kullanarak videoyu indirmeye çalışır.
    """
    # Alternatif indirme servisleri (Örnek mantık)
    apis = [
        f"https://api.v1.snapinst.app/v1/download?url={url}",
        f"https://api.tikmate.app/download?url={url}"
    ]
    for api in apis:
        try:
            r = requests.get(api, timeout=10)
            if r.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(r.content)
                return True
        except:
            continue
    return False

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

        # 1. ADIM: AKILLI İNDİRME SİSTEMİ
        ydl_opts = {
            'format': 'best',
            'outtmpl': input_file,
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except Exception as e:
            # Eğer yt-dlp hata verirse (Rate limit gibi), yedek yöntemi dene
            success = download_fallback(video_url, input_file)
            if not success:
                raise Exception("Tüm indirme yöntemleri Instagram engeline takıldı. Lütfen linki kontrol et veya daha sonra dene.")

        # 2. ADIM: SES ANALİZİ VE ALTYAZI ÇEVİRİSİ
        subprocess.run(['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', audio_path, '-y'], check=True)
        
        recognizer = sr.Recognizer()
        translator = GoogleTranslator(source='auto', target='tr')
        filter_parts = []
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        with sr.AudioFile(audio_path) as source:
            duration = int(source.DURATION)
            # 7. saniye barajını yıkmak için sesi küçük parçalara bölerek tarıyoruz
            for i in range(0, duration, 3):
                try:
                    audio_segment = recognizer.record(source, duration=3)
                    text = recognizer.recognize_google(audio_segment, language=None)
                    if text:
                        tr_text = translator.translate(text)
                        clean_text = tr_text.replace("'", "").replace('"', '').replace(':', '').strip()
                        if len(clean_text) > 38: clean_text = clean_text[:35] + "..."
                        
                        box_str = f":box=1:boxcolor=0x000000@0.7:boxborderw=15" if bg_on else ""
                        part = f"drawtext=fontfile='{font_path}':text='{clean_text}':fontcolor={t_color}:fontsize={f_size}{box_str}:x=(w-text_w)/2+({x_pos}):y=(h-text_h)/2+({y_pos}):enable='between(t,{i},{i+3})'"
                        filter_parts.append(part)
                except:
                    continue

        # 3. ADIM: RENDER VE ÇIKTI
        v_filter = ",".join(filter_parts) if filter_parts else "drawtext=text=' ':x=0:y=0"
        with open(filter_file, "w", encoding="utf-8") as f:
            f.write(v_filter)
        
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-filter_complex_script:v', filter_file,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
            '-c:a', 'aac', '-map', '0', output_path
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
        
