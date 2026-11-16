"""Render observed tool data; no calculation, file IO or inference."""


def reading_profile_view(result):
    return {k: v for k, v in result.items() if k != 'chart'}
