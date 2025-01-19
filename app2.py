import streamlit as st
import anthropic
import os
import tempfile
from PyPDF2 import PdfReader
import telebot
import datetime
import json  # 추가된 import
import requests  # requests 모듈도 필요합니다


# API 키 설정
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
        KAKAO_TOKEN = st.secrets.get(
            "KAKAO_TOKEN", "your-kakao-token-here"
        )  # 기본값 설정
    else:
        # 로컬 테스트용
        ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
        KAKAO_TOKEN = os.getenv("KAKAO_TOKEN", "your-kakao-token-here")
except Exception as e:
    st.error(f"API 키 설정 중 오류 발생: {str(e)}")
    ANTHROPIC_API_KEY = "your-api-key-here"
    KAKAO_TOKEN = "your-kakao-token-here"


# Claude 클라이언트 초기화
client = anthropic.Client(api_key=ANTHROPIC_API_KEY)


# 텔레그램 봇 설정
TELEGRAM_TOKEN = "7659346262:AAHdpHX1kN1vUxXO2H0sdFkXkOs3SQpsA3Q"
TELEGRAM_CHAT_ID = "5767743818"  # 텔레그램 봇으로부터 받은 chat_id
bot = telebot.TeleBot(TELEGRAM_TOKEN)


def get_text_from_pdf(pdf_path):
    """PDF 파일에서 텍스트 추출"""
    try:
        pdf_reader = PdfReader(pdf_path)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"PDF 파일 읽기 오류: {str(e)}")
        return ""


def send_telegram_reservation(customer_name, reservation_time, departure, destination):
    """텔레그램으로 예약 정보 전송"""
    try:
        message = f"""🚗 새로운 대리운전 예약
        
고객명: {customer_name}
예약시간: {reservation_time}
출발지: {departure}
도착지: {destination}

예약시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return True
    except Exception as e:
        st.error(f"텔레그램 메시지 전송 실패: {str(e)}")
        return False


def parse_reservation_time(time_str):
    """예약 시간 문자열을 파싱하는 함수"""
    try:
        # 다양한 형식 시도
        formats = [
            "%Y-%m-%d %H:%M",  # 2025-01-20 15:30
            "%Y-%m-%d",  # 2025-01-20
            "%m-%d %H:%M",  # 01-20 15:30
            "%Y.%m.%d %H:%M",  # 2025.01.20 15:30
            "%Y.%m.%d",  # 2025.01.20
        ]

        for fmt in formats:
            try:
                parsed_time = datetime.datetime.strptime(time_str, fmt)
                # 년도가 없는 형식인 경우 현재 년도 사용
                if fmt in ["%m-%d %H:%M"]:
                    current_year = datetime.datetime.now().year
                    parsed_time = parsed_time.replace(year=current_year)
                # 시간이 없는 경우 현재 시간 사용
                if fmt in ["%Y-%m-%d", "%Y.%m.%d"]:
                    current_time = datetime.datetime.now()
                    parsed_time = parsed_time.replace(
                        hour=current_time.hour, minute=current_time.minute
                    )
                return parsed_time
            except ValueError:
                continue

        # 어떤 형식도 맞지 않으면 현재 시간 반환
        return datetime.datetime.now()
    except Exception:
        return datetime.datetime.now()


def send_kakao_message(customer_name, reservation_time, departure, destination):
    """카카오톡으로 예약 정보 전송"""
    try:
        # 예약 시간 파싱
        parsed_time = parse_reservation_time(reservation_time)
        formatted_time = parsed_time.strftime("%Y-%m-%d %H:%M")

        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {"Authorization": f"Bearer {KAKAO_TOKEN}"}

        template = {
            "object_type": "text",
            "text": f"""🚗 대리운전 예약 알림

예약번호: {abs(hash(f"{customer_name}{formatted_time}")) % 1000000:06d}
고객명: {customer_name}
예약시간: {formatted_time}
출발지: {departure}
도착지: {destination}

