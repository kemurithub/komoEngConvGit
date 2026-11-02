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

PART2_APP_URL = "https://komoengconvgit2-rmxkqjwbpfbqnshj6zdyb9.streamlit.app/"

# --- APIキーの読み込み ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Gemini APIキー（GEMINI_API_KEY）がStreamlitのSecretsに設定されていません。")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
# 最新の安定した軽量モデルを指定
model = genai.GenerativeModel('gemini-1.5-flash')

# --- セッション状態の初期化 ---
if "page" not in st.session_state:
    st.session_state.page = "step0"
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "transcription" not in st.session_state:
    st.session_state.transcription = ""
if "questions" not in st.session_state:
    st.session_state.questions = []
if "script" not in st.session_state:
    st.session_state.script = ""
if "history" not in st.session_state:
    st.session_state.history = []

# --- サイドバー ---
with st.sidebar:
    st.title("⚙️ 前半アプリメニュー")
    if st.button("🏠 マイページ（履歴一覧）", use_container_width=True):
        st.session_state.page = "mypage"
        st.rerun()
        
    st.markdown("---")
    if st.button("🔄 最初からやり直す", use_container_width=True):
        st.session_state.page = "step0"
        st.session_state.uploaded_image = None
        st.session_state.transcription = ""
        st.session_state.questions = []
        st.session_state.script = ""
        st.rerun()
        
    st.markdown("---")
    st.info("教科書の画像を読み込み、パーソナルな英語スクリプトを作成・ダウンロードできるツールです。")

# ==========================================
# メイン画面ルーティング
# ==========================================

# 【マイページ】
if st.session_state.page == "mypage":
    st.title("📚 マイページ（作成履歴）")
    
    if not st.session_state.history:
        st.info("まだ作成履歴がありません。STEP 0から画像をアップロードしてみましょう！")
    else:
        for idx, hist in enumerate(st.session_state.history):
            with st.container():
                st.markdown(f"**履歴 #{idx+1}** - 📅 {hist['date']}")
                st.text(hist['script'][:100] + "...")
                with st.expander("📄 スクリプト全文を表示"):
                    st.markdown(hist['script'])
                st.download_button(
                    label=f"💾 ダウンロード (.txt) #{idx+1}",
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
    st.write("対話文の画像をアップロードしてください（PNG / JPG）。")
    
    uploaded_file = st.file_uploader("画像を選択", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.session_state.uploaded_image = uploaded_file
        st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)
        
        if st.button("文字起こしへ進む (STEP 1)", type="primary"):
            st.session_state.page = "step1"
            st.session_state.transcription = ""  # 新規画像用にクリア
            st.session_state.questions = []
            st.session_state.script = ""
            st.rerun()

# 【STEP 1：英文の文字起こし】
elif st.session_state.page == "step1":
    st.title("🎧 komoEngConvApp_1")
    st.subheader("STEP 1: 英文の文字起こし")
    
    if st.session_state.uploaded_image:
        st.image(st.session_state.uploaded_image, width=300)
        
        # まだ文字起こししていない場合のみ実行
        if not st.session_state.transcription:
            with st.spinner("AIが画像を読み取り、英文を文字起こししています..."):
                try:
                    img = Image.open(st.session_state.uploaded_image)
                    img.thumbnail((1000, 1000))  # 解像度の最適化
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=85)
                    img_bytes = buffered.getvalue()
                    
                    image_part = {
                        "mime_type": "image/jpeg",
                        "data": img_bytes
                    }
                    
                    response = model.generate_content([
                        image_part, 
                        "この画像に含まれる英語の対話文を正確にすべて文字起こししてください。"
                    ])
                    st.session_state.transcription = response.text
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        
        if st.session_state.transcription:
            st.session_state.transcription = st.text_area(
                "文字起こし結果（必要に応じて修正してください）", 
                st.session_state.transcription, 
                height=150
            )
            if st.button("カスタマイズ質問作成へ進む (STEP 2)", type="primary"):
                st.session_state.page = "step2"
                st.rerun()

# 【STEP 2：質問作成 ＆ 回答入力】
elif st.session_state.page == "step2":
    st.title("🎧 komoEngConvApp_1")
    st.subheader("STEP 2: カスタマイズのための質問回答")
    
    # 質問がまだ作成されていない場合のみ生成
    if not st.session_state.questions:
        with st.spinner("AIが質問を作成中..."):
            prompt = f"""以下の対話をベースに、ユーザーの生活に合わせた自然な表現にするための日本語の質問を5つ作成してください。
【重要条件】
- 余計な説明、挨拶、マークダウン記号（###, >, 番号など）は一切つけない。
- 純粋な質問文のみを1行に1つずつ、合計5行だけ出力する。

対話データ:
{st.session_state.transcription}"""
            try:
                response = model.generate_content(prompt)
                lines = [q.strip() for q in response.text.split('\n') if q.strip()]
                st.session_state.questions = lines[:5]
            except Exception as e:
                st.error(f"質問作成中にエラーが発生しました: {e}")
                
    if st.session_state.questions:
        with st.form("answers_form"):
            user_answers = {}
            for i, q in enumerate(st.session_state.questions):
                user_answers[i] = st.text_input(f"Q{i+1}: {q}", key=f"ans_{i}")
            
            submitted = st.form_submit_button("回答を確定して完成スクリプトを作成する", type="primary")
            if submitted:
                with st.spinner("カスタマイズスクリプトを作成中..."):
                    q_a_text = "\n".join([f"Q: {st.session_state.questions[i]}\nA: {ans}" for i, ans in user_answers.items()])
                    
                    script_prompt = f"""
以下の元の対話とユーザーの回答をもとに、英語の完成スクリプトを作成してください。

【元の対話】
{st.session_state.transcription}

【ユーザーの回答】
{q_a_text}
"""
                    try:
                        response = model.generate_content(script_prompt)
                        generated_script = response.text
                        st.session_state.script = generated_script
                        
                        # 履歴に自動追加
                        today_str = datetime.date.today().strftime("%Y-%m-%d %H:%M")
                        st.session_state.history.append({
                            "date": today_str,
                            "script": generated_script
                        })
                        
                        st.session_state.page = "step3"
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成エラーが発生しました: {e}")

# 【STEP 3：完成＆ダウンロード】
elif st.session_state.page == "step3":
    st.title("🎧 komoEngConvApp_1")
    st.subheader("STEP 3: 完成スクリプトの確認とダウンロード")
    
    if st.session_state.script:
        st.markdown("### 📄 作成されたスクリプト")
        st.markdown(st.session_state.script)
        
        st.markdown("---")
        st.download_button(
            label="💾 スクリプトをテキストファイル（.txt）でダウンロード",
            data=st.session_state.script,
            file_name="radio_english_script.txt",
            mime="text/plain"
        )
        
        st.markdown("---")
        st.markdown("### 🚀 次のステップへ進む")
        st.link_button(
            "🎧 後半アプリ（ロールプレイ＆音声練習）を開く", 
            PART2_APP_URL, 
            type="primary",
            use_container_width=True
        )
        
        st.markdown("---")
        if st.button("🔄 最初からやり直す"):
            st.session_state.page = "step0"
            st.session_state.uploaded_image = None
            st.session_state.transcription = ""
            st.session_state.questions = []
            st.session_state.script = ""
            st.rerun()
