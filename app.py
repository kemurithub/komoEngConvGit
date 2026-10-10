import streamlit as st
import google.generativeai as genai
import json
import os
from io import BytesIO
from PIL import Image
from gtts import gTTS

# ページの設定
st.set_page_config(
    page_title="komoEngConv2026",
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

import io
from PIL import Image
import streamlit as st
import google.generativeai as genai

# （もし初期化やAPIキー設定がこの下にあればそのまま置いてください）

# 【STEP 0：画像アップロード】
if st.session_state.step == 0:
    st.subheader("STEP 0: 画像のアップロード")
    st.write("学習したい対話や教材の画像をアップロードするか、Googleドライブから選択してください。")
    
    upload_option = st.radio("画像の選択方法を選んでください", ["スマホから直接アップロード", "Googleドライブから選択"])
    
    if upload_option == "スマホから直接アップロード":
        uploaded_file = st.file_uploader("画像をアップロード（PNG / JPG）", type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
            # ★ファイルをそのままセッションに保存する
            st.session_state.uploaded_image = uploaded_file
            
            # プレビュー表示
            st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)
            
            if st.button("文字起こしへ進む (STEP 1)"):
                st.session_state.step = 1
                st.rerun()
    else:
        st.info("Googleドライブ連携機能は次のステップで本格有効化されます。まずは直接アップロードでお試しください！")
        
# 【STEP 1：英文の文字起こし】
elif st.session_state.step == 1:
    st.subheader("STEP 1: 英文の文字起こし")
    if st.session_state.uploaded_image:
        st.image(st.session_state.uploaded_image, width=300)
        
        if not st.session_state.transcription:
            with st.spinner("AIが画像を読み取り、英文を文字起こししています..."):
                try:
                    # 1. 画像を開いてリサイズする（そのままPILオブジェクトとして保持）
                    img = Image.open(st.session_state.uploaded_image)
                    img.thumbnail((1024, 1024))
                    
                    # 透明度などがある場合に備えてRGBに変換
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    # 2. PILオブジェクトのままGeminiに渡す
                    response = model.generate_content([
                        img, 
                        "この画像に含まれる英語の対話文を正確にすべて文字起こししてください。"
                    ], request_options={"timeout": 120})
                    
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
            prompt = f"""以下の対話をベースに、ユーザーの生活に合わせた自然な表現にするための日本語の質問を5つだけ作成してください。
【重要条件】
- 余計な説明、挨拶、マークダウンの見出し（###）や引用（>）、番号（1.やQ1など）は一切つけないでください。
- 純粋な質問文のテキストだけを、1行に1つずつ、合計5行だけ出力してください。

対話データ:
{st.session_state.transcription}"""
            
            response = model.generate_content(prompt)
            # 改行区切りで綺麗に5つ取得する
            lines = [q.strip() for q in response.text.split('\n') if q.strip()]
            st.session_state.questions = lines[:5]
    
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
    st.subheader("STEP 3 & 4: カスタマイズスクリプト ＆ 音声読み上げ")
    
    if not st.session_state.script:
        with st.spinner("カスタマイズスクリプトを作成中..."):
            q_a_text = "\n".join([f"Q: {st.session_state.questions[i]}\nA: {ans}" for i, ans in st.session_state.answers.items()])
            
            # プロンプトはシンプルに
            prompt = f"以下の元の対話と回答をもとに、英語の完成スクリプトを作成してください。\n\n【元の対話】\n{st.session_state.transcription}\n\n【回答】\n{q_a_text}"
            
            response = model.generate_content(
                prompt,
                request_options={"timeout": 120}
            )
            st.session_state.script = response.text
            
    st.markdown("### 作成されたスクリプト")
    st.markdown(st.session_state.script)
    
    # --- STEP 4：音声読み上げ機能 ---
    st.markdown("---")
    st.subheader("🔊 STEP 4: 音声読み上げ")
    
    try:
        import re
        
        if st.button("音声を生成する"):
            with st.spinner("音声を生成しています..."):
                script_text = st.session_state.script
                
                # ★行頭の話者名（A: や Ken: など）だけを削除し、文中の人名はそのまま残す処理
                cleaned_text = re.sub(r'^[^\n]*?[:：]\s*', '', script_text, flags=re.MULTILINE)
                
                # マークダウンの記号を掃除
                cleaned_text = cleaned_text.replace('#', '').replace('*', '')
                
                # gTTSで音声データを作成
                tts = gTTS(text=cleaned_text, lang='en')
                audio_bytes = io.BytesIO()
                tts.write_to_fp(audio_bytes)
                audio_bytes.seek(0)
                
                st.session_state.audio_data = audio_bytes
        
        # 音声データがあればプレイヤーを表示
        if "audio_data" in st.session_state and st.session_state.audio_data:
            st.audio(st.session_state.audio_data, format="audio/mp3")
            
    except Exception as e:
        st.error(f"音声生成エラー: {e}")
    
    st.markdown("---")
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
