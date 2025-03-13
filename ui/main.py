import asyncio
import os
from typing import List, Optional, Tuple

import streamlit as st
import base64
from langserve import RemoteRunnable
from streamlit.logger import get_logger


logger = get_logger(__name__)



# 🌟 Configuration de la page Streamlit
st.set_page_config(page_title="HealthCare Agent", page_icon="🤖", layout="wide")

# 📂 Définition des chemins des images
LOGO_PATH = "images/D&AMedlabs_long.jpg"
HEADER_IMAGE_PATH = "images/network_colored.jpg"

# 🔄 Fonction pour encoder une image en Base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# 🌟 Affichage de l'en-tête
def display_header():
    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <img src="data:image/png;base64,{get_base64_image(LOGO_PATH)}" style="width: 150px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-size: 24px; font-weight: bold; color: #0d1b2a;">D&A Medlabs</div>
    </div>
    """, unsafe_allow_html=True)

# 🌟 Gestion de l'affichage (accueil ou chatbot)
if "chat_started" not in st.session_state:
    st.session_state.chat_started = False

# 🌟 Page d'accueil
display_header()

st.markdown("""
<h1 style='text-align:center; margin-bottom:20px;'>AI Medical Research Assistant</h1>
<h3 style='text-align:center; color:#4a4a4a; margin-bottom:25px;'>Transforming Biomedical Data into Clinical Insights</h3>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])  # Ajuste les colonnes pour centrer l'image
with col2:
    st.image(HEADER_IMAGE_PATH, width=600)  # Change la largeur selon ton besoin

st.markdown("<p style='text-align:center; color: #666;'>Advanced Neural Network Architecture</p>", unsafe_allow_html=True)

# 🌟 Bouton centré pour démarrer le chatbot
if not st.session_state.chat_started:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Démarrer le Chatbot 🚀", use_container_width=True):
            st.session_state.chat_started = True
            st.rerun()  # Rafraîchissement pour afficher le chatbot

# 🌟 Chatbot Interface (s'affiche après avoir cliqué sur le bouton)
if st.session_state.chat_started:
    st.title("HealthCare Agent 🤖")

    class StreamHandler:
        def __init__(self, container, status, initial_text=""):
            self.status = status
            self.container = container
            self.text = initial_text

        def new_token(self, token: str) -> None:
            self.text += token
            self.container.markdown(self.text)

        def new_status(self, status_update: str) -> None:
            status.update(label="Generating answer🤖", state="running", expanded=True)
            with status:
                st.write(status_update)

    # 🛠️ Initialisation de l'historique du chat
    if "generated" not in st.session_state:
        st.session_state["generated"] = []
    if "user_input" not in st.session_state:
        st.session_state["user_input"] = []

    # 📖 Affichage de l'historique des messages
    if st.session_state["generated"]:
        size = len(st.session_state["generated"])
        for i in range(max(size - 3, 0), size):
            with st.chat_message("user"):
                st.markdown(st.session_state["user_input"][i])
            with st.chat_message("assistant"):
                st.markdown(st.session_state["generated"][i])

    # 🔄 API pour le chatbot
    API_URL = os.getenv("CLINICAL_AGENT_URL", "http://localhost:8080/clinical-agent/")

    async def get_agent_response(input: str, stream_handler: StreamHandler, chat_history: Optional[List[Tuple]] = []):
        url = API_URL
        st.session_state["generated"].append("")
        remote_runnable = RemoteRunnable(url)
        async for chunk in remote_runnable.astream_log({"input": input, "chat_history": chat_history}):
            log_entry = chunk.ops[0]
            value = log_entry.get("value")
            if isinstance(value, dict) and isinstance(value.get("steps"), list):
                for step in value.get("steps"):
                    stream_handler.new_status(step["action"].log.strip("\n"))
            elif isinstance(value, str) and "ChatOpenAI" in log_entry["path"]:
                st.session_state["generated"][-1] += value
                stream_handler.new_token(value)

    def generate_history():
        context = []
        if st.session_state["generated"]:
            size = len(st.session_state["generated"])
            for i in range(max(size - 3, 0), size):
                context.append((st.session_state["user_input"][i], st.session_state["generated"][i]))
        return context

    # 🗣️ Gestion des entrées utilisateur
    if prompt := st.chat_input("How can I help you today?"):
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            status = st.status("Generating answer🤖")
            stream_handler = StreamHandler(st.empty(), status)

        chat_history = generate_history()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(get_agent_response(prompt, stream_handler, chat_history))
        loop.close()
        status.update(label="Finished!", state="complete", expanded=False)
        st.session_state.user_input.append(prompt)