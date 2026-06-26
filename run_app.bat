@echo off
chcp 65001 > nul
py -m pip install -r requirements.txt
py -m streamlit run app.py
pause
