from pydantic.error_wrappers import ValidationError

from torpedo.exceptions import BadRequestException


class Validator:
    """
    Base Validator
    """

    def __init__(self):
        pass

    @classmethod
    def validate_schema(cls, validator_class, data):
        """
        Validate data against a provided schema
        :param validator_class: Validator class
        :param data: Input data
        :return: Validated data
        """
        try:
            return validator_class(**data)
        except (ValidationError, Exception) as e:
            errors = e.errors()
            raise BadRequestException("Invalid Parameters", meta={"errors": errors})
