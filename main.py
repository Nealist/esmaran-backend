from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
# MoviePy yerine daha hafif bir mantık deneyeceğiz veya ayar ekleyeceğiz
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.config import change_settings

# ÖNEMLİ: Render gibi yerlerde ImageMagick yolu bazen sorun olur
# Bu kod ImageMagick hatasını bypass etmeye çalışır
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'processed'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def home():
    return "Esmaran AI Motoru Calisiyor!"

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.json
        video_url = data.get('url')
        
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"esmaran_{unique_id}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)

        # ŞİMDİLİK SADECE İNDİRME TESTİ (Motorun çalışıp çalışmadığını anlamak için)
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

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
    
