import aiotask_context as context


class SharedContext:
    @classmethod
    def set(cls, key, value):
        key = cls.transform_key(key)
        context.set(key, value)
        return

    @classmethod
    def get(cls, key) -> str:
        key = cls.transform_key(key)
        value = context.get(key)
        return value

    @classmethod
    def transform_key(cls, key):
        return key.lower()
