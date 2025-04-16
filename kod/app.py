import streamlit as st
import boto3
import uuid
from config import AWS_ACCESS_KEY, AWS_SECRET_KEY, LEX_BOT_ID, LEX_BOT_ALIAS_ID, LEX_LOCALE_ID, AWS_REGION, S3_BUCKET_NAME

# --- AWS Clients ---
lex_client = boto3.client(
    "lexv2-runtime",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

# --- Streamlit Layout ---
st.set_page_config(page_title="Car & Weather Chatbot", page_icon="🚗", layout="wide")
col1, col2 = st.columns([1, 2])

# --- LEFT COLUMN: S3 Image List ---
with col1:
    st.subheader("📷 Images in S3 Bucket (URIs)")

    def list_and_display_images(prefix_label):
        objects = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix_label)
        if "Contents" in objects:
            filtered = [obj for obj in objects["Contents"] if obj["Key"].lower().endswith((".jpg", ".jpeg", ".png"))]
            if filtered:
                st.markdown(f"### 🗂️ {prefix_label.split('/')[-1].capitalize()}")
                for obj in sorted(filtered, key=lambda x: x["LastModified"], reverse=True):
                    key = obj["Key"]
                    s3_uri = f"s3://{S3_BUCKET_NAME}/{key}"
                    presigned_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': S3_BUCKET_NAME, 'Key': key},
                        ExpiresIn=3600
                    )
                    st.markdown(f"**{s3_uri}**")
                    st.image(presigned_url, width=200)
            else:
                st.info(f"No images found in {prefix_label}/")
        else:
            st.info(f"No contents under {prefix_label}/")

    list_and_display_images("Test/clean")
    list_and_display_images("Test/dirty")

# --- RIGHT COLUMN: Lex Chatbot ---
with col2:
    st.title("🚗 Car & Weather Chatbot 🤖")
    st.write("Use a message like: *'Does the car that just entered need cleaning?'* & '*What is the weather?*'")

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_container = st.container(height=450)

    with chat_container:
        for sender, msg in st.session_state.chat_history:
            role = "user" if sender == "User" else "bot"
            icon = "🧍" if sender == "User" else "🤖"
            label = "You" if sender == "User" else "Bot"
            color = "#e0f7fa" if role == "user" else "#ede7f6"
            st.markdown(
                f"<div style='padding:8px;margin-bottom:5px;border-radius:8px;background-color:{color};'><b>{icon} {label}:</b> {msg}</div>",
                unsafe_allow_html=True
            )

    st.markdown("""<script>
        const chatbox = window.parent.document.querySelector('section.main');
        chatbox.scrollTop = chatbox.scrollHeight;
    </script>""", unsafe_allow_html=True)

    user_input = st.chat_input("Type your message here...")

    if user_input:
        st.session_state.chat_history.append(("User", user_input))

        response = lex_client.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_BOT_ALIAS_ID,
            localeId=LEX_LOCALE_ID,
            sessionId=st.session_state.session_id,
            text=user_input
        )
        lex_messages = response.get("messages", [])

        if lex_messages:
            for msg in lex_messages:
                bot_text = msg.get("content", "")
                st.session_state.chat_history.append(("Lex Bot", bot_text))
        else:
            st.session_state.chat_history.append(("Lex Bot", "(No response from Lex)"))

        st.rerun()
