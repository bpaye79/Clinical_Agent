import asyncio
import os
from typing import List, Optional, Tuple

import streamlit as st
import base64
from langserve import RemoteRunnable
from streamlit.logger import get_logger


logger = get_logger(__name__)



st.set_page_config(page_title="HealthCare Agent", page_icon="🤖", layout="wide")

LOGO_PATH = "images/D&AMedlabs_long.jpg"


# Custom CSS styles
st.markdown(f"""
<style>
    /* Header container styling */
    .header-container {{
        padding: 20px;
        margin-bottom: 10px;
    }}
    
    /* Logo container styling */
    .logo-wrapper {{
        display: flex;
        flex-direction: column;
        gap: 8px;
        align-items: flex-start;
    }}
    
    /* Enhanced logo styling (+10%) */
    .company-logo {{
        width: 103px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    
    /* Company name styling */
    .company-name {{
        font-size: 24px;
        color: #0d1b2a;
        font-weight: 600;
        margin-left: 5px;
    }}
    
    /* Image caption styling */
    .image-caption {{
        text-align: center;
        color: #666;
        margin-top: 8px;
        margin-bottom: 30px;
    }}
</style>
""", unsafe_allow_html=True)


# Ajouter cette fonction d'aide pour encoder l'image
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def display_header():
    # """Displays header with logo and company name"""
    # # Solution 1 : Utilisation native de Streamlit
    # col1, col2 = st.columns([1, 4])
    # with col1:
    #     st.image(
    #         LOGO_PATH,
    #         width=103,  # +10% de la taille originale
    #         use_column_width=False
    #     )
    # st.markdown("<div class='company-name'>D&A Medlabs</div>", 
    #            unsafe_allow_html=True)

    # Solution alternative 2 : HTML corrigé
    st.markdown(f"""
    <div class='header-container'>
        <div class='logo-wrapper'>
            <img src="data:images/png;base64,{get_base64_image(LOGO_PATH)}" class="company-logo">
            <div class='company-name'>D&A Medlabs</div>
        </div>
    </div>
    """, unsafe_allow_html=True)



# Vérifier si l'utilisateur est sur la page d'accueil
if "page" not in st.session_state:
    st.session_state.page = "home"

# Page d'accueil
if st.session_state.page == "home":
    #st.title("Bienvenue sur l'Agent HealthCare 🤖")

    display_header()
    st.markdown("<h1 style='text-align: center;'>Bienvenue sur l'Agent HealthCare 🤖</h1>", unsafe_allow_html=True)
    


    #st.image("images/D&AMedlabs_long.jpg",use_container_width=True)  # Image temporaire
   
    st.markdown("### Cliquez ci-dessous pour commencer à discuter avec l'agent 👇")

    if st.button("Démarrer le Chatbot 🚀"):
        st.session_state.page = "chatbot"
        st.rerun()

# Page Chatbot
elif st.session_state.page == "chatbot":

    st.title("HealthCare agent")
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


    # Initialize chat history
    if "generated" not in st.session_state:
        st.session_state["generated"] = []
    if "user_input" not in st.session_state:
        st.session_state["user_input"] = []

    # Display user message in chat message container
    if st.session_state["generated"]:
        size = len(st.session_state["generated"])
        # Display only the last three exchanges
        for i in range(max(size - 3, 0), size):
            with st.chat_message("user"):
                st.markdown(st.session_state["user_input"][i])
            with st.chat_message("assistant"):
                st.markdown(st.session_state["generated"][i])


    API_URL = os.getenv("CLINICAL_AGENT_URL", "http://localhost:8080/clinical-agent/")
    async def get_agent_response(
        input: str, stream_handler: StreamHandler, chat_history: Optional[List[Tuple]] = []
    ):
        url = API_URL
        st.session_state["generated"].append("")
        remote_runnable = RemoteRunnable(url)
        async for chunk in remote_runnable.astream_log(
            {"input": input, "chat_history": chat_history}
        ):
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
        # If any history exists
        if st.session_state["generated"]:
            # Add the last three exchanges
            size = len(st.session_state["generated"])
            for i in range(max(size - 3, 0), size):
                context.append(
                    (st.session_state["user_input"][i], st.session_state["generated"][i])
                )
        return context


    # Accept user input
    if prompt := st.chat_input("How can I help you today?"):
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            status = st.status("Generating answer🤖")
            stream_handler = StreamHandler(st.empty(), status)

        chat_history = generate_history()
        # Create an event loop: this is needed to run asynchronous functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Run the asynchronous function within the event loop
        loop.run_until_complete(get_agent_response(prompt, stream_handler, chat_history))
        # Close the event loop
        loop.close()
        status.update(label="Finished!", state="complete", expanded=False)
        # Add user message to chat history
        st.session_state.user_input.append(prompt)
