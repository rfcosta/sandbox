ARG GRAFANA_TAG
FROM grafana/grafana:$GRAFANA_TAG
USER root
RUN echo 'root:root' | chpasswd
#
RUN apt-get update
RUN apt-get install -y vim
RUN apt-get install -y nano

RUN mkdir /home/grafana
RUN chown grafana:grafana /home/grafana

USER grafana
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


