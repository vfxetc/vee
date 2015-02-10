from vee.managers.base import BaseManager
from vee.package import Package as BasePackage



class HttpManager(BaseManager):
    pass


class HttpPackage(BasePackage):
    pass


HttpManager.package_class = HttpPackage
