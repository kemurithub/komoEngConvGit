import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# ==========================================
# ページの設定
# ==========================================
st.set_page_config(
    page_title="komoEngConv2026",
    page_icon="🗣️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- APIキーの読み込み（Streamlit Secretsから取得） ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("⚠️ Gemini APIキー（GEMINI_API_KEY）がStreamlitのSecretsに設定されていません。")
    st.stop()

# Gemini APIの初期設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.8-flash')

# --- セッション状態の初期化（アプリの状態保持） ---
if "step" not in st.session_state:
    st.session_state.step = 0
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "transcription" not in st.session_state:
    st.session_state.transcription = ""
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "script" not in st.session_state:
    st.session_state.script = ""

# --- サイドバー：ナビゲーション・リセット ---
with st.sidebar:
    st.title("⚙️ メニュー")
    if st.button("🔄 リセット（STEP 0へ）"):
        st.session_state.step = 0
        st.session_state.uploaded_image = None
        st.session_state.transcription = ""
        st.session_state.questions = []
        st.session_state.answers = {}
        st.session_state.script = ""
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 📚 アプリ情報")
    st.info("教科書の画像を読み込み、あなただけのパーソナルな英語スクリプトを作成・ダウンロードできるツールです。")

# --- メイン画面：各STEPの処理 ---
st.title("🗣️ komoEngConvApp_1")

# 【STEP 0：画像アップロード】
if st.session_state.step == 0:
    st.subheader("STEP 0: 画像のアップロード")
    st.write("画像をアップロード。")
    
    uploaded_file = st.file_uploader("画像をアップロード（PNG / JPG）", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.session_state.uploaded_image = uploaded_file
        st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)
        
        if st.button("文字起こしへ進む (STEP 1)"):
            st.session_state.step = 1
            st.rerun()
      
# 【STEP 1：英文の文字起こし】
elif st.session_state.step == 1:
    st.subheader("STEP 1: 英文の文字起こし")
    if st.session_state.uploaded_image:
        st.image(st.session_state.uploaded_image, width=300)
        
        if not st.session_state.transcription:
            with st.spinner("AIが画像を読み取り、英文を文字起こししています..."):
                try:
                    img = Image.open(st.session_state.uploaded_image)
                    img.thumbnail((1024, 1024))
                    
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    response = model.generate_content([
                        img, 
                        "この画像に含まれる英語の対話文を正確にすべて文字起こししてください。"
                    ], request_options={"timeout": 120})
                    
                    st.session_state.transcription = response.text
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        
        if st.session_state.transcription:
            st.session_state.transcription = st.text_area("文字起こし結果（編集可能）", st.session_state.transcription, height=150)
            if st.button("カスタマイズ準備へ進む (STEP 2)"):
                st.session_state.step = 2
                st.rerun()
              
# 【STEP 2 & 2.5：カスタマイズ準備 ＆ 質問作成・編集確認】
elif st.session_state.step == 2:
    st.subheader("STEP 2 & 2.5: カスタマイズの準備と編集確認")
    st.write("あなたの生活スタイルに合わせて自然な英語表現に落とし込むため、AIからの質問にお答えください。")
    
    if not st.session_state.questions:
        with st.spinner("AIが質問を作成中..."):
            prompt = f"""以下の対話をベースに、ユーザーの生活に合わせた自然な表現にするための日本語の質問を5つだけ作成してください。
【重要条件】
- 余計な説明、挨拶、マークダウンの見出し（###）や引用（>）、番号（1.やQ1など）は一切つけないでください。
- 純粋な質問文のテキストだけを、1行に1つずつ、合計5行だけ出力してください。

対話データ:
{st.session_state.transcription}"""
            
            response = model.generate_content(prompt)
            lines = [q.strip() for q in response.text.split('\n') if q.strip()]
            st.session_state.questions = lines[:5]
    
    with st.form("answers_form"):
        user_answers = {}
        for i, q in enumerate(st.session_state.questions):
            user_answers[i] = st.text_input(f"Q{i+1}: {q}")
        
        submitted = st.form_submit_button("回答を確定して完成スクリプトを作成する")
        if submitted:
            st.session_state.answers = user_answers
            st.session_state.step = 3
            st.rerun()

# 【STEP 3：スクリプト作成 ＆ テキストダウンロード】
elif st.session_state.step == 3:
    st.subheader("STEP 3: 完成スクリプトの作成とダウンロード")
    
    if not st.session_state.script:
        with st.spinner("カスタマイズスクリプトを作成中..."):
            q_a_text = "\n".join([f"Q: {st.session_state.questions[i]}\nA: {ans}" for i, ans in st.session_state.answers.items()])
            
            prompt = f"""
以下の元の対話と回答をもとに、英語の完成スクリプトを作成してください。

【元の対話】
{st.session_state.transcription}

【回答】
{q_a_text}
"""
            try:
                response = model.generate_content(
                    prompt,
                    request_options={"timeout": 120}
                )
                st.session_state.script = response.text
            except Exception as e:
                st.error(f"生成エラーが発生しました: {e}")
            
    if st.session_state.script:
        st.markdown("### 📄 作成されたスクリプト")
        st.markdown(st.session_state.script)
        
        st.markdown("---")
        
        # ワンクリックでテキストファイルとしてダウンロード
        st.download_button(
            label="💾 スクリプトをテキストファイル（.txt）でダウンロード",
            data=st.session_state.script,
            file_name="radio_english_script.txt",
            mime="text/plain"
        )
        
        st.markdown("---")
        if st.button("最初からやり直す"):
            st.session_state.step = 0
            st.session_state.uploaded_image = None
            st.session_state.transcription = ""
            st.session_state.questions = []
            st.session_state.answers = {}
            st.session_state.script = ""
            st.rerun()
