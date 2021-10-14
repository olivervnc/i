python -c "from google.colab import drive;drive.mount('/content/drive')"
clear
nohup git clone https://github.com/olivervnc/i.git
cd i
nohup pip install -r requirements.txt
nohup python main.py
