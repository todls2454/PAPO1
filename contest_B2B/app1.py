from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image as PILImage, ImageEnhance
import uuid
import logging

# .env 파일에서 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 폴더 생성
UPLOAD_FOLDER = 'static/uploads'
PROCESSED_FOLDER = 'static/processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Gemini API 초기화
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY가 없습니다!")
    logger.error("💡 .env 파일에 GEMINI_API_KEY=your-key를 추가하세요")
    logger.error("💡 API 키: https://aistudio.google.com/app/apikey")
    exit(1)

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')
    logger.info("✅ Gemini API 연결 성공!")
except Exception as e:
    logger.error(f"❌ Gemini API 실패: {e}")
    exit(1)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "ai": "Gemini API",
        "message": "서버 정상 작동 중"
    })

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/edit_image', methods=['POST'])
def edit_image():
    try:
        logger.info("🎯 이미지 업로드 시작...")
        
        if 'image' not in request.files:
            return jsonify({"error": "이미지가 없습니다"}), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({"error": "파일을 선택하세요"}), 400

        # 파일 저장
        file_ext = os.path.splitext(image_file.filename)[1].lower()
        if file_ext not in ['.jpg', '.jpeg', '.png']:
            return jsonify({"error": "JPG, PNG 파일만 가능합니다"}), 400
        
        # 원본 파일 저장
        original_filename = f"original_{uuid.uuid4().hex}{file_ext}"
        original_path = os.path.join(UPLOAD_FOLDER, original_filename)
        image_file.save(original_path)
        logger.info(f"📁 원본 저장: {original_path}")

        # 이미지 개선 처리
        try:
            logger.info("🎨 이미지 개선 시작...")
            
            # PIL로 이미지 열기
            pil_image = PILImage.open(original_path)
            
            # RGB 변환
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 크기 조정
            pil_image.thumbnail((1024, 1024), PILImage.Resampling.LANCZOS)
            
            # 이미지 개선
            enhanced_image = enhance_pet_image(pil_image)
            
            # 개선된 이미지 저장
            enhanced_filename = f"enhanced_{uuid.uuid4().hex}.png"
            enhanced_path = os.path.join(PROCESSED_FOLDER, enhanced_filename)
            enhanced_image.save(enhanced_path, 'PNG', quality=95)
            
            logger.info(f"✅ 개선 완료: {enhanced_path}")
            
            # Gemini로 이미지 분석 (선택적)
            analysis = analyze_with_gemini(pil_image)
            
            return jsonify({
                "message": "이미지 개선 완료!",
                "image_path": f"processed/{enhanced_filename}",
                "original_path": f"uploads/{original_filename}",
                "analysis": analysis,
                "ai_used": "Gemini API + PIL"
            })
            
        except Exception as e:
            logger.error(f"❌ 이미지 처리 실패: {e}")
            return jsonify({"error": f"이미지 처리 실패: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"❌ 전체 오류: {e}")
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500

def enhance_pet_image(image):
    """반려동물 사진 개선"""
    try:
        enhanced = image.copy()
        
        # 1. 밝기 개선
        brightness = ImageEnhance.Brightness(enhanced)
        enhanced = brightness.enhance(1.2)
        
        # 2. 대비 개선  
        contrast = ImageEnhance.Contrast(enhanced)
        enhanced = contrast.enhance(1.1)
        
        # 3. 색상 강화
        color = ImageEnhance.Color(enhanced)
        enhanced = color.enhance(1.15)
        
        # 4. 선명도 개선
        sharpness = ImageEnhance.Sharpness(enhanced)
        enhanced = sharpness.enhance(1.05)
        
        logger.info("✅ 이미지 필터 적용 완료")
        return enhanced
        
    except Exception as e:
        logger.error(f"❌ 필터 적용 실패: {e}")
        return image

def analyze_with_gemini(image):
    """Gemini로 이미지 분석 (선택적)"""
    try:
        logger.info("🤖 Gemini 이미지 분석...")
        
        prompt = """
        이 반려동물 사진을 간단히 분석해주세요:
        1. 동물 종류
        2. 특징
        3. 사진 품질 평가
        
        한국어로 3-4줄 정도로 간단히 답변해주세요.
        """
        
        response = model.generate_content([prompt, image])
        
        if response and response.text:
            logger.info("✅ Gemini 분석 완료")
            return response.text
        else:
            return "분석 결과를 가져올 수 없습니다."
            
    except Exception as e:
        logger.error(f"❌ Gemini 분석 실패: {e}")
        return "이미지 분석 중 오류가 발생했습니다."

if __name__ == '__main__':
    logger.info("🚀 Gemini Flask 서버 시작!")
    logger.info("🤖 AI: Gemini API 사용")
    logger.info("🌐 주소: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)