# Local LLM RAG Setup

This project now supports database-grounded local LLM answers through Ollama.

## 1. Install Ollama

Install Ollama on the Windows server or development machine.

## 2. Download a small model

```powershell
ollama pull llama3.2:3b
```

For a stronger Bangla/English response model, you can also try:

```powershell
ollama pull qwen2.5:3b
```

## 3. Start Ollama

```powershell
ollama serve
```

Ollama should run at:

```text
http://127.0.0.1:11434
```

## 4. Run the Flask app

```powershell
cd D:\SoftwareGIT\PythonAuth
.\run_production.cmd
```

## Optional environment settings

```cmd
set RAG_LOCAL_LLM=1
set OLLAMA_MODEL=llama3.2:3b
set OLLAMA_URL=http://127.0.0.1:11434/api/generate
```

If Ollama is not running, the app will still answer using database fallback results.
