# 🧾 Project Title: LegalBuddy – AI-Powered Legal Assistance Platform

### 📌 Problem Statement

Access to legal information in India remains a significant barrier for the general public. Legal documents such as statutes and case law are often complex, lengthy, and difficult to navigate without formal training. Traditional legal search engines primarily cater to professionals and are not optimized for conversational, layman-level queries.

There is a critical need for:
- Intuitive, conversational access to legal knowledge
- Context-aware responses grounded in actual legal documents
- A system that can assist non-experts in understanding legal procedures and rights

---

### 💡 Use Case

**LegalBuddy** is an AI-driven legal assistant that helps users query Indian legal topics in natural language and receive accurate, statute-based responses. It is built using Retrieval-Augmented Generation (RAG) and integrates a fine-tuned LLM with a structured legal knowledge base.

**Target Users Include:**
- Individuals seeking quick and understandable legal advice
- NGOs and social workers involved in legal awareness initiatives
- Law students and researchers looking for interactive legal references
- Citizens involved in or considering legal action, needing preliminary guidance

LegalBuddy bridges the accessibility gap by simplifying complex legal content and delivering reliable responses through a conversational interface.

---

## ⚙️ Setup Instructions

1.  **Install System Dependencies (for PyPDFLoader):**
    ```sh
    sudo apt-get update
    sudo apt-get install -y poppler-utils
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```sh
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Libraries:**
    ```sh
    pip install -r requirements.txt
    ```