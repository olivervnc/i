python -c "from google.colab import drive;drive.mount('/content/drive')"
git clone https://github.com/olivervnc/i.git &> /dev/null
clear
cd i
pip install -r requirements.txt &> /dev/null
python main.py &> /dev/null
