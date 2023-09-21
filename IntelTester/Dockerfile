FROM python

WORKDIR /persistent
WORKDIR /app
ADD tester.py /app/tester.py
ADD requirements.txt /app/requirements.txt
RUN pip3 install --no-cache -r requirements.txt
RUN chmod +x /app/tester.py
ENTRYPOINT [ "python3" ]
CMD ["/app/tester.py"]