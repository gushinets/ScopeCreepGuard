from scope_guard.api.errors import ApiError, ErrorCode
from scope_guard.domain.evaluations.evaluation_input import parse_evaluation as domain_parse
from scope_guard.domain.shared.errors import ValidationError


def parse_evaluation(body):
    try:
        return domain_parse(body)
    except ValidationError as error:
        raise ApiError(ErrorCode(error.code), error.status) from None
