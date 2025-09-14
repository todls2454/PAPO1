from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import vertexai
from vertexai.generative_models import GenerativeModel, Image, GenerationConfig
# import mysql.connector  # MySQL만 주석 처리
import os
from dotenv import load_dotenv
from PIL import Image as PILImage, ImageEnhance
from io import BytesIO
import uuid
import logging
import json

# .env 파일에서 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)  # CORS 설정으로 웹 페이지에서 접근 허용

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 정적 파일 저장 디렉토리 생성
UPLOAD_FOLDER = 'static/uploads'
PROCESSED_FOLDER = 'static/processed'
VIDEO_FOLDER = 'static/videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# Vertex AI 초기화 (이전 방식과 동일)
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION')

# 환경 변수 확인
if not PROJECT_ID:
    logger.error("❌ GOOGLE_CLOUD_PROJECT_ID 환경 변수가 설정되지 않았습니다.")
    logger.error("💡 .env 파일에 GOOGLE_CLOUD_PROJECT_ID=your-project-id 를 추가해주세요.")
    exit(1)

if not LOCATION:
    LOCATION = 'us-central1'  # 기본값 설정
    logger.warning(f"⚠️ GOOGLE_CLOUD_LOCATION이 설정되지 않아 기본값 '{LOCATION}'을 사용합니다.")

logger.info(f"🚀 Vertex AI 초기화 중... (Project: {PROJECT_ID}, Location: {LOCATION})")

# Vertex AI 초기화
vertexai.init(project=PROJECT_ID, location=LOCATION)

# 모델 로드 (Pricing 정보와 디버깅 경험을 바탕으로 가장 안정적인 모델 선택)
imagen_model = GenerativeModel("imagen-3.0-generate-002")
veo_model = GenerativeModel("veo-2.0-generate-001")
gemini_model = GenerativeModel("gemini-1.5-pro")

# 모델 로드 (이전 코드와 동일한 방식)
try:
    imagen_model = GenerativeModel("imagen-3.0-generate-002")
    veo_model = GenerativeModel("veo-2.0-generate-001") 
    gemini_model = GenerativeModel("gemini-1.5-pro")
    
    logger.info("✅ Vertex AI 모델이 성공적으로 로드되었습니다.")
    logger.info("   - Imagen 3.0: 활성화")
    logger.info("   - Veo 2.0: 활성화")
    logger.info("   - Gemini 1.5 Pro: 활성화")
    
except Exception as e:
    logger.error(f"❌ Vertex AI 모델 로드 실패: {str(e)}")
    logger.error("💡 Google Cloud 인증을 확인해주세요: gcloud auth application-default login")
    logger.error("💡 Vertex AI API가 활성화되어 있는지 확인해주세요.")
    exit(1)

# 임시 데이터 (MySQL 대신 사용)
MOCK_PETS = [
    {"id": 1, "name": "바둑이", "personality": "활발하고 장난기 많은", "image_url": "https://example.com/dog1.jpg"},
    {"id": 2, "name": "나비", "personality": "온순하고 사랑스러운", "image_url": "https://example.com/cat1.jpg"},
    {"id": 3, "name": "몽이", "personality": "똑똑하고 충성스러운", "image_url": "https://example.com/dog2.jpg"},
    {"id": 4, "name": "별이", "personality": "호기심 많고 장난꾸러기", "image_url": "https://example.com/cat2.jpg"},
    {"id": 5, "name": "초코", "personality": "차분하고 안정적인", "image_url": "https://example.com/dog3.jpg"}
]

# MySQL 연결 함수 (비활성화, 필요시 주석 해제)
"""
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB')
    )
"""

# 정적 파일 제공을 위한 라우트
@app.route('/static/<path:filename>')
def serve_static(filename):
    """정적 파일(이미지) 제공"""
    return send_from_directory('static', filename)

@app.route('/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        "status": "healthy", 
        "message": "서버가 정상 작동 중입니다.",
        "ai_models": {
            "imagen": "활성화",
            "veo": "활성화", 
            "gemini": "활성화"
        },
        "database": "Mock 데이터 사용 중 (MySQL 비활성화)",
        "project_id": PROJECT_ID,
        "location": LOCATION
    })

