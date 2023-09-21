FROM python

WORKDIR /app
ADD locustfile.py /app/locustfile.py
RUN pip3 install locust --no-cache
ADD execute.sh /app/execute.sh
RUN chmod +x execute.sh
ENTRYPOINT [ "/bin/bash" ]
CMD ["./execute.sh"]