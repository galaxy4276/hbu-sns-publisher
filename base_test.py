import base64
from requests_toolbelt.multipart import decoder

# Content-Type 헤더에서 boundary 추출
content_type_header = mock_request['headers'].get("Content-Type", "")

if "boundary=" in content_type_header:
    boundary = content_type_header.split("boundary=")[-1]
elif "multipart/form-data" in content_type_header:
    # API Gateway가 boundary를 제거하는 경우 수동으로 추출
    boundary = content_type_header.split(";")[-1].strip().replace("boundary=", "")
else:
    raise ValueError("Missing boundary in Content-Type header")

# Base64 디코딩 후 UTF-8 변환
postdata = base64.b64decode(mock_request['body']).decode('utf-8', errors='ignore')

# MultipartDecoder로 파싱
multipart_data = decoder.MultipartDecoder(postdata.encode(), f"multipart/form-data; boundary={boundary}")

lst = []
for part in multipart_data.parts:
    content_disposition = part.headers.get(b"Content-Disposition", b"").decode()
    if "filename=" in content_disposition:
        lst.append(f"File received: {content_disposition}")
    else:
        lst.append(part.content.decode('utf-8', errors='ignore'))  # UTF-8로 디코딩

print(lst)  # 파싱된 데이터 출력