예약시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}""",
            "link": {
                "web_url": "https://example.com/booking-status",
                "mobile_web_url": "https://example.com/booking-status",
            },
            "button_title": "예약 확인하기",
        }

        data = {"template_object": json.dumps(template)}

        response = requests.post(url, headers=headers, data=data)
        if response.status_code != 200:
            raise Exception(f"카카오톡 메시지 전송 실패: {response.text}")
        return True
    except Exception as e:
        st.error(f"카카오톡 메시지 전송 실패: {str(e)}")
        return False


def send_reservation(customer_name, reservation_time, departure, destination):
    """텔레그램과 카카오톡으로 예약 정보 전송"""
    telegram_success = send_telegram_reservation(
        customer_name, reservation_time, departure, destination
    )
    kakao_success = send_kakao_message(
        customer_name, reservation_time, departure, destination
    )

    if telegram_success and kakao_success:
        return True, "모든 메시지가 성공적으로 전송되었습니다!"
    elif telegram_success:
        return True, "텔레그램 메시지만 전송되었습니다."
    elif kakao_success:
        return True, "카카오톡 메시지만 전송되었습니다."
    else:
        return False, "메시지 전송에 실패했습니다."


def load_qa_documents():
    """QA PDF 문서들을 자동으로 로드"""
    qa_text = ""
    try:
        pdf_files = [
            f for f in os.listdir(".") if f.startswith("qa") and f.endswith(".pdf")
        ]

        if not pdf_files:
            st.error("PDF 파일을 찾을 수 없습니다.")
            return ""

        pdf_files.sort()

        for pdf_file in pdf_files:
            content = get_text_from_pdf(pdf_file)
            if content:
                qa_text += content + "\n\n"

        if qa_text:
            st.markdown(
                '<div class="success-msg" style="padding: 1rem; border-radius: 0.5rem; background-color: #d4edda; color: black;">당신은 DS라온 대리운전의 친절하고 전문적인 상담원입니다. 궁금하신 점을 물어보세요. 😊</div>',
                unsafe_allow_html=True
            )


        return qa_text
    except Exception as e:
        st.error("문서 로드 중 오류가 발생했습니다.")
        return ""


def get_claude_response(messages, prompt):
    """Claude API를 사용하여 응답 생성"""
    try:
        context = """당신은 DS라온 대리운전의 전문 상담원입니다. 다음 지침을 따라 응답해주세요:

        1. 답변 스타일:
        - '네, 안녕하세요. DS라온 대리운전입니다.'로 시작
        - 항상 친절하고 전문적인 어투 사용
        - 정확한 정보와 구체적인 설명 제공
        - 추가 문의사항이 있을 수 있다는 것을 언급
        
        2. 예약 관련 답변:
        - 구체적인 예약 절차 설명
        - 필요한 정보(출발지, 도착지, 시간 등) 문의
        - 예상 소요시간과 예상 요금 안내 가능함을 언급
        - 예약 확정 시 문자 안내됨을 설명

        3. 가격 문의:
        - 기본요금과 거리별 요금 체계 설명
        - 할증 요금(심야, 날씨, 공휴일 등) 안내
        - 결제 방법 설명 (현금, 카드, 앱 결제 등)

        4. 서비스 관련:
        - 24시간 연중무휴 운영 강조
        - 실시간 위치 확인 가능함을 안내
        - 안전한 운행과 보험 보장 설명
        - 고객 만족 보장 강조
        
        
        5. 만약 고객이 예약을 원하면 다음 정보를 반드시 물어보세요:
        - 고객명
        - 예약시간
        - 출발지 주소
        - 도착지 주소
        
        이 정보들을 모두 받으면 '예약 정보를 전달하겠습니다.'라고 답변해주세요.
       

        참고 문서 내용:
        {st.session_state.get('qa_text', '문서 내용이 없습니다.')}

        위의 내용을 기반으로 다음 질문에 답변해주세요: {prompt}
        """

        # 메시지 목록 생성
        message_list = [{"role": "user", "content": context}]

        # 이전 대화 기록 추가
        for msg in messages:
            if msg["role"] != "system":  # system 역할 메시지 제외
                message_list.append({"role": msg["role"], "content": msg["content"]})

        # Claude API 호출
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=message_list,
            max_tokens=1000,
            temperature=0.7,
        )

        return response.content[0].text
    except Exception as e:
        if "rate_limit_exceeded" in str(e):
            return "죄송합니다. 잠시 후 다시 시도해주시기 바랍니다."
        st.error(f"에러가 발생했습니다: {str(e)}")
        return None


def main():
    # 페이지 설정
    st.set_page_config(
        page_title="DS라온 대리운전 QA 챗봇",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=None,
    )

    
    # 테마 설정을 위한 CSS 주입
    st.markdown("""
        <style>
            :root {
                --primary-color: #ff4b4b;
            }
            .stApp {
                background-color: white;
            }
            .st-emotion-cache-1v0mbdj {
                background-color: white;
            }
        </style>
    """, unsafe_allow_html=True)

    # 스타일 적용
    st.markdown(
        """
        <style>
            .stApp {
                background-color: white;
            }
            .stButton button {
                background-color: #ff4b4b;
                color: white;
                border-radius: 5px;
                border: none;
                padding: 0.5rem 1rem;
            }
            .stButton button:hover {
                background-color: #ff3333;
            }
            div[data-testid="stExpander"] {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
            }
            .st-emotion-cache-16txtl3 {
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
                background-color: white;
            }
            div.st-emotion-cache-16txtl3 p {
                color: #31333F;
            }
            .st-emotion-cache-1v0mbdj {
                width: 100%;
            }
            .stTextInput input {
                border: 1px solid #e0e0e0;
            }
            /* AI 챗봇 답변 스타일 */
            .st-emotion-cache-1gulkj5 {
                background-color: #FFF9C4 !important;  /* 연한 노란색 배경 */
            }
            
            /* AI 챗봇 텍스트 색상 */
            .st-emotion-cache-1gulkj5 p {
                color: black !important;  /* 검정색 텍스트 */
            }
            
            /* AI 아이콘 배경 */
            .st-emotion-cache-1v0mbdj {
                background-color: #FFF9C4 !important;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # 예약하기 버튼
    if st.button("🚗 예약하기", help="대리운전 예약하기"):
        show_reservation_form()

    # 최초 실행 시 QA 문서 로드
    if "qa_text" not in st.session_state:
        st.session_state["qa_text"] = load_qa_documents()

    # QA 문서가 비어있는지 확인
    if not st.session_state.get("qa_text", "").strip():
        st.error("QA 문서가 비어있습니다. PDF 파일을 확인해주세요.")
        return

    # 메인 채팅 인터페이스
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 채팅 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 답변 생성
        with st.chat_message("assistant"):
            with st.spinner("답변을 생성하고 있습니다..."):
                response = get_claude_response(st.session_state.messages, prompt)
                if response:
                    if "죄송합니다" in response:  # rate limit 에러 응답인 경우
                        st.warning(response)
                    else:
                        st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )


def show_reservation_form():
    """예약 폼을 표시하는 함수"""
    with st.expander("대리운전 예약", expanded=True):
        st.header("예약 정보 입력")
        with st.form("reservation_form", clear_on_submit=False):
            customer_name = st.text_input("고객명")

            # 날짜 선택기
            selected_date = st.date_input(
                "예약 날짜",
                min_value=datetime.datetime.now().date(),
                format="YYYY-MM-DD",
            )

            # 시간 선택기
            selected_time = st.time_input(
                "예약 시간", datetime.time(hour=21, minute=0)  # 기본값 21:00
            )

            # 날짜와 시간 결합
            reservation_time = datetime.datetime.combine(selected_date, selected_time)

            departure = st.text_input("출발지 주소")
            destination = st.text_input("도착지 주소")

            submit_col1, submit_col2 = st.columns([1, 4])
            with submit_col1:
                submit_button = st.form_submit_button("예약하기")
            with submit_col2:
                if submit_button:
                    if customer_name and departure and destination:
                        formatted_time = reservation_time.strftime("%Y-%m-%d %H:%M")
                        success, message = send_reservation(
                            customer_name, formatted_time, departure, destination
                        )
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.warning("모든 필드를 입력해주세요.")


if __name__ == "__main__":
    main()
