import json
import os
import logging
import requests
import tempfile
import pyotp
from instagrapi import Client
from instagrapi.types import StoryLink


# 로거 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 환경 변수에서 계정 정보 불러오기
ACCOUNT_USERNAME = os.environ.get('INSTAGRAM_USERNAME')
ACCOUNT_PASSWORD = os.environ.get('INSTAGRAM_PASSWORD')
SESSION_FILE = "/tmp/instagram_session.json"  # 세션 저장 경로
TEST_URI = os.environ.get('TEST_URI', 'https://www.hanbat.ac.kr/bbs/BBSMSTR_000000000050/view.do?nttId=B000000154122Nz1uS2l')
TEST_IMAGE_URL = os.environ.get('TEST_IMAGE_URL', 'https://hbu-automation-content.s3.ap-northeast-2.amazonaws.com/story-image-1.png')

# TOTP 백업 코드 목록
TOTP_SECRETS = [
    "06831475",
    "85279346",
    "10473285",
    "65210487",
    "84256719"
]

if not ACCOUNT_USERNAME or not ACCOUNT_PASSWORD:
    raise ValueError("Instagram 계정 정보가 필요합니다.")

# CORS 헤더 정의
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST'
}

def try_login_with_totp(cl):
    """ 여러 TOTP 시크릿을 순차적으로 시도하며 로그인 """
    last_error = None
    
    for idx, secret in enumerate(TOTP_SECRETS, 1):
        try:
            logger.info(f"🔑 TOTP 시도 #{idx} 진행 중...")
            totp = pyotp.TOTP(secret)
            code = totp.now()
            cl.two_factor_login(code)
            logger.info(f"✅ TOTP #{idx} 인증 성공!")
            return True
        except Exception as e:
            last_error = e
            logger.warning(f"❌ TOTP #{idx} 실패: {str(e)}")
            continue
    
    # 모든 TOTP 시도 실패
    logger.error("❌ 모든 TOTP 인증 시도 실패")
    raise last_error

def login_instagram():
    """ 세션을 유지하며 인스타그램에 로그인 """
    cl = Client()
    
    # 기존 세션 불러오기
    if os.path.exists(SESSION_FILE):
        logger.info("기존 세션 불러오기 시도 중...")
        cl.load_settings(SESSION_FILE)

        try:
            cl.get_timeline_feed()  # 세션이 유효한지 확인
            logger.info("✅ 기존 세션 로그인 성공")
            return cl
        except Exception:
            logger.warning("❌ 세션 만료됨, 다시 로그인 시도")

    # 세션이 없거나 만료되었으면 다시 로그인
    cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
    logger.info("🔑 인스타그램 로그인 성공")

    # 여러 TOTP 코드 시도
    try_login_with_totp(cl)

    # 로그인 후 세션 저장
    cl.dump_settings(SESSION_FILE)
    logger.info("💾 세션 저장 완료")

    return cl

def upload_story(image_url: str, link: str):
    """ 스토리를 업로드하는 함수 """
    logger.info("📤 스토리 업로드 시작")
    cl = login_instagram()  # 로그인 또는 기존 세션 불러오기

    # S3 URL에서 이미지 다운로드
    response = requests.get(image_url)
    if response.status_code != 200:
        logger.error("이미지 다운로드 실패")
        raise ValueError("이미지 다운로드 실패")
    
    # /tmp 디렉토리에 임시 파일 생성
    temp_path = "/tmp/story_image.png"
    with open(temp_path, "wb") as f:
        f.write(response.content)
    logger.info(f"🖼️ 임시 파일 생성 완료: {temp_path}")
    
    try:
        # 스토리 업로드
        cl.photo_upload_to_story(
            path=temp_path,
            links=[{"webUri": link}]
        )
        logger.info("✅ 스토리 업로드 완료")
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info("🗑️ 임시 파일 삭제 완료")

def lambda_handler(event, context):
    """ AWS Lambda 핸들러 """
    logger.info("🚀 람다 핸들러 시작")
    
    # OPTIONS 메소드 요청 처리
    if event.get('httpMethod') == 'OPTIONS':
        logger.info("OPTIONS 요청 처리")
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': ''
        }

    try:
        # JSON 요청 처리
        if 'body' not in event:
            logger.warning("❌ 요청 본문 누락")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': '요청 본문이 필요합니다.'})
            }

        # JSON 파싱
        request_data = json.loads(event['body'])
        logger.info("📩 요청 데이터:")
        logger.info(request_data)
        
        # 이미지 URL과 링크 추출
        image_url = request_data.get('image')
        link = request_data.get('link')
        
        if not image_url or not link:
            logger.warning("⚠️ 필수 파라미터 누락")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'image와 link가 모두 필요합니다.'})
            }
            
        upload_story(image_url, link)

        logger.info("✅ 스토리 업로드 프로세스 완료")
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': '스토리가 성공적으로 업로드되었습니다.',
                'link': link
            })
        }
        
    except json.JSONDecodeError:
        logger.error("❌ 잘못된 JSON 형식")
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'message': '잘못된 JSON 형식입니다.'})
        }
    except Exception as e:
        logger.error(f"⚠️ 처리 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': f'오류가 발생했습니다: {str(e)}'})
        }
