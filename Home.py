from langchain.llms import OpenAI
from langchain.chains.llm import LLMChain
from langchain.agents import AgentType, initialize_agent, load_tools
from langchain.callbacks import StreamlitCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate
)
import streamlit as st
import string
import base64
import zlib
import requests
import ga

maketrans = bytes.maketrans
plantuml_alphabet = string.digits + string.ascii_uppercase + string.ascii_lowercase + '-_'
base64_alphabet   = string.ascii_uppercase + string.ascii_lowercase + string.digits + '+/'
b64_to_plantuml = maketrans(base64_alphabet.encode('utf-8'), plantuml_alphabet.encode('utf-8'))
plantuml_to_b64 = maketrans(plantuml_alphabet.encode('utf-8'), base64_alphabet.encode('utf-8'))

st.set_page_config(
    page_title="TEQ AI - DB Schema generator",
    layout="wide"
)
ga.add_analytics_tag()

llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k", streaming=True)

def plantuml_encode(plantuml_text):
    """zlib compress the plantuml text and encode it for the plantuml server"""
    zlibbed_str = zlib.compress(plantuml_text.encode('utf-8'))
    compressed_string = zlibbed_str[2:-4]
    return base64.b64encode(compressed_string).translate(b64_to_plantuml).decode('utf-8')

def plantuml_decode(plantuml_url):
    """decode plantuml encoded url back to plantuml text"""
    data = base64.b64decode(plantuml_url.translate(plantuml_to_b64).encode("utf-8"))
    dec = zlib.decompressobj() # without check the crc.
    header = b'x\x9c'
    return dec.decompress(header + data).decode("utf-8")

def get_history(messages):
  resp = ""
  for msg in messages:
    resp = msg["content"] + "." if msg["role"] == "assistant" else ""
  return resp

def process_response(msg):
  start_uml = msg.find("@startuml")
  end_uml = msg.find("@enduml") + len("@enduml")
  uml = ""
  content = msg
  if start_uml != -1 and end_uml != -1:
    uml = msg[start_uml: end_uml]
    start_uml = msg.find("PlantUML:")
    content = msg[0:start_uml] 
  return content, uml

template_promting = """
Act as a database engineer. You'll only respond to me SQL code that I can use in a {database} database. I will describe what I want in plain English and you will respond with the database schema which I can use to create the database. This is a relational database so you should de-normalise the tables and add relationships where appropriate.
After creating SQL code, convert it to plantUML code (http://www.plantuml.com), the codes must be forced by listed rules:
  - The definition of Primary key  is ```!define PK PRIMARY KEY``` and the definition of ForeignKey is ```!define FK FOREIGN KEY ```
  - Use Version 1.2023 or higher.
  - Do not incorporate other resources.
Do not write any explanations. If you don't know the answer, just say that you don't know, don't try to make up an answer.
The answer is below format
SQLSchema: (show SQL schema in markdown below)
PlantUML: (show PlantUML code markdown below)

You will use this previous {history}
"""

user_prompting = "{message}. You update SQL Schema and response full SQL Schema, DO NOT use Alter table"

prompt = ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template(
            template_promting
        ),
        HumanMessagePromptTemplate.from_template(user_prompting)
    ]
)
# Notice that we `return_messages=True` to fit into the MessagesPlaceholder
# Notice that `"chat_history"` aligns with the MessagesPlaceholder name.
# memory = ConversationBufferMemory(memory_key="history", input_key="database")
conversation = LLMChain(
    llm=llm,
    prompt=prompt,
    verbose=True
)
# set database type
database = "Mysql 8.0"

# st.markdown(uml_code)

# init messages
if "messages" not in st.session_state:
  st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you in designing database ?"}]
  st.session_state["last_schema"] = ""
  
# render messages chat
for msg in st.session_state["messages"]:
  with st.chat_message(msg["role"]):
    st.write(msg["content"])
  
# handle input of user
if prompt := st.chat_input():
    st.chat_message("user").write(prompt)
    with st.chat_message("assistant"):
        st_callback = StreamlitCallbackHandler(st.container())
        st.session_state.messages.append({"role": "user", "content": prompt})
        # response = chain.run(database=database,request=prompt,history=get_history(st.session_state["messages"]))
        response = conversation.run(message=prompt,database=database,history=st.session_state["last_schema"])
        content, uml = process_response(response)
        st.write(content)
        st.session_state["last_schema"] = content
        # if img := render_image(response):
        #   st.image(img.content,caption="Diagram is from plantuml.com")
        st.session_state.messages.append({"role": "assistant", "content": content})
        with st.expander("See diagram"):
          img = requests.get('https://plantuml.com/plantuml/png/{0}'.format(plantuml_encode(uml)))
          st.image(img.content, width=450)
