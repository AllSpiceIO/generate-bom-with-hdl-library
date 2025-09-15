FROM python:3.12-bookworm

COPY requirements.txt /requirements.txt
COPY entrypoint.py /entrypoint.py
COPY cell.py /cell.py
COPY combinators.py /combinators.py
COPY css.py /css.py
COPY library.py /library.py

RUN pip install -r /requirements.txt

ENTRYPOINT [ "/entrypoint.py" ]
