import os
import uuid
import yt_dlp
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
        t_color = data.get('color', 'white').replace('#', '0x') # FFmpeg formatı
        b_color = data.get('bg_color', 'black').replace('#', '0x')
        
        unique_id = str(uuid.uuid4())[:8]
        input_path = f"in_{unique_id}.mp4"
        output_filename = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)

        # 1. VİDEOYU İNDİR
        ydl_opts = {'format': 'best', 'outtmpl': input_path}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 2. ALTYAZIYI FFmpeg İLE BAS (En Sağlam Yol)
        # ImageMagick gerektirmez, doğrudan sistem komutu kullanır
        y_pos = data.get('y', 100) # Siteden gelen Y konumu
        
        # Basit bir yazı basma komutu (drawtext)
        cmd = (
            f'ffmpeg -i {input_path} -vf "drawtext=text=\'ESMARAN AI\':fontcolor={t_color}:'
            f'fontsize=24:box=1:boxcolor={b_color}@0.8:x=(w-text_w)/2:y={y_pos}+200" '
            f'-codec:a copy {output_path}'
        )
        
        os.system(cmd)

        # Temizlik
        if os.path.exists(input_path):
            os.remove(input_path)

        return jsonify({
            "status": "success",
            "download_url": f"https://{request.host}/download/{output_filename}"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
