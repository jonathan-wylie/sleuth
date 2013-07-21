from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from lxml import objectify


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
    	activity = objectify.fromstring(request.body)
        self.__activity_receiver.activity_web_hook(activity)
        return Response('OK')


class Story(object):
	"""The class represents a Pivotal Tracker User Story"""
  <id type="integer">387555039</id>
  <version type="integer">8659</version>
  <event_type>story_create</event_type>
  <occurred_at type="datetime">2013/07/15 19:58:39 UTC</occurred_at>
  <author>Jonathan Wylie</author>
  <project_id type="integer">138737</project_id>
  <description>Jonathan Wylie added &quot;test - new story&quot;</description>
  <stories type="array">
    <story>
      <id type="integer">53421649</id>
      <url>https://www.pivotaltracker.com/services/v3/projects/138737/stories/53421649</url>
      <name>test - new story</name>
      <story_type>bug</story_type>
      <description>the description</description>
      <current_state>unscheduled</current_state>
      <requested_by>Jonathan Wylie</requested_by>

	@static
	def create(story, activity):
		return Story(story.id, activity.project_id,
			         story.story_type, story.url, _story.estimate, story.current_state,
			         story.description, story.name, story.requested_by, _story.owned_by,
			         _story.created_at, _story.accepted_at, _story.labels)


	def __init__(self, story_id, project_id,
	             story_type, url, estimate, current_state,
	             description, name, requested_by, owned_by,
	             created_at, accepted_at, labels):
		self.id = story_id
		self.project_id = project_id
		self.story_type = story_type
		self.url = url
		self.estimate = estimate
		self.current_state = current_state
		self.description = description
		self.name = name
		self.requested_by = requested_by
		self.owned_by = owned_by
		self.created_at = created_at
		self.accepted_at = accepted_at
		self.labels = labels.split(",")


    def update(story, activity):
    	pass

    def delete():
    	pass


class Sleuth(object):
	"""This class receives the activity xml parsed from the web app, and updates all the data"""
	def __init__(self):
		self.projects = {}
		self.stories = {}

	def activity_web_hook(self, activity):
        if activity.event_type == 'story_update':
        	for story in activity.stories.iterchildren():
        		if story.id in self.stories:
        			self.stories[story.id].update(story, activity)
		elif activity.event_type == 'story_create':
			print activity
		elif activity.event_type == 'story_delete':
			if story.id in self.stories:
       			self.stories[story.id].delete()
       			del self.stories[story.id]
	



if __name__ == '__main__':
    web_app = Sleuth_Web_App(Sleuth())