FROM python:3.5
MAINTAINER philipp.holler93@googlemail.com

# Add python files
ADD /magnet-alldebrid-jd.py /
ADD /requirements.txt /

RUN pip install -r /requirements.txt \
 && rm /requirements.txt \
 && chmod +x /magnet-alldebrid-jd.py

CMD ["python", "/magnet-alldebrid-jd.py"]