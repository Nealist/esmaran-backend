from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

app = Flask(__name__)
CORS(app)

# Videoların geçici olarak tutulacağı klasör
UPLOAD_FOLDER = 'processed_videos'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.json
        video_url = data.get('url')
        t_color = data.get('color', 'white')
        b_color = data.get('bg_color', 'black')
        f_size = int(data.get('font_size', 24))
        # Siteden gelen X ve Y koordinatları (Örn: {x: 50, y: 100})
        pos_x = data.get('x', 0)
        pos_y = data.get('y', 0)

        unique_id = str(uuid.uuid4())[:8]
        input_filename = f"input_{unique_id}.mp4"
        output_filename = f"output_{unique_id}.mp4"

        # 1. VİDEOYU İNDİR (yt-dlp)
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': input_filename,
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 2. VİDEOYU İŞLE (MoviePy)
        video = VideoFileClip(input_filename)
        
        # Altyazı klibi (Burada font dosyasının sunucuda olması gerekir, şimdilik standart font)
        txt_clip = TextClip("ESMARAN AI", fontsize=f_size, color=t_color, bg_color=b_color)
        
        # Sitedeki sürükleme mantığını MoviePy'ye aktarıyoruz
        # Not: Koordinat hesaplaması ön izleme ekranı ile video çözünürlüğü arasında oranlanmalıdır
        txt_clip = txt_clip.set_start(0).set_duration(video.duration).set_pos((pos_x, pos_y))

        final_video = CompositeVideoClip([video, txt_clip])
        final_video.write_videofile(os.path.join(UPLOAD_FOLDER, output_filename), fps=video.fps, codec="libx264")

        # Temizlik
        video.close()
        os.remove(input_filename)

        return jsonify({
            "status": "success",
            "download_url": f"https://your-api-link.render.com/download/{output_filename}"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
