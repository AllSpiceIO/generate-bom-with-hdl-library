FROM python:3.12-bookworm

COPY requirements.txt /requirements.txt
COPY entrypoint.py /entrypoint.py
COPY ptflib.py /ptflib.py

RUN pip install -r /requirements.txt

ENTRYPOINT [ "/entrypoint.py" ]
