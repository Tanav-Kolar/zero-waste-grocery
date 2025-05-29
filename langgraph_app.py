# langgraph_app.py
from langchain.vectorstores import FAISS
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langgraph.graph import StateGraph, END
from groq import Groq
import os
from typing import TypedDict, List, Tuple


from langgraph.graph import END, START, MessagesState, StateGraph

from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")


class State(TypedDict):
    query: str
    docs: list
    recipe: str
    result: str
    chat_history: List[Tuple[str, str]]
    step_index: int
    continue_chat: bool  

api_key = "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"
client = Groq(api_key=api_key)

# Build Vector Store
def build_vectorstore():
    loader = TextLoader("recipes.txt")
    docs = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = text_splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    return vectorstore

vectorstore = build_vectorstore()
retriever = vectorstore.as_retriever()

def format_chat_history(history):
    return "\n".join([f"{role}: {msg}" for role, msg in history])

def retrieve_step(state):
    query = state["query"]
    docs = retriever.get_relevant_documents(query)
    return {
        **state,
        "docs": docs,
        "chat_history": state.get("chat_history", []) + [("user", query)]
    }

def generate_step(state):
    docs = state["docs"]
    context = "\n".join([doc.page_content for doc in docs])
    history = state["chat_history"]
    prompt = f"""
You are a zero-waste cooking assistant.
Use only these ingredients: {state['query']}.
Use this context:
{context}

Conversation:
{format_chat_history(history)}

Generate a creative, waste-free recipe and steps.
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_completion_tokens=1024,
        top_p=1,
        stream=False
    )

    message = response.choices[0].message.content
    return {
        **state,
        "result": message,
        "chat_history": history + [("assistant", message)],
        "recipe": message,
        "step_index": state["step_index"] + 1
    }

def followup_step(state):
    query = state["query"]
    history = state["chat_history"]
    recipe = state["recipe"]
    prompt = f"""
Continue the cooking conversation about this recipe:
{recipe}

Conversation:
{format_chat_history(history)}

User: {query}
Assistant:
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=False
    )

    message = response.choices[0].message.content
    return {
        **state,
        "result": message,
        "chat_history": history + [("assistant", message)],
        "recipe": recipe,
        "continue_chat": False,
        "step_index": state["step_index"] + 1
    }

def entry_condition(state: State) -> str:
    # If it's the first turn, go to retrieve
    if state["step_index"] == 0:
        return "retrieve"
    else:
        return "followup"

builder = StateGraph(State)
builder.add_node("retrieve", retrieve_step)
builder.add_node("generate", generate_step)
builder.add_node("followup", followup_step)

builder.set_conditional_entry_point(entry_condition)
builder.add_edge("retrieve", "generate")
#builder.add_edge("generate", "followup")
#builder.add_edge("followup", "followup")



# 🔁 Conditional routing to either continue or end the chat
def followup_condition(state: State) -> str:
    # Continue followup if flag is True, else end
    if state.get("continue_chat", False):
        return "followup"
    else:
        return "__end__"

builder.add_conditional_edges(
    "followup",
    followup_condition,
    {
        "followup": "followup",
        "__end__": END
    }
)

app_flow = builder.compile()
