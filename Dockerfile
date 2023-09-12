FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

WORKDIR /apps

COPY requirements.txt ./

RUN pip install --upgrade pip 

RUN pip install -r requirements.txt

COPY . . 

EXPOSE 8080

CMD ["waitress-serve", "app:app"]


