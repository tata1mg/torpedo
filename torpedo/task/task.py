class Task:
    def __init__(self, func, result_key, is_main=True):
        self._func = func
        self._result_key = result_key
        self._result = None
        self._is_main = is_main

    @property
    def result_key(self):
        return self._result_key

    @property
    def func(self):
        return self._func

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, data):
        self._result = data

    @property
    def is_main(self):
        return self._is_main
