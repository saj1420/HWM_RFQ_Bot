from threading import local


class Shared_values(local):
    clients = {}


shared_object = Shared_values()
