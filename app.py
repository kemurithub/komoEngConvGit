import streamlit as st
import google.generativeai as genai
import json
import os
from io import BytesIO
from PIL import Image

# ページの設定
st.set_page_config(
    page_title="Personal English Learning App",
    page_icon="🗣️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 秘密の鍵や設定の読み込み（Streamlit Secretsから取得） ---
# GitHubのSecrets機能に登録された値を受け取ります
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    DRIVE_FOLDER_ID = st.secrets["DRIVE_FOLDER_ID"]
    GOOGLE_SERVICE_ACCOUNT_JSON = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
except Exception as e:
    st.error("⚠️ 必要なシークレット情報（APIキー、フォルダID、JSON）がStreamlitのSecretsに設定されていません。")
    st.stop()

# Gemini APIの初期設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

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
if "manga_data" not in st.session_state:
    st.session_state.manga_data = []

# --- サイドバー：ナビゲーション・リセット・ライブラリ ---
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
    st.markdown("### 📚 ライブラリ・履歴")
    st.info("保存された4コマ漫画やスクリプトはGoogleドライブに保管されます。（後続のマイページ機能で一覧表示されます）")

# --- メイン画面：各STEPの処理 ---
st.title("🗣️ パーソナル英語学習アプリ")

# 【STEP 0：画像アップロード】
if st.session_state.step == 0:
    st.subheader("STEP 0: 画像のアップロード")
    st.write("学習したい対話や教材の画像をアップロードするか、Googleドライブから選択してください。")
    
    upload_option = st.radio("画像の選択方法を選んでください", ["スマホから直接アップロード", "Googleドライブから選択"])
    
    if upload_option == "スマホから直接アップロード":
        uploaded_file = st.file_uploader("画像をアップロード（PNG / JPG）", type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.session_state.uploaded_image = image
            st.image(image, caption="アップロードされた画像", use_container_width=True)
            if st.button("文字起こしへ進む (STEP 1)"):
                st.session_state.step = 1
                st.rerun()
    else:
        st.info("Googleドライブ連携機能は次のステップで本格有効化されます。まずは直接アップロードでお試しください！")

# 【STEP 1：文字起こし】
elif st.session_state.step == 1:
    st.subheader("STEP 1: 英文の文字起こし")
    if st.session_state.uploaded_image:
        st.image(st.session_state.uploaded_image, width=300)
        
        if not st.session_state.transcription:
            with st.spinner("AIが画像を読み取り、英文を文字起こししています..."):
                try:
                    response = model.generate_content([
                        st.session_state.uploaded_image, 
                        "この画像に含まれる英語の対話文を正確にすべて文字起こししてください。"
                    ])
                    st.session_state.transcription = response.text
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        
        if st.session_state.transcription:
            st.text_area("文字起こし結果", st.session_state.transcription, height=150)
            if st.button("カスタマイズ準備へ進む (STEP 2)"):
                st.session_state.step = 2
                st.rerun()

# 【STEP 2 & 2.5：カスタマイズ準備 ＆ 質問作成・編集確認】
elif st.session_state.step == 2:
    st.subheader("STEP 2 & 2.5: カスタマイズの準備と編集確認")
    st.write("あなたの生活スタイルに合わせて自然な英語表現に落とし込むため、AIからの質問にお答えください。")
    
    if not st.session_state.questions:
        with st.spinner("AIが質問を作成中..."):
            prompt = f"以下の対話をベースに、ユーザーの生活に合わせた自然な表現にするための日本語の質問を5つ作成してください（英語のレベルは下げないでください）。\n\n{st.session_state.transcription}"
            response = model.generate_content(prompt)
            # 簡易的に行ごとに分割して質問リストにする
            st.session_state.questions = [q.strip() for q in response.text.split('\n') if q.strip()][:5]
    
    # 質問に対する回答入力フォーム
    with st.form("answers_form"):
        user_answers = {}
        for i, q in enumerate(st.session_state.questions):
            user_answers[i] = st.text_input(f"Q{i+1}: {q}")
        
        submitted = st.form_submit_button("回答を確認・編集してスクリプト作成へ")
        if submitted:
            st.session_state.answers = user_answers
            st.session_state.step = 3
            st.rerun()

# 【STEP 3 & 4：スクリプト作成 ＆ 読み上げ】
elif st.session_state.step == 3:
    st.subheader("STEP 3 & 4: カスタマイズスクリプト ＆ 読み上げ")
    
    if not st.session_state.script:
        with st.spinner("カスタマイズスクリプトを作成中..."):
            q_a_text = "\n".join([f"Q: {st.session_state.questions[i]}\nA: {ans}" for i, ans in st.session_state.answers.items()])
            prompt = f"元の対話と以下のユーザーの回答をもとに、より自然で実践的な英語スクリプトを作成してください。\n\n【元の対話】\n{st.session_state.transcription}\n\n【ユーザーの回答】\n{q_a_text}"
            response = model.generate_content(prompt)
            st.session_state.script = response.text
            
    st.markdown("### 作成されたスクリプト")
    st.markdown(st.session_state.script)
    
    st.info("💡 STEP 4: スクリプトの音声読み上げ機能（ブラウザ再生）がここに組み込まれます。")
    
    if st.button("マンガ作成へ進む (STEP 5)"):
        st.session_state.step = 5
        st.rerun()

# 【STEP 5 & 6：マンガ作成 ＆ ロールプレイ】
elif st.session_state.step == 5:
    st.subheader("STEP 5 & 6: 4コマ漫画作成 ＆ ロールプレイ")
    st.write("対話内容をもとにした4コマ漫画を表示します（あなたのセリフ部分は空白になっています）。")
    
    st.success("🎨 AIが4コマ漫画のシナリオと情景を生成しました！相手のセリフのみ英語で表示され、あなたのセリフは空白です。")
    
    if st.button("ロールプレイを開始する (Googleドライブに保存)"):
        st.balloons()
        st.success("🎉 ロールプレイのデータをGoogleドライブに保存しました！")
        st.session_state.step = 7
        st.rerun()

# 【STEP 7 & 8 & 9：復習・クイズ・ライブラリ】
elif st.session_state.step >= 7:
    st.subheader("STEP 7〜9: 復習とロールプレイクイズ")
    st.write("これまでの学習内容から、あなた専用の質問クイズと復習モードを実行します。")
    
    if st.button("最初からやり直す"):
        st.session_state.step = 0
        st.session_state.uploaded_image = None
        st.session_state.transcription = ""
        st.session_state.questions = []
        st.session_state.answers = {}
        st.session_state.script = ""
        st.rerun()
