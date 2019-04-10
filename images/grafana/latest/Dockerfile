ARG GRAFANA_TAG
FROM grafana/grafana:$GRAFANA_TAG
USER root
RUN echo 'root:root' | chpasswd
#
RUN apt-get update
RUN apt-get install -y vim
RUN apt-get install -y nano

RUN apt-get install -y python
RUN apt-get install -y python-pip
RUN pip install requests


RUN mkdir /home/grafana
RUN mkdir /var/log/shp
RUN chown grafana:grafana /home/grafana
RUN chown grafana:grafana /var/log/shp

USER grafana
RUN touch /var/log/shp/shp.log
#
#RUN apt-get install -y openssh-server
#RUN mkdir /var/run/sshd
#
#
#RUN sed -ri 's/^#?PermitRootLogin\s+.*/PermitRootLogin yes/' /etc/ssh/sshd_config
#RUN sed -ri 's/UsePAM yes/#UsePAM yes/g' /etc/ssh/sshd_config

#RUN mkdir /root/.ssh

#EXPOSE 22
#CMD ["/usr/sbin/sshd","-D"]


