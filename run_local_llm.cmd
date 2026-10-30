@echo off
setlocal

where ollama >nul 2>nul
if errorlevel 1 (
    echo Ollama was not found. Please install Ollama first.
    echo Then run: ollama pull llama3.2:3b
    exit /b 1
)

echo Starting Ollama local LLM server on http://127.0.0.1:11434
ollama serve
