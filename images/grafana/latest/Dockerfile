ARG GRAFANA_TAG
FROM grafana/grafana:$GRAFANA_TAG
USER root
RUN echo 'root:root' | chpasswd
#
#
RUN apk update
RUN apk add vim
RUN apk add nano
RUN apk add python
RUN apk add py-pip
#
#
# apt-get not used since grafana went to ubuntu alpine
#
#
#
#
#-- RUN apt-get update
#-- RUN apt-get install -y vim
#-- RUN apt-get install -y nano

#-- RUN apt-get install -y python
#
# Network problem getching files at random made unreliable to
# install PIP from here. lines commented out
# Use root after sandbox enter grafana to manually install PIP, REQUESTS and RETRYING

# RUN apt-get install -y python-pip  --fix-missing

RUN pip install requests
RUN pip install retrying


RUN mkdir -p /home/grafana
RUN mkdir -p /var/log/shp
RUN chown grafana:grafana /home/grafana
RUN chown grafana:grafana /var/log/shp

USER grafana
RUN touch /var/log/shp/shp.log

#----------------------------------------------#
#RUN apt-get install -y openssh-server
#RUN mkdir /var/run/sshd
#
#
#RUN sed -ri 's/^#?PermitRootLogin\s+.*/PermitRootLogin yes/' /etc/ssh/sshd_config
#RUN sed -ri 's/UsePAM yes/#UsePAM yes/g' /etc/ssh/sshd_config

#RUN mkdir /root/.ssh

#EXPOSE 22
#CMD ["/usr/sbin/sshd","-D"]


