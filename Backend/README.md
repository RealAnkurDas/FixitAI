# FixitAI Backend
the backend for the FixitAI app

## How it works


## Setup
1. clone the repo
2. make an ngrok account using the link https://ngrok.com and follow the instructions for your recommended OS and activate the static link
3. install and activate the virtual environment
```
> py -m venv venv

# for Windows
> /venv/Scripts/activate

# for Linux and MacOS
> source <path_to_venv>/bin/activate 
```
4. Install the modules from `requirements.txt`
```
> pip install -r requirements.txt
```
5. Install `gemma3:latest` from ollama, if you haven't installed ollama yet, install it from this link: https://ollama.com/download
```
ollama pull gemma3:latest
```

## Run the backend
1. Enter the following command
```
> python api.py
```
2. to test this, go to `streamlittest.py`, switch the API_URL to your static Ngrok URL, and run the following command
```
> streamlit run streamlittest.py
```