FROM agrdocker/agr_base_linux_env:latest

WORKDIR /usr/src/app

RUN mkdir /usr/src/app/output
RUN mkdir /usr/src/app/input

ADD requirements.txt .

RUN pip3 install -r requirements.txt

ADD . .

ENTRYPOINT [ "/bin/bash" ]