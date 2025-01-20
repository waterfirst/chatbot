import streamlit as st
import anthropic
import os
import tempfile
from PyPDF2 import PdfReader
import telebot
import datetime
import json
import requests

# API 키 설정
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
        KAKAO_TOKEN = st.secrets.get("KAKAO_TOKEN", "your-kakao-token-here")
    else:
        ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
        KAKAO_TOKEN = os.getenv("KAKAO_TOKEN", "your-kakao-token-here")
except Exception as e:
    st.error(f"API 키 설정 오류: {str(e)}")
    ANTHROPIC_API_KEY = "your-api-key-here"
    KAKAO_TOKEN = "your-kakao-token-here"

# Claude 클라이언트 초기화
client = anthropic.Client(api_key=ANTHROPIC_API_KEY)

# 텔레그램 봇 설정
TELEGRAM_TOKEN = "7659346262:AAHdpHX1kN1vUxXO2H0sdFkXkOs3SQpsA3Q"
TELEGRAM_CHAT_ID = "5767743818"  # 텔레그램 봇으로부터 받은 chat_id
bot = telebot.TeleBot(TELEGRAM_TOKEN)


def send_telegram_message(student_name, kakao_id, question):
    """텔레그램으로 질문 전송"""
    try:
        message = f"""📚 새로운 학습 질문
        
학생명: {student_name}
카카오ID: {kakao_id}
질문내용: {question}

전송시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return True
    except Exception as e:
        st.error(f"텔레그램 메시지 전송 실패: {str(e)}")
        return False


def send_kakao_message(student_name, kakao_id, question):
    """카카오톡으로 질문 전송"""
    try:
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {"Authorization": f"Bearer {KAKAO_TOKEN}"}

        template = {
            "object_type": "text",
            "text": f"""📚 학습 질문 알림

학생명: {student_name}
카카오ID: {kakao_id}
질문내용: {question}

