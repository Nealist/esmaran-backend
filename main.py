import os
import uuid
import yt_dlp
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'processed'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.json
        video_url = data.get('url')
        
        # Siteden gelen rengi temizle ve FFmpeg formatına (0xRRGGBB) çevir
        t_color = data.get('color', '#ffffff').replace('#', '0x')
        b_color = data.get('bg_color', '#000000').replace('#', '0x')
        f_size = data.get('font_size', '28')
        y_val = data.get('y_pos', 0)
        bg_enabled = data.get('bg', True)
        
        unique_id = str(uuid.uuid4())[:8]
        input_file = f"in_{unique_id}.mp4"
        output_name = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

        # 1. Video İndirme
        ydl_opts = {'format': 'best', 'outtmpl': input_file, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 2. FFmpeg Altyazı Yazma (Garantili Hex Renk Sistemi)
        box_cmd = f":box=1:boxcolor={b_color}@0.6" if bg_enabled else ""
        
        # Yazıyı videoya tam senin ayarladığın konumda basar
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-vf', f"drawtext=text='ESMARAN AI':fontcolor={t_color}:fontsize={f_size}{box_cmd}:x=(w-text_w)/2:y=(h-text_h)/2+({y_val})",
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
