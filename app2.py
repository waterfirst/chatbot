import streamlit as st
import google.generativeai as genai
import os
import tempfile
from PyPDF2 import PdfReader

# Streamlit 페이지 설정
st.set_page_config(page_title="DS라온 대리운전 QA 챗봇", page_icon="🚗", layout="wide")

# Gemini API 키 설정
if "GOOGLE_API_KEY" in st.secrets:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    # 로컬 테스트용
    GOOGLE_API_KEY = "AIzaSyCVWp5atr9rwq1u1TUWg6fmoJ6pq6r8Wcw"

genai.configure(api_key=GOOGLE_API_KEY)

# 모델 설정
model = genai.GenerativeModel("gemini-pro")


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

        # 파일이 모두 로드되면 성공 메시지만 표시
        if qa_text:
            st.success("대답할 준비가 완료되었습니다! 궁금하신 점을 물어보세요. 😊")

        return qa_text
    except Exception as e:
        st.error("문서 로드 중 오류가 발생했습니다.")
        return ""


def get_gemini_response(conversation, prompt):
    """Gemini API를 사용하여 응답 생성"""
    try:
        enhanced_prompt = f"""당신은 DS라온 대리운전의 전문 상담원입니다. 다음 지침을 따라 응답해주세요:

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

        고객의 질문: {prompt}

        참고 문서 내용:
        {st.session_state.get('qa_text', '문서 내용이 없습니다.')}
        """

        response = conversation.send_message(enhanced_prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "죄송합니다. 잠시 후 다시 시도해주시기 바랍니다."
        st.error(f"에러가 발생했습니다: {str(e)}")
        return None


def main():
    st.title("🚗 DS라온 대리운전 QA 챗봇")
    st.markdown(
        """
        <style>
            .stApp {
                max-width: 1200px;
                margin: 0 auto;
            }
            .chat-message {
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
            }
            .user-message {
                background-color: #f0f2f6;
            }
            .assistant-message {
                background-color: #e8f0fe;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # 최초 실행 시 QA 문서 로드
    if "qa_text" not in st.session_state:
        st.session_state["qa_text"] = load_qa_documents()

        # 디버깅을 위한 상태 확인
    if "qa_text" not in st.session_state:
        st.info("QA 문서를 처음 로드합니다...")
        st.session_state["qa_text"] = load_qa_documents()

    # QA 문서가 비어있는지 확인
    if not st.session_state.get("qa_text", "").strip():
        st.error("QA 문서가 비어있습니다. PDF 파일을 확인해주세요.")
        return

    # 메인 채팅 인터페이스
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.conversation = model.start_chat(history=[])

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
                response = get_gemini_response(st.session_state.conversation, prompt)
                if response:
                    if "죄송합니다" in response:  # 429 에러 응답인 경우
                        st.warning(response)
                    else:
                        st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )


if __name__ == "__main__":
    main()
