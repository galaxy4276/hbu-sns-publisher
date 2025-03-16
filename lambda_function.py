import json
from instagrapi import Client
from instagrapi.types import StoryLink
import os
import tempfile
import logging
import requests


# 로거 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 환경 변수에서 계정 정보 불러오기
ACCOUNT_USERNAME = os.environ.get('INSTAGRAM_USERNAME')
ACCOUNT_PASSWORD = os.environ.get('INSTAGRAM_PASSWORD')
TEST_URI = os.environ.get('TEST_URI', 'https://www.hanbat.ac.kr/bbs/BBSMSTR_000000000050/view.do?nttId=B000000154122Nz1uS2l')
TEST_IMAGE_URL = os.environ.get('TEST_IMAGE_URL', 'https://hbu-automation-content.s3.ap-northeast-2.amazonaws.com/story-image-1.png')

if not ACCOUNT_USERNAME or not ACCOUNT_PASSWORD:
    raise ValueError("Instagram credentials must be set in environment variables")

# CORS 헤더 정의
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST'
}

def upload_story(image_data: str, link: str):
    logger.info("스토리 업로드 시작")
    cl = Client()
    logger.info("인스타그램 클라이언트 생성 완료")
    
    cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
    logger.info("인스타그램 로그인 완료")
    
    # S3 URL에서 이미지 다운로드
    response = requests.get(image_data)
    if response.status_code != 200:
        logger.error("이미지 다운로드 실패")
        raise ValueError("이미지 다운로드 실패")
    
    # /tmp 디렉토리에 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png', dir='/tmp') as temp_file:
        temp_file.write(response.content)
        temp_path = temp_file.name
    logger.info(f"임시 파일 생성 완료: {temp_path}")
    
    try:
        # 스토리 업로드
        cl.photo_upload_to_story(
            path=temp_path,
            links=[StoryLink(webUri=link)],
        )
        logger.info("스토리 업로드 완료")
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info("임시 파일 삭제 완료")

def lambda_handler(event, context):
    logger.info("람다 핸들러 시작")
    
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
            logger.warning("요청 본문 누락")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': '요청 본문이 필요합니다.'
                })
            }

        # JSON 파싱
        request_data = json.loads(event['body'])
        logger.info("요청 데이터:")
        logger.info(request_data)
        
        # base64로 인코딩된 이미지와 링크 추출
        image_data = request_data.get('image')
        link = request_data.get('link')
        
        if not image_data or not link:
            logger.warning("필수 파라미터 누락")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'image와 link가 모두 필요합니다.'
                })
            }
            
        # base64 이미지 데이터에서 헤더 제거
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
            
        upload_story(image_data, link)

        logger.info("스토리 업로드 프로세스 완료")
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': '스토리가 성공적으로 업로드되었습니다.',
                'link': link
            })
        }
        
    except json.JSONDecodeError:
        logger.error("잘못된 JSON 형식")
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({
                'message': '잘못된 JSON 형식입니다.'
            })
        }
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'message': f'오류가 발생했습니다: {str(e)}'
            })
        }
