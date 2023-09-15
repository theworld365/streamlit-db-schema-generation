from langchain.chains.llm import LLMChain
from langchain.callbacks import StreamlitCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
import streamlit as st
import string
import base64
import zlib
import requests

maketrans = bytes.maketrans
plantuml_alphabet = string.digits + string.ascii_uppercase + string.ascii_lowercase + '-_'
base64_alphabet   = string.ascii_uppercase + string.ascii_lowercase + string.digits + '+/'
b64_to_plantuml = maketrans(base64_alphabet.encode('utf-8'), plantuml_alphabet.encode('utf-8'))
plantuml_to_b64 = maketrans(plantuml_alphabet.encode('utf-8'), base64_alphabet.encode('utf-8'))

st.set_page_config(
    page_title="TEQ AI - DB Schema generator",
    layout="wide"
)

with st.sidebar:
  st.image(image ="https://teqnological.asia/images/companyLogo.webp", width=240)
  "[Teqnological Asia - AI Team](https://teqnological.asia)"
  "Contact us: ai-team@teqnological.asia"
  database = st.selectbox("Database you use:",('MySQL 5.7', 'MySQL 8.0', 'Postgres 12','Postgres 13','Postgres 14','Postgres 15'))
  btn_reset = st.button("RESTART")
  if btn_reset:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you in designing database ?"}]
    st.session_state["last_schema"] = ""

openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.")
    st.stop()
    
llm = ChatOpenAI(model="gpt-3.5-turbo-16k", openai_api_key=openai_api_key, temperature=0)

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
Act as a database engineer. You'll only respond to me SQL schema code that I can use in {database} database. I will describe what I want in plain English and you will respond with the database schema which I can use to create the database. This is a relational database so you should de-normalise the tables and add relationships where appropriate.
Do not write any explanations. If you don't know the answer, just say that you don't know, don't try to make up an answer.
The answer is below format
Schema: 
```sql
-- table name
CREATE TABLE `table` (
  `id` INT AUTO_INCREMENT NOT NULL, -- important
  /* other fields */
);
```

You will continue to update this schema {history}
"""

user_prompting = "{message}. You update Schema and response in full Schema with include previous schema if had. You DO NOT use Alter table"

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
# database = "Mysql 8.0"

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
          # convert content to plantuml 
          
          
          st.image(image='https://plantuml.com/plantuml/svg/{0}'.format(plantuml_encode(uml)))
          # st.text(uml)