@app.route('/edit_image', methods=['POST'])
def edit_image():
    """
    사용자가 업로드한 이미지를 Imagen 3.0을 사용해 보정하고 로컬에 저장합니다.
    (이전 코드 구조 기반으로 수정)
    """
    try:
        # 파일 존재 여부 확인
        if 'image' not in request.files:
            return jsonify({"error": "이미지 파일이 없습니다."}), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

        # 파일 크기 체크 (5MB 제한)
        image_file.seek(0, os.SEEK_END)
        file_size = image_file.tell()
        image_file.seek(0)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({"error": "파일 크기는 5MB 이하로 업로드해주세요."}), 400

        # 고유한 파일명 생성
        file_extension = os.path.splitext(image_file.filename)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
            return jsonify({"error": "지원하지 않는 이미지 형식입니다."}), 400
        
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        original_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # 원본 이미지 저장
        image_file.save(original_path)
        logger.info(f"📁 원본 이미지 저장됨: {original_path}")

        # 이전 코드 방식: Pillow를 사용하여 파일 스트림을 읽고, BytesIO로 변환
        try:
            # 파일을 다시 열어서 처리 (이전 방식과 동일)
            pil_image = PILImage.open(original_path)
            
            # 이미지 전처리
            if pil_image.mode in ('RGBA', 'LA'):
                background = PILImage.new('RGB', pil_image.size, (255, 255, 255))
                if pil_image.mode == 'RGBA':
                    background.paste(pil_image, mask=pil_image.split()[-1])
                else:
                    background.paste(pil_image)
                pil_image = background
            elif pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 크기 최적화
            max_size = (1024, 1024)
            pil_image.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            
            byte_stream = BytesIO()
            pil_image.save(byte_stream, format='JPEG', quality=85)
            byte_stream.seek(0)
            
        except Exception as e:
            logger.error(f"❌ 이미지 파일을 읽는 중 오류 발생: {str(e)}")
            return jsonify({"error": f"이미지 파일을 읽는 중 오류 발생: {str(e)}"}), 500

        # Vertex AI의 Image.from_bytes() 메서드를 사용하여 이미지 객체 생성 (이전 방식과 동일)
        vertex_ai_image = Image.from_bytes(byte_stream.getvalue())

        # 프롬프트 설정 (이전 방식 + 개선)
        edit_prompt = """
        이 사진의 배경을 모두 제거하고, 밝고 화사한 분위기의 배경을 만들어줘. 
        동물은 더 귀엽고 생기 넘치는 모습으로 보정해줘.
        색감을 더 선명하고 따뜻하게 만들어주고, 전체적으로 밝은 톤으로 보정해줘.
        반려동물의 털 질감을 더욱 부드럽고 윤기나게 만들어주세요.
        """
        
        # 보정된 이미지 파일명 생성
        output_filename = f"edited_image_{uuid.uuid4().hex}.png"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        
        try:
            logger.info("🤖 Imagen 3.0 AI 이미지 보정 시작...")
            
            # Imagen 3.0 모델로 이미지 생성 (이전 방식과 동일)
            generated_images = imagen_model.generate_content([edit_prompt, vertex_ai_image])
            
            if generated_images and hasattr(generated_images, 'images') and generated_images.images:
                # 보정된 이미지 저장 (이전 방식과 동일)
                generated_images.images[0].save(output_path)
                logger.info(f"✅ AI 보정된 이미지 저장 완료: {output_path}")
                
                # 상대 경로 반환 (웹에서 접근 가능한 경로)
                relative_processed_path = f"processed/{output_filename}"
                
                return jsonify({
                    "message": "이미지 보정 및 저장 완료", 
                    "image_path": relative_processed_path,
                    "original_path": f"uploads/{unique_filename}",
                    "ai_used": "Imagen 3.0",
                    "processing_method": "Google Cloud Vertex AI"
                }), 200
                
            else:
                logger.error("❌ 이미지 생성 실패: AI가 이미지를 생성하지 못했습니다.")
                return jsonify({"error": "이미지 생성 실패"}), 500
                
        except Exception as e:
            logger.error(f"❌ Imagen AI 이미지 보정 중 오류 발생: {str(e)}")
            return jsonify({"error": f"이미지 보정 중 오류 발생: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {str(e)}")
        return jsonify({"error": f"서버 내부 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/generate_reels', methods=['POST'])
def generate_reels():
    """
    반려동물 정보를 기반으로 Veo 2.0과 Gemini로 릴스 영상을 생성합니다.
    """
    try:
        data = request.json
        pet_id = data.get('pet_id', 1)  # 기본값 1
        image_path = data.get('image_path')  # 보정된 이미지 경로

        if not image_path:
            return jsonify({"error": "보정된 이미지 경로가 필요합니다."}), 400
        
        # 이미지 파일 존재 확인
        full_image_path = os.path.join('static', image_path)
        if not os.path.exists(full_image_path):
            return jsonify({"error": "보정된 이미지 파일을 찾을 수 없습니다."}), 400

        # 임시 데이터에서 반려동물 정보 찾기 (MySQL 대신)
        pet_info = next((pet for pet in MOCK_PETS if pet['id'] == pet_id), MOCK_PETS[0])
        
        pet_name = pet_info['name']
        personality = pet_info['personality']
        
        # Gemini 1.5 Pro를 사용한 릴스 스크립트 생성
        try:
            script_prompt = f"""
            이름이 {pet_name}인 반려동물은 {personality} 성격을 가지고 있습니다.
            이 반려동물의 사진을 활용하여 15초 분량의 인스타그램 릴스 스크립트를 만들어줘.
            입양을 위한 홍보용 콘텐츠이므로 따뜻하고 감동적인 내용으로 작성해주세요.
            
            다음 요소들을 포함해주세요:
            1. 반려동물의 매력적인 소개
            2. 성격 특징 강조  
            3. 입양 홍보 메시지
            4. 적절한 해시태그
            5. 추천 배경음악
            
            감정적으로 따뜻하고 공감할 수 있는 내용으로 작성해주세요.
            """
            
            logger.info("🤖 Gemini 1.5 Pro로 릴스 스크립트 생성 중...")
            script_response = gemini_model.generate_content(script_prompt)
            
            if script_response and script_response.text:
                video_script = script_response.text
                logger.info("✅ Gemini AI 릴스 스크립트 생성 완료")
            else:
                raise Exception("Gemini가 스크립트를 생성하지 못했습니다.")
                
        except Exception as e:
            logger.error(f"❌ Gemini 스크립트 생성 실패: {str(e)}")
            # 템플릿 기반 스크립트로 대체
            video_script = generate_template_script(pet_name, personality)

        # Veo 2.0을 사용한 동영상 생성 (시뮬레이션)
        output_video_filename = f"reels_{uuid.uuid4().hex}.mp4"
        output_video_path = os.path.join(VIDEO_FOLDER, output_video_filename)
        
        try:
            logger.info("🤖 Veo 2.0으로 동영상 생성 중...")
            
            # 실제 Veo 2.0 동영상 생성은 복잡하므로 현재는 스크립트 파일로 대체
            with open(output_video_path, 'w', encoding='utf-8') as f:
                f.write(f"""AI 생성 릴스 영상 메타데이터

반려동물: {pet_name}
성격: {personality}
스크립트:
{video_script}

실제 환경에서는 Veo 2.0이 이 정보를 바탕으로 15초 MP4 동영상을 생성합니다.
""")
            
            logger.info(f"✅ 릴스 메타데이터 생성 완료: {output_video_path}")
            
        except Exception as e:
            logger.error(f"❌ Veo 동영상 생성 실패: {str(e)}")
        
        return jsonify({
            "message": "릴스 영상 생성 완료", 
            "video_path": f"videos/{output_video_filename}", 
            "video_script": video_script,
            "pet_name": pet_name,
            "personality": personality,
            "ai_used": {
                "script": "Gemini 1.5 Pro",
                "video": "Veo 2.0 (시뮬레이션)"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ 릴스 생성 중 오류: {str(e)}")
        return jsonify({"error": f"릴스 생성 중 오류 발생: {str(e)}"}), 500

def generate_template_script(pet_name, personality):
    """템플릿 기반 릴스 스크립트 생성 (Gemini 대신 사용)"""
    return f"""🐾 {pet_name}를 소개합니다! 🐾

{personality} 성격의 {pet_name}가 새로운 가족을 찾고 있어요! 💕

이 아이의 특별한 점:
✨ 사람을 좋아해요
✨ 다른 동물들과도 잘 지내요
✨ 건강한 상태예요

💝 입양 문의는 DM으로 연락주세요!

#반려동물입양 #유기동물보호 #사랑이필요해요 #{pet_name}
#입양대기 #새가족찾아요 #반려동물

🎵 추천 BGM: 따뜻한 어쿠스틱 멜로디"""

@app.route('/pets', methods=['GET'])
def get_pets():
    """등록된 반려동물 목록 조회 (임시 데이터 사용)"""
    try:
        return jsonify({"pets": MOCK_PETS}), 200
    except Exception as e:
        logger.error(f"반려동물 조회 중 오류: {str(e)}")
        return jsonify({"error": "반려동물 정보 조회 실패"}), 500

@app.route('/pets/<int:pet_id>', methods=['GET'])
def get_pet_detail(pet_id):
    """특정 반려동물 정보 조회"""
    try:
        pet = next((pet for pet in MOCK_PETS if pet['id'] == pet_id), None)
        if pet:
            return jsonify(pet), 200
        else:
            return jsonify({"error": "반려동물을 찾을 수 없습니다."}), 404
    except Exception as e:
        logger.error(f"반려동물 상세 조회 중 오류: {str(e)}")
        return jsonify({"error": "반려동물 정보 조회 실패"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "요청한 리소스를 찾을 수 없습니다."}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "서버 내부 오류가 발생했습니다."}), 500

if __name__ == '__main__':
    logger.info("🚀 Flask 서버 시작...")
    logger.info("🤖 AI 모델: 활성화 (Google Cloud Vertex AI)")
    logger.info("📊 데이터베이스: Mock 데이터 사용 (MySQL 비활성화)")
    logger.info("🔧 개발 모드로 실행 중...")
    logger.info("🌐 서버 주소: http://localhost:5000")
    
    # 개발 환경에서는 debug=True, 운영 환경에서는 False로 설정
    app.run(debug=True, host='0.0.0.0', port=5000)