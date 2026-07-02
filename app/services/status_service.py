from app.services.network import ethernet, wifi, access_point
from app.services.system import system_info
from app.services.resources import resources
from app.services.status import status


def get_status():
    result = {}

    result.update(ethernet())
    result.update(wifi())
    result.update(access_point())
    result.update(system_info())
    result.update(resources())
    result.update(status())

    return result
