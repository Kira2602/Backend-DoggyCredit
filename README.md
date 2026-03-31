# Backend-DoggyCredit-
Plataforma Inteligente de Crédito SaaS 
### Clonar el repositorio 💾
```sh
git clone https://github.com/Kira2602/Backend-DoggyCredit.git
```
```sh
cd Backend-DoggyCredit
```
### Levantar Docker (Tenerlo abierto antes)
```sh
docker compose up --build -d
```
## Ver contenedores
```sh
docker ps
```
## Comando extra: Ver contenedores
```sh
docker ps
```
### Comando extra: Para limpiar todo (volúmenes)
```sh
docker compose down -v
```
### Comandos para crear entorno local en cada microservicio
## autenticacion-tenant
```sh
cd servicios\autenticacion-tenant
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
cd ..\..
```

## integraciones
```sh
cd servicios\integraciones
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
cd ..\..
```
## perfil-financiero
```sh
cd servicios\perfil-financiero
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
cd ..\..
```
## scoring-recomendador
```sh
cd servicios\scoring-recomendador
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
cd ..\..
```
## Activar entorno cuando se chambee en ese microservicio 
## Ejemplo para autenticacion-tenant
```sh
cd servicios\autenticacion-tenant
.venv\Scripts\Activate.ps1
```
## Para desactivar el entorno 

```sh
deactivate
```
