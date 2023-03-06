FROM joyzoursky/python-chromedriver:3.8

WORKDIR /football_parser
COPY requirements.txt /football_parser
RUN pip install -r requirements.txt

COPY . /football_parser

CMD ["python3", "main.py"]