from torpedo import Host

if __name__ == '__main__':
    config = {
        "NAME": "basic",
        "HOST": "0.0.0.0",
        "PORT": 6581,
        "DEBUG": True
    }

    Host._name = config['NAME']
    Host._host = config['HOST']
    Host._port = config['PORT']
    Host._workers = config.get('WORKER', 2)
    Host._debug = config['DEBUG']
    Host._config = config

    Host.run()
