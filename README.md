### Torpedo
Torpedo is a lightweight wrapper over the Sanic framework (https://github.com/huge-success/sanic)


### How to install

Make sure you have a virtualenv manager like virtualenv(https://pypi.org/project/virtualenv/) or 
pyenv(https://pypi.org/project/pyenv/) to manager virtual environments.

We prefer pyenv since it helps in managing python versions as well.

```
- git clone git@github.com:tata1mg/torpedo.git
- cd torpedo/

- python3 setup.py install 
    or 
- pip3 install git+ssh://git@github.com/tata1mg/torpedo.git
```
### How to use
Add this library as dependency in your service.
As of now this project is made public for using in selected projects.
Soon we will write open source version of this project.

### Configurations to be provided in service for this library 
- Create config.json in root directory of project
- Add below mandatory configurations in config.json:-
```
  "NAME": "service_name",
  "HTTP_VERSION": "1.0.0",
  "HOST": "0.0.0.0", //host on which service will be up
  "PORT": {PORT}, // port on which service shall listen
  "WORKERS": {worker}, //like 2
  "DEBUG": false,
  "SENTRY": {
            "DSN": "<DSN LINK>",
            "EM": "",
            "ENVIRONMENT": "<env_name>"
  },
  "APM": {
    "ENABLED": false,
    "ENVIRONMENT": "local",
    "SECRET_TOKEN": "",
    "SERVER_TIMEOUT": "30s",
    "SERVER_URL": "localhost",
    "SPAN_FRAMES_MIN_DURATION": "10ms",
    "TRANSACTION_SAMPLE_RATE": 0.1
  }
```

### How to raise issues
Please use github issues to raise any bug or feature request

### Discussions

Please use github discussions for any topic related to this project

### Contributions

Soon we will be inviting open source contributions.

### Supported python versions
3.7.x,3.8.x,3.9.x
