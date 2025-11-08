import os
import json
from typing_extensions import TypedDict
from typing import List

# LangChain Imports
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_tavily import TavilySearch  # This is the new, correct import
from langchain_core.documents import Document

# LangGraph Imports
from langgraph.graph import END, StateGraph

# --- Local Imports ---
from src.llm import llm 
from src.chat_history import get_user_chat_history 

# --- 1. SET UP TOOLS ---

# Initialize our local vector store
print("Initializing LangChain vector store wrappers with FastEmbed...")
lc_embedder = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
vector_store = Chroma(
    persist_directory="db_storage/chroma_db",
    collection_name="text_collection",
    embedding_function=lc_embedder
)
# We retrieve 3 docs to give the grader more options
retriever = vector_store.as_retriever(search_kwargs={"k": 3}) 

# Initialize our new web search tool
print("Initializing Tavily web search tool...")
web_search_tool = TavilySearch(max_results=3) 

# --- 2. DEFINE THE CRAG "STATE" ---

class GraphState(TypedDict):
    question: str
    user_id: str
    session_id: str
    documents: List[Document]
    chat_history: str
    generation: str
    relevance: str  # This will be "yes" or "no"

# --- 3. DEFINE THE CRAG "NODES" ---

def load_history(state: GraphState):
    """Loads chat history into the state."""
    print("---NODE: LOADING HISTORY---")
    history = get_user_chat_history(state["user_id"], state["session_id"])
    return {"chat_history": history}

def retrieve(state: GraphState):
    """Retrieves documents from our local ChromaDB."""
    print("---NODE: RETRIEVING DOCUMENTS---")
    question = state["question"]
    documents = retriever.invoke(question)
    print(f"Retrieved {len(documents)} documents locally.")
    return {"documents": documents}

# --- START OF NEW MULTI-FACTOR GRADER ---

# Define the Pydantic schema for our new grader
class DocumentGrader(BaseModel):
    topical_relevance: int = Field(..., description="A score from 1-10 of how well the document's *main topic* matches the query.")
    specific_answer: int = Field(..., description="A score from 1-10 of whether the document *directly answers* the specific question.")

def grade_documents(state: GraphState):
    """
    Grades the relevance of retrieved documents using a multi-factor threshold.
    """
    print("---NODE: GRADING DOCUMENTS---")
    question = state["question"]
    documents = state["documents"]
    
    if not documents:
        print("No documents found, triggering web search.")
        return {"relevance": "no"}

    # Create a JSON parser
    parser = JsonOutputParser(pydantic_object=DocumentGrader)

    # Create the grader chain
    grader_prompt = ChatPromptTemplate.from_template(
        """
        You are a strict, objective grader. Your job is to assess a document
        based on two factors relative to the user's question:
        1.  topical_relevance: How well does the document's main topic match? (Score 1-10)
        2.  specific_answer: How well does the document provide a direct answer? (Score 1-10)
        
        Respond *only* with a valid JSON object.
        
        {format_instructions}
        
        Document:
        {document}
        
        User Question:
        {question}
        """
    )
    
    grader_chain = grader_prompt | llm | parser
    
    is_relevant = "no"
    for doc in documents:
        try:
            # The result is now a dictionary, e.g., {'topical_relevance': 8, 'specific_answer': 4}
            result = grader_chain.invoke({
                "question": question, 
                "document": doc.page_content,
                "format_instructions": parser.get_format_instructions()
            })
            
            # Calculate the average score (out of 10)
            avg_score = (result['topical_relevance'] + result['specific_answer']) / 2
            
            print(f"Document score: {avg_score}/10")
            
            # --- THIS IS YOUR 50% THRESHOLD (5/10) ---
            if avg_score >= 5:
                is_relevant = "yes"
                print("Decision: Document is relevant. Using local data.")
                break # We only need one good doc to proceed
                
        except Exception as e:
            # If the LLM fails to return valid JSON, just give it a 0
            print(f"Grader failed to parse: {e}")
            print(f"Document score: 0/10")
            pass
            
    print(f"Final Grader decision: {is_relevant}")
    return {"relevance": is_relevant}

# --- END OF NEW MULTI-FACTOR GRADER ---

