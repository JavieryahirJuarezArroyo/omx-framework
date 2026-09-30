# OMX-F follower + omx-framework (ROS 2 Jazzy en Docker)

## Modos

| Modo | Variable | Uso |
|------|----------|-----|
| **Mock** (sin USB) | `OMX_USE_MOCK=true` (default) | Probar chat + tools sin cable |
| **Hardware** | `OMX_USE_MOCK=false` + `OMX_SERIAL_DEVICE=/dev/ttyACM0` | Brazo real por USB en Linux/WSL |

## Windows (PowerShell)

```powershell
cd omx-framework
.\scripts\run-omx-follower-agent.ps1
```

Chat: **http://localhost:8503** (puerto por defecto).

Primera build: **15–30 min** (clona y compila `open_manipulator`).

### USB real en Windows (COM3 / VID 2f5d:2202)

Docker **no usa COM3** directamente. Hay que pasar el USB a la VM de Docker Desktop con **usbipd-win**:

```powershell
winget install dorssel.usbipd-win
# Clic derecho → Ejecutar como administrador:
.\scripts\setup-omx-usb.ps1

# Luego, PowerShell normal:
.\scripts\run-omx-follower-agent.ps1 -Hardware -SkipBuild
```

Si el bus USB cambia, `setup-omx-usb.ps1` detecta `2f5d:2202` automáticamente.

Alternativa manual:

```powershell
$env:OMX_USE_MOCK = "false"
$env:OMX_SERIAL_DEVICE = "/dev/ttyACM0"
.\scripts\run-omx-follower-agent.ps1 -SkipBuild
```

## Dentro del contenedor (manual)

```bash
docker exec -it omx-follower-run bash
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
ros2 topic echo /joint_states --once
```

## Perfil JSON

`configs/robots/open_manipulator_omx_f.json` — mismo contrato que el bringup ROBOTIS (`FollowJointTrajectory`, gripper, torque).

## Official ROBOTIS (alternativa)

Si prefieres el contenedor oficial:

```bash
git clone -b jazzy https://github.com/ROBOTIS-GIT/open_manipulator.git
cd open_manipulator/docker && ./container.sh start
```

Monta `omx-framework` dentro y ejecuta `ROS_AGENT_ROBOT=open_manipulator_omx_f python -m agent.server`.
