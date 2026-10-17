import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import datetime

# ==========================================
# ページの設定
# ==========================================
st.set_page_config(
    page_title="komoEngConv2026",
    page_icon="🎧",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 後半アプリのURL ---
PART2_APP_URL = "https://komoengconvgit2-rmxkqjwbpfbqnshj6zdyb9.streamlit.app/"

# --- APIキーの読み込み（Streamlit Secretsから取得） ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("⚠️ Gemini APIキー（GEMINI_API_KEY）がStreamlitのSecretsに設定されていません。")
    st.stop()

# Gemini APIの初期設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- セッション状態の初期化 ---
if "page" not in st.session_state:
    st.session_state.page = "step0"  # "step0", "step1", "step2", "step3", "mypage"
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
if "history" not in st.session_state:
    st.session_state.history = []

# --- サイドバー：ナビゲーション・リセット ---
with st.sidebar:
    st.title("⚙️ 前半アプリメニュー")
    if st.button("🏠 マイページ（履歴一覧）"):
        st.session_state.page = "mypage"
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 📌 現在の進捗")
    current_page = st.session_state.page
    if current_page != "mypage":
        st.write(f"現在のモード: {current_page.upper()}")
    else:
        st.write("マイページ表示中")
        
    st.markdown("---")
    if st.button("🔄 最初からやり直す"):
        st.session_state.page = "step0"
        st.session_state.uploaded_image = None
        st.session_state.transcription = ""
        st.session_state.questions = []
        st.session_state.answers = {}
        st.session_state.script = ""
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 📚 アプリ情報")
    st.info("教科書の画像を読み込み、あなただけのパーソナルな英語スクリプトを作成・ダウンロードできるツールです。")

# ==========================================
# メイン画面のルーティング
# ==========================================

# 【マイページ】
if st.session_state.page == "mypage":
    st.title("📚 マイページ（作成履歴）")
    st.write("これまでに作成した英語スクリプトの一覧です。過去のスクリプトの確認やダウンロードができます。")
    
    if not st.session_state.history:
        st.info("まだ作成履歴がありません。STEP 0から画像をアップロードしてスクリプトを作成してみましょう！")
    else:
        for idx, hist in enumerate(st.session_state.history):
            with st.container():
                st.markdown(f"**履歴 #{idx+1}** - 📅 {hist['date']}")
                st.text(hist['script'][:100] + "...")
                
                with st.expander("📄 スクリプト全文を表示"):
                    st.markdown(hist['script'])
                    
                st.download_button(
                    label=f"💾 このスクリプトをダウンロード (.txt) #{idx+1}",
                    data=hist['script'],
                    file_name=f"english_script_{idx+1}.txt",
                    mime="text/plain",
                    key=f"dl_hist_{idx}"
                )
                st.markdown("---")
                
    if st.button("⬅️ 作成画面に戻る"):
        st.session_state.page = "step0"
        st.rerun()

# 【STEP 0：画像アップロード】
elif st.session_state.page == "step0":
    st.title("🎧 komoEngConvApp_1")
    st.subheader("STEP 0: 画像のアップロード")
    st.write("教科書や教材の対話文の画像をアップロードしてください。")
    
    uploaded_file = st.file_uploader("画像をアップロード（PNG / JPG）", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.session_state.uploaded_image = uploaded_file
        st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)
        
        if st.button("文字起こしへ進む (STEP 1)"):
            st.session_state.page = "step1"
            st.rerun()

# 【STEP 1：英文の文字起こし】
elif st.session_state.page == "step1":
    st.title("🎧 komoEngConvApp_1")
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
                st.session_state.page = "step2"
                st.rerun()

# 【STEP 2 & 2.5：カスタマイズ準備 ＆ 質問作成・編集確認】
elif st.session_state.page == "step2":
    st.title("🎧 komoEngConvApp_1")
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
            st.
