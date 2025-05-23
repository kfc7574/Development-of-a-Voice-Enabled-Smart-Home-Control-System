from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import subprocess
import os

app = Flask(__name__)
CORS(app, supports_credentials=True)

load_dotenv()  # 載入 .env 檔案

app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')

mysql = MySQL(app)

UPLOAD_FOLDER = 'backend/face/face_dataset/faces'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/ping")
def ping():
    return "pong"

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        name = data.get('name')
        pwd = data.get('pwd')
        via = data.get('via')  # 用來判斷是否為人臉登入

        if not name:
            return jsonify(success=False, error="Missing 'name'")

        cursor = mysql.connection.cursor()

        if via == 'face':
            # 臉部辨識只驗證名字存在
            cursor.execute("SELECT * FROM user WHERE name = %s", (name,))
        else:
            # 一般登入要驗證帳密
            if not pwd:
                return jsonify(success=False, error="Missing 'pwd'")
            cursor.execute("SELECT * FROM user WHERE name = %s AND pwd = %s", (name, pwd))

        result = cursor.fetchall()
        cursor.close()

        if result:
            return jsonify(success=True)
        else:
            return jsonify(success=False)

    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/uploadImagePath', methods=['POST'])
def upload_image_path():
    try:
        if 'image' not in request.files:
            return jsonify(success=False, error="No file part")

        file = request.files['image']
        if file.filename == '':
            return jsonify(success=False, error="No selected file")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace("\\", "/")
            file.save(save_path)

            script_path = 'backend/face/face_recognition/opencv_realtime.py'
            result = subprocess.run(
                ['python', script_path, '--image_path', save_path],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                recognized_name = result.stdout.strip().split('\n')[-1]

                # 使用 via=face 呼叫 login
                login_response = app.test_client().post('/login', json={
                    'name': recognized_name,
                    'via': 'face'
                })

                login_data = login_response.get_json()

                if login_data.get('success'):
                    return jsonify(success=True, username=recognized_name)
                else:
                    return jsonify(success=False, error="Login failed")
            else:
                return jsonify(success=False, error="Face recognition script failed.")

        else:
            return jsonify(success=False, error="Invalid file format")

    except Exception as e:
        return jsonify(success=False, error=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)