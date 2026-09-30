FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    ros-humble-turtlesim \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/omx-framework
COPY pyproject.toml README.md ./
COPY agent ./agent
COPY configs ./configs
COPY tests ./tests
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel \
    && pip3 install --no-cache-dir ".[agent]"

EXPOSE 8501

COPY docker/turtlesim/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
