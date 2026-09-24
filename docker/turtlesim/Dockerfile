FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    ros-humble-turtlesim \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir fastapi uvicorn

WORKDIR /workspace
COPY bridge/turtlesim_bridge.py /workspace/turtlesim_bridge.py

# turtlesim_node + bridge; publicar 8000 al host
EXPOSE 8000

RUN sed -i 's/\r$//' /dev/null 2>/dev/null || true
COPY docker/turtlesim/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
