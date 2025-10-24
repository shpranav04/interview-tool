import streamlit as st
import google.generativeai as genai
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="StreamlitChatMessageHistory (Gemini)", page_icon="💬")
st.title("Chatbot✨")

# Initialize session state variables
if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "user_message_count" not in st.session_state:
    st.session_state.user_message_count = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "chat_complete" not in st.session_state:
    st.session_state.chat_complete = False
if "messages" not in st.session_state:
    st.session_state.messages = []  # Will store Gemini-formatted messages
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# Helper functions to update session state
def complete_setup():
    """Initializes the chat model with user details."""
    try:
        # Create the system instruction
        system_instruction = (
            f"You are an HR executive that interviews an interviewee called {st.session_state['name']} "
            f"with experience {st.session_state['experience']} and skills {st.session_state['skills']}. "
            f"You should interview him for the position {st.session_state['level']} {st.session_state['position']} "
            f"at the company {st.session_state['company']}. "
            "Start the interview by greeting the candidate and asking them to introduce themselves."
        )
        
        # Initialize the model and chat session
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        st.session_state.chat_session = model.start_chat(history=[])
        st.session_state.setup_complete = True
        st.session_state.messages = [] # Clear any previous messages
    except Exception as e:
        st.error(f"Failed to initialize model. Error: {e}")

def show_feedback():
    st.session_state.feedback_shown = True

# --- Setup Stage ---
if not st.session_state.setup_complete:
    st.subheader('Personal Information')

    # Initialize session state for personal information
    st.session_state.setdefault("name", "")
    st.session_state.setdefault("experience", "")
    st.session_state.setdefault("skills", "")

    # Get personal information input
    st.session_state["name"] = st.text_input(label="Name", value=st.session_state["name"], placeholder="Enter your name", max_chars=40)
    st.session_state["experience"] = st.text_area(label="Experience", value=st.session_state["experience"], placeholder="Describe your experience", max_chars=200)
    st.session_state["skills"] = st.text_area(label="Skills", value=st.session_state["skills"], placeholder="List your skills", max_chars=200)

    # Company and Position Section
    st.subheader('Company and Position')

    # Initialize session state for company and position information
    st.session_state.setdefault("level", "Junior")
    st.session_state.setdefault("position", "Data Scientist")
    st.session_state.setdefault("company", "Amazon")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state["level"] = st.radio(
            "Choose level",
            options=["Junior", "Mid-level", "Senior"],
            index=["Junior", "Mid-level", "Senior"].index(st.session_state["level"]),
            key="level_radio" # Added a unique key
        )
    with col2:
        st.session_state["position"] = st.selectbox(
            "Choose a position",
            ("Data Scientist", "Data Engineer", "ML Engineer", "BI Analyst", "Financial Analyst"),
            index=("Data Scientist", "Data Engineer", "ML Engineer", "BI Analyst", "Financial Analyst").index(st.session_state["position"])
        )
    st.session_state["company"] = st.selectbox(
        "Select a Company",
        ("Amazon", "Meta", "Udemy", "365 Company", "Nestle", "LinkedIn", "Spotify"),
        index=("Amazon", "Meta", "Udemy", "365 Company", "Nestle", "LinkedIn", "Spotify").index(st.session_state["company"])
    )

    # --- Gemini API Key Input has been removed ---

    # Button to complete setup
    st.button("Start Interview", on_click=complete_setup)

# --- Interview Phase ---
if st.session_state.setup_complete and not st.session_state.feedback_shown and not st.session_state.chat_complete:

    st.info("Start by introducing yourself 👋", icon="👋")
    
    # Display chat messages
    for message in st.session_state.messages:
        # Use the role ("user" or "assistant") to display the correct avatar
        with st.chat_message(message["role"]):
            st.markdown(message["parts"][0]) # Access the text content from 'parts'

    # Handle user input and Gemini response
    if st.session_state.user_message_count < 5:
        if prompt := st.chat_input("Your response", max_chars=1000):
            # Add user message to state and display
            st.session_state.messages.append({"role": "user", "parts": [prompt]})
            with st.chat_message("user"):
                st.markdown(prompt)

            if st.session_state.user_message_count < 4:
                # Use "assistant" for the role Streamlit understands
                with st.chat_message("assistant"): 
                    try:
                        # Send message to Gemini and stream response
                        stream = st.session_state.chat_session.send_message(prompt, stream=True)
                        
                        # Helper function to iterate over the stream and build the full response
                        def stream_gemini_response(stream):
                            full_response = ""
                            for chunk in stream:
                                if chunk.parts:
                                    text = chunk.parts[0].text
                                    full_response += text
                                    yield text
                                elif chunk.prompt_feedback:
                                    # Handle potential safety blocks
                                    st.error("Response blocked due to safety settings.")
                                    return
                        
                        response_text = st.write_stream(stream_gemini_response(stream))
                        # Store with the "assistant" role for Streamlit's UI
                        st.session_state.messages.append({"role": "assistant", "parts": [response_text]})
                    
                    except Exception as e:
                        st.error(f"An error occurred while generating the response: {e}")

            # Increment the user message count
            st.session_state.user_message_count += 1

    # Check if the user message count reaches 5
    if st.session_state.user_message_count >= 5:
        st.session_state.chat_complete = True
        st.rerun() # Rerun to show the "Get Feedback" button

# --- Show "Get Feedback" Button ---
if st.session_state.chat_complete and not st.session_state.feedback_shown:
    if st.button("Get Feedback", on_click=show_feedback):
        st.write("Fetching feedback...")
        st.rerun() # Rerun to show the feedback screen

# --- Show Feedback Screen ---
if st.session_state.feedback_shown:
    st.subheader("Feedback")

    # Format conversation history for the feedback prompt
    conversation_history = "\n".join(
        # This is just text, so "assistant" role is perfectly fine here
        f"{msg['role']}: {msg['parts'][0]}" for msg in st.session_state.messages
    )
    
    try:
        # Initialize a new Gemini model for feedback
        feedback_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction="""You are a helpful tool that provides feedback on an interviewee's performance.
Before the Feedback, give a score from 1 to 10.
Follow this exact format:
Overall Score: //Your score
Feedback: //Here you put your feedback
Give only the score and feedback; do not ask any additional questions.
"""
        )

        # Generate feedback
        feedback_prompt = (
            f"This is the interview you need to evaluate. Keep in mind that you are only a tool "
            f"and you shouldn't engage in any conversation:\n\n{conversation_history}"
        )
        
        with st.spinner("Generating feedback..."):
            feedback_completion = feedback_model.generate_content(feedback_prompt)
            st.write(feedback_completion.text)

    except Exception as e:
        st.error(f"Failed to generate feedback: {e}")
        st.write("Your API key might be invalid or a model error occurred.")
        
    # Button to restart the interview
    if st.button("Restart Interview", type="primary"):
        # Reload the entire page to reset the state
        streamlit_js_eval(js_expressions="parent.window.location.reload()")


