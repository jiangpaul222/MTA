FROM python:3.10.8

RUN mkdir /streamlit

COPY requirements.txt /streamlit

WORKDIR /streamlit

RUN pip install -r requirements.txt

COPY . /streamlit

EXPOSE 5000

CMD ["streamlit", "run", "app.py", "--server.port", "5000"]
