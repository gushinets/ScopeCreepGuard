from scope_guard.domain.evaluations.evaluation_input import parse_evaluation as domain_parse
from scope_guard.domain.shared.errors import ValidationError

from scope_guard_api.errors import ApiError, ErrorCode


def parse_evaluation(body):
    try:
        return domain_parse(body)
    except ValidationError as error:
        raise ApiError(ErrorCode(error.code), error.status) from None