전송시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}""",
            "link": {
                "web_url": "https://example.com/question-status",
                "mobile_web_url": "https://example.com/question-status",
            },
            "button_title": "답변 확인하기",
        }

        data = {"template_object": json.dumps(template)}
        response = requests.post(url, headers=headers, data=data)

        if response.status_code != 200:
            raise Exception(f"카카오톡 메시지 전송 실패: {response.text}")
        return True
    except Exception as e:
        st.error(f"카카오톡 메시지 전송 실패: {str(e)}")
        return False


def get_text_from_pdf(pdf_path):
    """PDF 파일에서 텍스트 추출"""
    try:
        pdf_reader = PdfReader(pdf_path)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"PDF 읽기 오류: {str(e)}")
        return ""


def send_messages(student_name, kakao_id, question):
    """텔레그램과 카카오톡으로 질문 전송"""
    telegram_success = send_telegram_message(student_name, kakao_id, question)
    kakao_success = send_kakao_message(student_name, kakao_id, question)

    if telegram_success and kakao_success:
        return True, "모든 메시지가 성공적으로 전송되었습니다!"
    elif telegram_success:
        return True, "텔레그램 메시지만 전송되었습니다."
    elif kakao_success:
        return True, "카카오톡 메시지만 전송되었습니다."
    else:
        return False, "메시지 전송에 실패했습니다."


def load_course_materials():
    """강의 자료 PDF 로드"""
    course_text = ""
    try:
        pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]

        if not pdf_files:
            st.error("PDF 파일을 찾을 수 없습니다.")
            return ""

        for pdf_file in pdf_files:
            content = get_text_from_pdf(pdf_file)
            if content:
                course_text += f"[{pdf_file}]\n{content}\n\n"

        return course_text
    except Exception as e:
        st.error("문서 로드 중 오류가 발생했습니다.")
        return ""


def show_question_form():
    """질문 폼을 표시하는 함수"""
    with st.expander("교수님께 질문하기", expanded=True):
        st.header("질문 정보 입력")

        # 세션 상태에 폼 데이터 초기화
        if "form_submitted" not in st.session_state:
            st.session_state.form_submitted = False

        # 폼 데이터를 세션 상태로 관리
        if "form_data" not in st.session_state:
            st.session_state.form_data = {
                "student_name": "",
                "kakao_id": "",
                "question": "",
            }

        # 폼 입력 필드
        student_name = st.text_input(
            "이름", value=st.session_state.form_data["student_name"]
        )
        kakao_id = st.text_input(
            "카카오톡 ID", value=st.session_state.form_data["kakao_id"]
        )
        question = st.text_area(
            "질문 내용", value=st.session_state.form_data["question"]
        )

        # 입력된 데이터 저장
        st.session_state.form_data["student_name"] = student_name
        st.session_state.form_data["kakao_id"] = kakao_id
        st.session_state.form_data["question"] = question

        if not st.session_state.form_submitted:
            if st.button("질문 보내기"):
                if not all([student_name, kakao_id, question]):
                    st.warning("모든 필드를 입력해주세요.")
                else:
                    success, message = send_messages(student_name, kakao_id, question)
                    if success:
                        st.success(message)
                        st.session_state.form_submitted = True
                        st.rerun()
                    else:
                        st.error(message)

        # 질문이 완료되었을 때 새로운 질문 버튼 표시
        if st.session_state.form_submitted:
            if st.button("새로운 질문하기"):
                # 폼 데이터 초기화
                st.session_state.form_data = {
                    "student_name": "",
                    "kakao_id": "",
                    "question": "",
                }
                st.session_state.form_submitted = False
                st.rerun()


def get_claude_response(messages, prompt):
    """Claude API를 사용하여 응답 생성"""
    try:
        context = """당신은 친절하고 전문적인 AI 조교입니다. 다음 지침을 따라 응답해주세요:

        1. 답변 스타일:
        - '안녕하세요! AI 조교입니다. 💡'로 시작
        - 학생의 수준에 맞는 설명 제공
        - 구체적인 예시와 함께 설명
        - 추가 학습 리소스 추천
        
        2. 피드백:
        - 건설적인 피드백 제공
        - 학생의 이해도 확인
        - 심화 학습 방향 제시
        
        참고 자료:
        {st.session_state.get('course_text', '강의 자료가 없습니다.')}

        위 내용을 바탕으로 답변해주세요: {prompt}"""

        message_list = [{"role": "user", "content": context}]
        for msg in messages:
            if msg["role"] != "system":
                message_list.append({"role": msg["role"], "content": msg["content"]})

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=message_list,
            max_tokens=1000,
            temperature=0.7,
        )

        return response.content[0].text
    except Exception as e:
        if "rate_limit_exceeded" in str(e):
            return "잠시 후 다시 시도해주세요."
        st.error(f"오류 발생: {str(e)}")
        return None


def load_course_materials():
    """강의 자료 PDF 로드 - 최적화 버전"""
    st.session_state.course_text = ""  # 초기화

    try:
        # PDF 파일 검색
        pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]

        if not pdf_files:
            st.warning("📚 등록된 PDF 파일이 없습니다.")
            return ""

        # 프로그레스 바 생성
        progress_text = "강의 자료를 불러오는 중입니다..."
        total_files = len(pdf_files)

        with st.spinner(progress_text):
            progress_bar = st.progress(0)

            for idx, pdf_file in enumerate(pdf_files):
                # 진행 상태 표시
                progress = int((idx + 1) * 100 / total_files)
                progress_bar.progress(progress, f"Processing: {pdf_file}")

                # 파일 크기 확인
                file_size = os.path.getsize(pdf_file) / (1024 * 1024)  # MB 단위

                if file_size > 50:  # 50MB 이상인 경우
                    st.warning(
                        f"⚠️ {pdf_file}의 용량이 큽니다 ({file_size:.1f}MB). 처리에 시간이 걸릴 수 있습니다."
                    )

                # 텍스트 추출
                content = get_text_from_pdf(pdf_file)
                if content:
                    st.session_state.course_text += f"\n[{pdf_file}]\n{content}\n\n"

            progress_bar.empty()  # 프로그레스 바 제거

        # 데이터 요약 정보 표시
        total_size = sum(os.path.getsize(f) for f in pdf_files) / (1024 * 1024)
        st.success(
            f"""
        ✅ 강의 자료 로드 완료:
        - 처리된 파일: {total_files}개
        - 총 용량: {total_size:.1f}MB
        """
        )

        return st.session_state.course_text

    except Exception as e:
        st.error(f"문서 로드 중 오류가 발생했습니다: {str(e)}")
        return ""


def main():
    # 페이지 설정
    st.set_page_config(
        page_title="AI 조교 챗봇",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=None,
    )

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
        
        /* 전체 폰트 설정 */
        * {
            font-family: 'Noto Sans KR', sans-serif !important;
        }
        
        /* 챗봇 답변 컨테이너 스타일 */
        .st-emotion-cache-1gulkj5 {
            background-color: #E3F2FD !important;
            border-radius: 15px !important;
        }
        
        /* 챗봇 답변 텍스트 색상 */
        .st-emotion-cache-1gulkj5 p {
            color: #1565C0 !important;
        }
        
        /* 챗봇 아이콘 배경 */
        .st-emotion-cache-1v0mbdj {
            background-color: #1565C0 !important;
        }
    
        /* 사용자 메시지 컨테이너 */
        .st-emotion-cache-91bucy {
            background-color: #F5F5F5 !important;
            border-radius: 15px !important;
        }
    
        /* 사용자 메시지 텍스트 */
        .st-emotion-cache-91bucy p {
            color: #333 !important;
        }
    
        /* 챗봇 메시지 전체 스타일 통일 */
        .stChatMessage {
            margin: 1rem 0;
            padding: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        /* 버튼 스타일 */
        .stButton > button {
            background-color: #1565C0;
            color: white;
            border-radius: 25px;
            padding: 0.5rem 2rem;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background-color: #0D47A1;
            transform: translateY(-2px);
        }
        
        /* 입력 필드 스타일 */
        .stTextInput > div > div > input {
            border-radius: 25px;
            border: 2px solid #E0E0E0;
            padding: 1rem;
        }
        
        /* 헤더 스타일 */
        h1, h2, h3 {
            color: #1565C0;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 사이드바 설정
    # main 함수의 사이드바 부분을 다음과 같이 수정
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="background: linear-gradient(135deg, #1565C0, #0D47A1); 
                            border-radius: 15px; 
                            padding: 20px; 
                            display: inline-block;">
                    <span style="font-size: 40px;">👨‍🏫</span>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.title("AI 조교")
        st.markdown("---")
        st.write("강의 내용에 대해 궁금한 점을 물어보세요!")
        # 교수님께 질문하기 버튼
        if st.button("❓ 교수님께 질문하기"):
            st.session_state.showing_form = True
            st.rerun()

    # 메인 영역
    st.title("🎓 AI 조교와 대화하기")

    # 최초 실행 시 강의 자료 로드 - 로딩 화면 개선
    if "course_text" not in st.session_state:
        st.markdown(
            """
        <div style='text-align: center; padding: 2rem;'>
            <h2>🎓 AI 조교 시스템 초기화 중...</h2>
            <p>강의 자료를 분석하고 있습니다. 잠시만 기다려주세요.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        course_text = load_course_materials()

        if course_text:
            st.success("AI 조교가 준비되었습니다! 질문해 주세요. 😊")
        else:
            st.warning("강의 자료 로드에 실패했습니다. PDF 파일을 확인해주세요.")
            return

    # 질문 폼 표시 (조건부)
    if st.session_state.get("showing_form", False):
        show_question_form()

    # 최초 실행 시 강의 자료 로드
    if "course_text" not in st.session_state:
        st.session_state["course_text"] = load_course_materials()

    # 강의 자료 확인
    if not st.session_state.get("course_text", "").strip():
        st.warning("등록된 강의 자료가 없습니다. PDF 파일을 확인해주세요.")
        return

    # 챗봇 대화 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # 시작 메시지 추가
        welcome_msg = {
            "role": "assistant",
            "content": "안녕하세요! 저는 강의를 도와드릴 AI 조교입니다. 강의 내용에 대해 궁금한 점을 물어보세요! 💡",
        }
        st.session_state.messages.append(welcome_msg)

    # 채팅 이력 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("궁금한 점을 물어보세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("답변을 생성하고 있습니다..."):
                response = get_claude_response(st.session_state.messages, prompt)
                if response:
                    if "죄송합니다" in response:  # rate limit 에러 응답
                        st.warning(response)
                    else:
                        st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )


if __name__ == "__main__":
    main()