def web_search(state: GraphState):
    """
    Performs a web search using Tavily if local documents are not relevant.
    This is the "C" (Corrective) in CRAG.
    """
    print("---NODE: SEARCHING WEB---")
    question = state["question"]
    
    # Call Tavily
    # This returns a simple list of strings: [snippet1, snippet2, snippet3]
    search_results = web_search_tool.invoke(question) 
    
    # --- START OF FIX ---
    # Format results as LangChain Documents
    # We now loop through the list of strings (snippets)
    web_docs = [
        Document(
            page_content=snippet,
            metadata={"source": "web_search", "title": "Tavily Search Result"}
        ) for snippet in search_results
    ]
    # --- END OF FIX ---
    
    print(f"Found {len(web_docs)} results from web search.")
    return {"documents": web_docs}

def generate(state: GraphState):
    """
    Generates the final answer using the LLM and the provided context.
    """
    print("---NODE: GENERATING ANSWER---")
    question = state["question"]
    documents = state["documents"]
    chat_history = state["chat_history"]
    
    PROMPT_TEMPLATE = """
    ---
    ### Persona
    You are LegalBuddy, a friendly and empathetic legal guide. Your main goal is to help users understand complex legal topics using simple, clear, and reassuring language. Your tone should be that of a patient not a robot and understanding expert who is here to help.

    ### Core Task
    Your primary goal is to answer the user's question using the 'Context' provided below.

    ### Rules for Answering
    1.  **Be Simple and Clear:** Explain the answer as if you're talking to a friend. Avoid robotic phrases and dense legal jargon. If you must use a legal term, briefly explain what it means.
    2.  **Be Conversational:** Start your response in a natural, helpful way. **Do not** begin with "Based on the provided context...". A good start would be, "I feel bad to hear that something this bad happened, here's what can be done..." or "I can certainly help with that."
    3.  **Handle All Legal Topics:** Treat all queries as requests for legal information. You MUST NOT refuse to answer questions about criminal law.
    4.  **Be Honest if You Don't Know:** If the answer isn't in your documents, just say so in a helpful way.
    5.  **Use History:** Pay attention to the 'Chat History' to understand the conversation.

    ---

    ### Context
    {context}

    ### Chat History
    {chat_history}

    ### Question
    {question}

    ### Helpful Answer
    """
    
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    
    rag_chain = (
        prompt
        | llm
        | StrOutputParser()
    )
    
    context_str = "\n\n---\n\n".join(
        f"Source: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content}"
        for doc in documents
    )
    
    generation = rag_chain.invoke({
        "context": context_str,
        "question": question,
        "chat_history": chat_history
    })
    
    return {"generation": generation}

# --- 4. DEFINE THE CRAG "EDGES" (CONDITIONAL LOGIC) ---

def decide_to_search(state: GraphState):
    """
    This is the conditional edge. It decides whether to go to
    web_search or generate based on the grader's decision.
    """
    print("---DECISION: WEB SEARCH OR GENERATE?---")
    if state["relevance"] == "no":
        print("Decision: Documents are not relevant. Triggering web search.")
        return "web_search"
    else:
        print("Decision: Documents are relevant. Proceeding to generation.")
        return "generate"

# --- 5. BUILD AND COMPILE THE GRAPH ---

print("Building CRAG workflow...")
workflow = StateGraph(GraphState)

# Add all the nodes
workflow.add_node("load_history", load_history)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("web_search", web_search)
workflow.add_node("generate", generate)

# Define the graph's flow
workflow.set_entry_point("load_history")
workflow.add_edge("load_history", "retrieve")
workflow.add_edge("retrieve", "grade_documents")

workflow.add_conditional_edges(
    "grade_documents",
    decide_to_search,
    {
        "web_search": "web_search",
        "generate": "generate"
    }
)

workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
print("CRAG workflow compiled successfully.")


# --- 6. THE MAIN INTERFACE FUNCTION (This is what app/main.py calls) ---

def get_rag_response(query: str, user_id: str, session_id: str):
    """
    Gets a response from the new CRAG graph.
    """
    if not llm:
        return "Error: LLM not initialized. Please check src/llm.py"
        
    print(f"Processing CRAG query for user '{user_id}'...")
    
    inputs = {
        "question": query,
        "user_id": user_id,
        "session_id": session_id
    }
    
    final_state = app.invoke(inputs)
    
    return final_state["generation"]

if __name__ == "__main__":
    # This allows you to test this file directly
    # Run: python -m src.rag_pipeline
    
    print("Testing CRAG pipeline...")
    test_query = "What are the bail procedures in India?"
    test_user = "test_user"
    test_session = "test_session_123"
    
    response = get_rag_response(test_query, test_user, test_session)
    
    print(f"\nTest Query: {test_query}")
    print(f"\nTest Response: {response}")