FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=jazzy

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws/src
RUN git clone -b jazzy --depth 1 https://github.com/ROBOTIS-GIT/DynamixelSDK.git \
    && git clone -b jazzy --depth 1 https://github.com/ROBOTIS-GIT/dynamixel_interfaces.git \
    && git clone -b jazzy --depth 1 https://github.com/ROBOTIS-GIT/dynamixel_hardware_interface.git \
    && git clone -b jazzy --depth 1 https://github.com/ROBOTIS-GIT/open_manipulator.git

WORKDIR /ros2_ws
# Playground pulls robotis_interfaces (not needed for OMX-F bringup).
RUN rm -rf src/open_manipulator/open_manipulator_playground

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
        ros-jazzy-controller-manager \
        ros-jazzy-joint-state-broadcaster \
        ros-jazzy-joint-trajectory-controller \
        ros-jazzy-gripper-controllers \
        ros-jazzy-hardware-interface \
        ros-jazzy-xacro \
        ros-jazzy-moveit-configs-utils \
    && rosdep init 2>/dev/null || true \
    && rosdep update \
    && rosdep install --from-paths src -y --ignore-src --rosdistro jazzy \
        --skip-keys robotis_interfaces \
    && rm -rf /var/lib/apt/lists/*

RUN bash -c "source /opt/ros/jazzy/setup.bash && colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release"

WORKDIR /workspace/omx-framework
COPY pyproject.toml README.md ./
COPY agent ./agent
COPY configs ./configs
RUN pip3 install --no-cache-dir --break-system-packages ".[agent]"

EXPOSE 8501

COPY docker/omx-follower/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
