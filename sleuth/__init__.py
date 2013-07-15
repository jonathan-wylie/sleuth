from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response


class Sleuth_Web_App(object):
    """This class listens for pivotal tracker activity posts, and publishes them."""
    
    def __init__(self, activity_receiver, port=8080):
        self.__activity_receiver = activity_receiver
        self.__port = port
        self.__config = Configurator()
        self.__config.add_route('activity_web_hook', '/activity_web_hook')
        self.__config.add_view(self.__activity_web_hook, route_name='activity_web_hook', request_method='POST')
        self.__app = self.__config.make_wsgi_app()
        self.__server = make_server('0.0.0.0', self.__port, self.__app)
        self.__server.serve_forever()
    
    def __activity_web_hook(self, request):
        self.__activity_receiver.activity_web_hook(request.body)
        return Response('OK')


class Sleuth(object):
	"""This class receives the activity xml parsed from the web app, and updates all the data"""
	def __init__(self):
		self.projects = {}

	def activity_web_hook(self, activity):
		print activity
		
		
if __name__ == '__main__':
    web_app = Sleuth_Web_App(Sleuth())
